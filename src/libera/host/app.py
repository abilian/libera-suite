"""Starting the application: the server, the first windows, the menu bar.

The top of the host: the only module that may touch every layer below it.

It exists because of a cycle. `run()` used to live in `window.py`, which meant
window reached *up* to `menu` to install the menu bar -- while `menu` reached
down to window for the front window. Six function-level imports held the two
apart; a function-level import is a circular dependency that somebody has
worked around.

Putting the runner above both leaves every import pointing one way. See
`host/__init__.py` for the order.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import webview

from libera import payload as payload_mod, timeline
from libera.host import (
    apps,
    hooks,
    instance,
    language,
    locking,
    menu,
    opening,
    server,
    updates,
)
from libera.host.session import (
    SESSIONS,
    Session,
    configure,
    create_session,
    drop_session,
    find_session_showing,
    new_work,
    sweep_sessions,
)
from libera.host.window import (
    ask_open_path,
    ask_save_path,
    ask_to_recover,
    bring_start_window_forward,
    close_session_window,
    close_start_window,
    confirm_close,
    create_window,
    dialogs,
    find_window,
    forget_start_window,
    listen_for_drops,
    make_new_document,
    native,
    offer_reload,
    remember_start_window,
    set_fullscreen,
    show_session_edited,
    take_dropped,
)
from libera.payload import fonts, generate, locate, prune

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from libera.host.convert import ConversionError

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
    return _show_session(port, first, first.document, title)


def _show_session(
    port: int, session: Session, document: Path, title: str | None = None
):
    """A window on a session's document, with what ends when it closes.

    Every document window comes through here. The first once made its own,
    wired to ask before closing but not to let go after: its lock file
    outlived Libera Suite and its session stayed registered, so the edits
    "Don't Save" left behind were never offered back.
    """
    window = create_window(
        title or f"{document.name} — {session.editor.title}",
        server.make_editor_url(port, session, document.name),
    )
    session.window = window.uid
    window.events.closing += lambda: confirm_close(session.id)
    # A closed window's session is over, and so is its lock. Its directory
    # stays: it may hold edits that never reached the file, which are offered
    # back.
    window.events.closed += lambda: close_session(session)
    return window


def _open_start_window(port: int, title: str | None = None):
    """The start window, which offers every kind of document."""
    window = create_window(
        title or "Libera Suite",
        f"http://127.0.0.1:{port}/__host__/start?key={instance.TOKEN}",
        size=(720, 640),
        tabs=False,
    )
    remember_start_window(window)
    window.events.closed += lambda: forget_start_window(window)
    return window


def run(
    payload_root: Path,
    work: Path,
    documents: list[Path],
    *,
    title: str | None = None,
    shot: Path | None = None,
) -> None:
    """Open documents, one window each, and block until the last one closes
    (on macOS, until Quit).

    With no documents this is `libera` on its own: the start window comes up
    instead, and goes away as soon as it has been used for something.
    """
    first = documents[0] if documents else None
    # A session either way. Everything the start window asks the host for
    # (the recent list, a new blank, the payload) is answered for a session,
    # even with no document shown, so there has to be one to answer for.
    timeline.mark("host")
    prune.note_use(payload_root)
    layout = locate.Layout(payload_root)
    first_session = Session(
        payload=payload_root,
        work=new_work(work),
        document=first,
        fonts=fonts.choose(layout),
        # `libera --shot FILE`: every window's page posts its own render, each
        # to a name of its own (session.create_session). What the real web
        # engine drew is otherwise unmeasurable -- see tests/d_gui/.
        shot=shot,
    )
    logger.info("fonts: %s", first_session.fonts or "the payload's own")
    configure(first_session)

    port = server.find_free_port()
    httpd = server.make_server(port, first_session)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    # From here the host has windows to put documents in and dialogs to ask
    # with -- before the first document opens, because opening it may ask
    # whether to recover its unsaved edits.
    shell = WindowedShell(port)
    hooks.shell = shell
    listen_for_drops()
    previous_hook = threading.excepthook
    threading.excepthook = _say_thread_failed

    converting = False
    if first is not None:
        # Before the window: opening a document destroys the previous session,
        # and that session is where unsaved edits live. Its conversion waits
        # for the window, and runs while the window loads the editor.
        converting = opening.begin_opening(first_session, first)
    # Anything left by earlier runs that holds no unsaved edits.
    sweep_sessions(work, keep={first_session.id})

    # What the toolkit reads once, as the application is first made: on macOS
    # the application's name, and its window and Edit-menu defaults.
    native.prepare()

    window = _open_first_window(port, first_session, title)
    timeline.mark("window")
    if first is not None and converting:
        _convert_behind(first_session, first)
    # After the first window, so that allfontsgen does not slow its document.
    fonts.build_behind(layout, {first_session.fonts})
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
    # own: start() does not return until the last window closes, and on macOS
    # a quit ends the process without its returning at all.
    native.on_quit(_let_go_of_everything)
    try:
        webview.start(
            func=native.complete_startup,
            args=(_once_running,),
            private_mode=False,
            storage_path=str(payload_mod.get_state_dir()),
            menu=bar,
            localization=translate_pywebview(),
            gui=native.GUI,
        )
        native.stay_open()
    finally:
        threading.excepthook = previous_hook
        _let_go_of_everything()


def translate_pywebview() -> dict[str, str]:
    """pywebview's own strings -- its Edit and View menus, the application
    menu's Hide and Quit, OK and Cancel, the Save panel's title -- through our
    catalogue. menu.macos finds the Edit and View menus by these titles."""
    return {
        key: language.translate(english)
        for key, english in webview.localization.original_localization.items()
    }


def _let_go_of_everything() -> None:
    """On the way out, however the windows went: a quit need not close each one
    first, yet no lock of ours may outlive the process, nor the announcement a
    second launch would hand its documents to, nor a font index's build."""
    instance.withdraw()
    generate.stop_allfontsgen()
    for left in list(SESSIONS.values()):
        locking.let_go(left)


