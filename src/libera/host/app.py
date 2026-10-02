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
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import webview

from libera import payload as payload_mod
from libera.host import apps, hooks, instance, menu, opening, server
from libera.host.session import (
    NotReadyError,
    Session,
    configure,
    create_session,
    drop_session,
    sweep_sessions,
)
from libera.host.window import (
    _create_window,
    ask_open_path,
    ask_save_path,
    ask_to_recover,
    close_start_window,
    confirm_close,
    dialogs,
    make_new_document,
    native,
    offer_reload,
    set_fullscreen,
)
from libera.host.window.windows import START_WINDOW

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# How long the later documents wait for the first window to be on screen.
SHOWN_TIMEOUT = 30.0


def _open_first_window(port: int, first: Session, title: str | None):
    """What `libera` puts on screen: a document, or the start window.

    The first session is configured either way; only the start window has no
    document in it, and therefore nothing to prompt about on close.
    """
    if first.document is None:
        return _open_start_window(port, title)
    window = _create_window(
        title or f"{first.document.name} — {first.editor.title}",
        server.make_editor_url(port, first, first.document.name),
    )
    first.window = window.uid
    window.events.closing += lambda: confirm_close(first.id)
    return window


def _open_start_window(port: int, title: str | None = None):
    """The start window, which offers every kind of document."""
    window = _create_window(
        title or "Libera Suite",
        f"http://127.0.0.1:{port}/__host__/start",
        size=(720, 640),
    )
    START_WINDOW.append(window)
    # Closed by hand rather than by opening a document, it has to leave the
    # list too, or the next request to show it would find a dead window.
    window.events.closed += lambda: _forget_start_window(window)
    return window


def run(
    payload_root: Path, work: Path, documents: list[Path], *, title: str | None = None
) -> None:
    """Open documents, one window each, and block until the last one closes.

    With no documents this is `libera` on its own: the start window comes up
    instead, and goes away as soon as it has been used for something.
    """
    first = documents[0] if documents else None
    # A session either way. The start window shows no document, but everything
    # it asks the host for -- the recent list, a new blank, the payload -- is
    # answered for a session, and there has to be one to answer for.
    first_session = Session(payload=payload_root, work=work / "0", document=first)
    configure(first_session)

    port = server.find_free_port()
    httpd = server.make_server(port, first_session)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    # From here the host has windows to put documents in and dialogs to ask
    # with -- before the first document opens, because opening it may ask
    # whether to recover its unsaved edits.
    shell = WindowedShell(port)
    hooks.shell = shell

    if first is not None:
        # Before the window: opening a document destroys the previous session,
        # and that session is where unsaved edits live.
        opening.open_document(first_session, first)
    # Anything left by earlier runs that holds nothing worth keeping.
    sweep_sessions(work, keep={first_session.id})

    # What the toolkit reads once, as the application is first made: on macOS
    # the application's name, and its window and Edit-menu defaults.
    native.prepare()

    window = _open_first_window(port, first_session, title)
    # The rest open once the GUI loop is running: pywebview can only create a
    # window after start() from a thread that is not the one running it.
    if len(documents) > 1:
        threading.Thread(
            target=_open_rest,
            args=(window, documents[1:], shell.open_window),
            daemon=True,
        ).start()

    # The Linux and Windows bar has to exist before start(): pywebview reads
    # `menu` once, on the application's startup signal, and GTK has no way to
    # add to a bar afterwards. macOS is the other way round -- its bar is
    # extended once the application runs, by complete_startup below, because
    # there is no menu to extend before -- and hands start() nothing.
    bar = menu.native.make_menubar()
    # From here a second `libera FILE` hands its documents to this process
    # rather than starting another; see `instance`.
    instance.announce(port)
    # The editor keeps every preference it has in localStorage -- theme, units,
    # spellcheck language, dismissed tips -- and pywebview defaults to
    # private_mode, which on macOS wipes the whole WebKit data store at startup.
    # So the editor began from nothing every launch. storage_path does nothing
    # on macOS (the default store is used either way); it is where the GTK and
    # Edge backends will put the same data.
    #
    # `func` is pywebview's own "once the GUI loop starts", on a thread of its
    # own: start() does not return until the last window closes.
    try:
        webview.start(
            func=native.complete_startup,
            args=(menu.native.install,),
            private_mode=False,
            storage_path=str(payload_mod.get_state_dir()),
            menu=bar,
        )
    finally:
        instance.withdraw()


