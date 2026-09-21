"""Starting the application: the server, the first windows, the menu bar.

The top of the host, and the only module that may touch every layer below it.

It exists because of a cycle. `run()` used to live in `window.py`, which meant
window reached *up* to `menu` to install the menu bar -- while `menu` reached
down to window for the front window. Six function-level imports held the two
apart, and a function-level import is what a circular dependency looks like
once somebody has worked around it.

Putting the runner above both leaves every import pointing one way. See
`host/__init__.py` for the order.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

from libera import payload as payload_mod
from libera.host import apps, hooks, menu, opening, server
from libera.host.session import (
    SESSIONS,
    H,
    Host,
    configure,
    drop_session,
    new_session,
    sweep_sessions,
    use,
)
from libera.host.window import (
    SESSION_BY_WINDOW,
    _ask_to_recover,
    _window,
    ask_open_path,
    ask_save_path,
    close_start_window,
    confirm_close,
    new_document,
    offer_reload,
    on_gui_thread,
    reload_session,
    set_fullscreen,
)
from libera.host.window.windows import START_WINDOW

logger = logging.getLogger(__name__)


def _first_window(port: int, first: Path | None, title: str | None):
    """What `libera` puts on screen: a document, or the start window.

    Session "0" is already configured either way; only the start window has no
    document in it, and therefore nothing to prompt about on close.
    """
    import webview

    if first is None:
        window = webview.create_window(
            title or "Libera Suite",
            f"http://127.0.0.1:{port}/__host__/start",
            width=720,
            height=640,
        )
        START_WINDOW.append(window)
        return window

    window = _window(
        title or f"{first.name} — {H.editor.title}",
        server.editor_url(port, first.name, "0"),
    )
    SESSION_BY_WINDOW[window.uid] = "0"
    window.events.closing += lambda: confirm_close("0")
    return window


def run(
    payload_root: Path, work: Path, documents: list[Path], *, title: str | None = None
) -> None:
    """Open documents, one window each, and block until the last one closes.

    With no documents this is `libera` on its own: the start window comes up
    instead, and goes away as soon as it has been used for something.
    """
    # Imported here rather than at module scope: pywebview pulls in the pyobjc
    # frameworks, and `libera --payload-status` has no reason to pay for them.
    import webview

    first = documents[0] if documents else None
    # A session either way. The start window shows no document, but everything
    # it asks the host for -- the recent list, a new blank, the payload -- goes
    # through a bound session, and there has to be one to bind.
    configure(Host(payload=payload_root, work=work / "0", document=first))
    hooks.RECOVERY_CHOOSER = _ask_to_recover
    if first is not None:
        # Before the window: opening a document destroys the previous session,
        # and that session is where unsaved edits live.
        opening.open_document(first)
    # Anything left by earlier runs that holds nothing worth keeping.
    sweep_sessions(work, keep={"0"})

    # The server asks for filenames through these, because only a process with
    # a window can put a dialog on screen.
    hooks.SAVE_PATH_CHOOSER = ask_save_path
    hooks.OPEN_PATH_CHOOSER = ask_open_path

    port = server.free_port()
    httpd = server.make_server(port)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def open_window(document: Path | None, app: apps.App | None = None) -> None:
        """Put a document on screen in a window of its own.

        Called from a request thread: pywebview dispatches window creation to
        the GUI thread itself, so this does not have to.
        """
        document = document or new_document(app)
        session = new_session(document)
        use(SESSIONS[session], session)
        opening.open_document(document)

        opened = _window(
            f"{document.name} — {H.editor.title}",
            server.editor_url(port, document.name, session),
        )
        SESSION_BY_WINDOW[opened.uid] = session
        opened.events.closing += lambda: confirm_close(session)
        close_start_window()
        # A closed window's session is over. Its directory stays: it may hold
        # edits that never reached the file, and those are offered back.
        opened.events.closed += lambda: drop_session(session)

    hooks.WINDOW_OPENER = open_window
    hooks.FULLSCREEN = set_fullscreen

    hooks.BROKEN = lambda session, message: offer_reload(session, message, port)
    # File > Reload, which is the way out when the editor has told the user
    # itself and the host therefore stayed quiet.
    hooks.RELOAD = lambda session: on_gui_thread(lambda: reload_session(session, port))

    if sys.platform == "darwin":
        # First, and not for tidiness: this rewrites the running bundle's
        # CFBundleName, and macOS reads that once, when NSApplication.
        # sharedApplication() is first called. Afterwards the menu bar says
        # "Python" for the life of the process and nothing can change it.
        menu.name_the_application()

        # macOS gives any document-shaped window a tab bar, and a tab bar with
        # one tab is a second title bar saying what the first one said. Tabs
        # would need real support (newWindowForTab:, moving a document between
        # windows); until Libera Suite has it, turn them off. Class-level and before
        # the window exists, because a bar already on screen does not come off.
        import AppKit

        AppKit.NSWindow.setAllowsAutomaticWindowTabbing_(False)

        # Before the menu bar is built, which is the only time these are read.
        menu.quieten_system_items()

    _first_window(port, first, title)
    # The rest open once the GUI loop is running: pywebview can only create a
    # window after start() from a thread that is not the one running it.
    if len(documents) > 1:
        threading.Thread(
            target=_open_rest, args=(documents[1:], open_window), daemon=True
        ).start()

    # The editor keeps every preference it has in localStorage -- theme, units,
    # spellcheck language, dismissed tips -- and pywebview defaults to
    # private_mode, which on macOS wipes the whole WebKit data store at startup.
    # So the editor began from nothing every launch. storage_path does nothing
    # on macOS (the default store is used either way); it is where the GTK and
    # Edge backends will put the same data.
    if sys.platform == "darwin":
        # After start(), because there is no menu to add to until the
        # application is running; on a thread, because start() does not return
        # until the last window closes.
        threading.Thread(target=_install_menu, daemon=True).start()

    # The Linux bar has to exist before start(): pywebview reads `menu` once,
    # on the application's startup signal, and GTK has no way to add to a bar
    # afterwards. macOS is the other way round -- its bar is built from
    # _install_menu above, after start(), because there is no menu to extend
    # until the application is running.
    bar = menu.gtk_menubar() if sys.platform.startswith("linux") else []
    webview.start(
        private_mode=False,
        storage_path=str(payload_mod.state_dir()),
        menu=bar,
    )


def _install_menu() -> None:
    """Put Libera Suite's menus on the bar once pywebview has built its own.

    Waiting for `webview.windows` was waiting for nothing: create_window fills
    that list before start() runs, so the wait returned at once and the install
    landed before there was a menu to add to. install() checks and returns
    quietly in that case, which is why the symptom was an application with no
    File menu rather than a crash -- and why it came and went.

    So ask on the GUI thread, where the menu lives, and ask again shortly if it
    is not there yet.
    """
    from PyObjCTools import AppHelper

    def attempt(tries: int = 40) -> None:
        import AppKit

        if AppKit.NSApp is None or AppKit.NSApp.mainMenu() is None:
            if tries:
                AppHelper.callLater(0.05, attempt, tries - 1)
            else:
                logger.warning("no menu bar to add to; our menus are missing")
            return
        menu.install()

    AppHelper.callAfter(attempt)


def _open_rest(documents: list[Path], open_window) -> None:
    """The second and later documents, once the GUI loop is up."""
    import time

    import webview

    # Wait for the first window rather than guess at a delay: create_window
    # before start() has run leaves the window unshown.
    for _ in range(200):
        if webview.windows:
            break
        time.sleep(0.05)
    for document in documents:
        open_window(document)