def _say_thread_failed(args: threading.ExceptHookArgs) -> None:
    """A failure on one of our threads -- opening, a menu action, a drop --
    said where the user is looking. Launched from Finder, Explorer or a
    launcher, stderr goes nowhere; the traceback was all there was."""
    if args.exc_type is SystemExit:
        return
    where = args.thread.name if args.thread else "a thread"
    logger.error("%s failed", where, exc_info=args.exc_value)
    dialogs.say(
        language.translate("Libera Suite ran into a problem"),
        language.translate(
            "{error}. The details are in the log.",
            error=args.exc_value or args.exc_type.__name__,
        ),
    )


def _once_running() -> None:
    """What waits for the GUI loop: the menus, and the update check, whose one
    message is a dialog."""
    timeline.mark("gui-loop")
    menu.native.install()
    updates.check_in_background()
    # Other versions of the payload that nobody has used for weeks.
    prune.remove_unused_behind(locate.get_data_dir(), keep=locate.PAYLOAD_VERSION)


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
        connection with no answer, a menu action printed a traceback no one saw,
        a session stayed registered with no window, and a second launch whose
        hand-off failed that way started a second instance. The window opens
        before the converter has read the document (`_convert_behind`), so it
        is that window which closes again.
        """
        # One window per document. Two windows on one file each converted and
        # saved it on their own, and the last save silently won.
        shown = find_session_showing(document) if document else None
        window = find_window(shown) if shown else None
        if window is not None:
            window.show()
            return True
        document = document or make_new_document(app)
        made = create_session(document)
        converting = opening.begin_opening(made, document)
        _show_session(self.port, made, document)
        timeline.mark("window", again=True)
        if converting:
            # The start window goes once there is a document to show instead.
            _convert_behind(made, document, done=close_start_window)
        else:
            close_start_window()
        return True

    def show_start_window(self) -> None:
        """The start window, which offers every kind of document.

        One of it. Asked again, by a second click on the editor's Create New or a
        second launch with no document, the one on screen comes to the front.
        """
        if not bring_start_window_forward():
            _open_start_window(self.port)

    def choose_save_path(
        self, suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None
    ) -> str | None:
        return ask_save_path(suggested, formats, start_in)

    def choose_open_path(self, kind: str) -> str | None:
        return ask_open_path(kind)

    def set_fullscreen(self, on: bool) -> None:
        set_fullscreen(on)

    def close_window(self, session: Session) -> None:
        close_session_window(session)

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

    def show_edited(self, session: Session, edited: bool) -> None:
        show_session_edited(session, edited)

    def take_dropped(self, names: list[str]) -> list[Path]:
        return take_dropped(names)


def _convert_behind(
    session: Session, document: Path, done: Callable[[], None] = lambda: None
) -> None:
    """The document's conversion, while its window loads the editor. A
    document the converter refuses is said on screen, and its window closed."""

    def failed(_error: ConversionError) -> None:
        # convert has logged what x2t said; the user needs to hear it too.
        dialogs.say(
            language.translate(
                "Libera Suite could not open “{name}”", name=document.name
            ),
            language.translate(
                "The converter could not read it: it may be damaged, or in a "
                "format Libera Suite cannot open."
            ),
        )
        close_session_window(session)

    opening.convert_behind(session, document, failed, done)


def close_session(session: Session) -> None:
    locking.let_go(session)
    drop_session(session.id)
    if not SESSIONS:
        # A request that names no session is answered for the first: a second
        # launch's hand-off, the start window's. On macOS the application runs
        # on once its last window has closed, and refused them all.
        configure(
            Session(
                payload=session.payload,
                work=new_work(session.work.parent),
                fonts=session.fonts,
            )
        )


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
    `notes/lessons-learned/threads.md` is about exactly this: a docstring is
    not a test, so read the condition and the sentence next to each other and
    ask whether one implies the other.

    `shown` fires from the GUI loop with the window on screen, so unlike a list
    that `create_window` fills, it cannot be set before `start()`. It is also
    what pywebview waits on for the same job: `start()`'s own `_create_children`
    blocks on `windows[0].events.shown` before creating the rest.

    Losing the race costs the window itself.
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