class WindowedShell:
    """The shell `run()` installs: windows to put documents in, dialogs to ask
    with, and the port those windows load the editor from."""

    windowed = True

    def __init__(self, port: int) -> None:
        self.port = port

    def open_window(self, document: Path | None, app: apps.App | None = None) -> bool:
        """A document on screen in a window of its own.

        Called from a request thread: pywebview dispatches window creation to the
        GUI thread itself, so this does not have to.

        A document that will not open is said so on screen, and leaves nothing
        behind. It used to raise into whoever asked: a request lost its
        connection with no answer, a menu action printed a traceback nobody saw,
        a session stayed registered with no window, and a second launch whose
        hand-off failed that way started a second instance.
        """
        document = document or make_new_document(app)
        made = create_session(document)
        try:
            opening.open_document(made, document)
        except NotReadyError:
            # convert has logged what x2t said; the user needs to hear it too.
            drop_session(made.id)
            dialogs.say(
                f"Libera Suite could not open \u201c{document.name}\u201d",
                "The converter could not read it: it may be damaged, or in a "
                "format Libera Suite cannot open.",
            )
            return False

        opened = _create_window(
            f"{document.name} — {made.editor.title}",
            server.make_editor_url(self.port, made, document.name),
        )
        made.window = opened.uid
        opened.events.closing += lambda: confirm_close(made.id)
        close_start_window()
        # A closed window's session is over. Its directory stays: it may hold
        # edits that never reached the file, and those are offered back.
        opened.events.closed += lambda: drop_session(made.id)
        return True

    def show_start_window(self) -> None:
        """The start window, which offers every kind of document.

        One of it. Asked again, by a second click on the editor's Create New or a
        second launch with no document, the one on screen comes to the front.
        """
        if START_WINDOW:
            START_WINDOW[0].show()
            return
        _open_start_window(self.port)

    def choose_save_path(
        self, suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None
    ) -> str | None:
        return ask_save_path(suggested, formats, start_in)

    def choose_open_path(self, kind: str) -> str | None:
        return ask_open_path(kind)

    def set_fullscreen(self, on: bool) -> None:
        set_fullscreen(on)

    def offer_reload(self, session: Session, message: str) -> None:
        offer_reload(session, message, self.port)

    def reload(self, session: Session) -> None:
        # File > Reload, the way out when the editor has told the user itself
        # and the host therefore stayed quiet.
        dialogs.reload(session, self.port)

    def ask_to_recover(self, document: Path) -> bool:
        return ask_to_recover(document)

    def tell(self, heading: str, detail: str) -> None:
        dialogs.say(heading, detail)


def _forget_start_window(window) -> None:
    if window in START_WINDOW:
        START_WINDOW.remove(window)


def _open_rest(window, documents: list[Path], open_window) -> None:
    """The second and later documents, once the GUI loop is really running.

    **This waited for nothing.** The condition was `webview.windows`, and
    `create_window` appends to that list *before* `start()` is called, so the
    loop returned on its first iteration and every document after the first was
    created while the GUI loop did not yet exist. The comment above it stated
    the requirement it was failing to meet: a window created before `start()`
    has run is never shown. Whether it appeared came down to a race against
    `webview.start()` on the main thread, which `open_window` usually lost by a
    conversion's worth of time -- which is why this mostly worked.

    It is the same bug as `_install_menu`, from the same cause, and
    `notes/lessons-learned.md` is about exactly this: a docstring is not a test,
    so read the condition and the sentence next to each other and ask whether
    one implies the other.

    `shown` fires from the GUI loop with the window on screen, so unlike a list
    that `create_window` fills, it cannot be set before `start()`. It is also
    what pywebview waits on for the same job: `start()`'s own `_create_children`
    blocks on `windows[0].events.shown` before creating the rest.

    The cost of losing the race is not a slow window but a missing one.
    `start()` runs `_initialize` over `windows`, then snapshots `windows[1:]`
    for that thread, then enters the GUI loop; a window appended between the
    snapshot and the loop is never created, and one appended between the two
    earlier steps is created without being initialised. Waiting for `shown`
    puts every later document after all three, which is the only state with one
    outcome.
    """
    if not window.events.shown.wait(SHOWN_TIMEOUT):
        # Opening them anyway: a window that is slow to appear is still better
        # served by trying than by silently dropping the documents someone named
        # on the command line.
        logger.warning("the first window has not appeared; opening the rest anyway")
    for document in documents:
        open_window(document)
