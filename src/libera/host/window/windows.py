"""Windows: which ones exist, which is in front, and what is in them.

The lower half of the package. Nothing here puts a dialog on screen -- that is
`dialogs`, which is above this and calls into it.

`on_gui_thread` lives here because both halves need it and it is the smallest
thing either depends on: AppKit is not thread-safe, and everything below is
called from HTTP request threads.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from libera import payload as payload_mod
from libera.host import apps, convert, server
from libera.host.session import (
    SESSIONS,
    H,
    NotReadyError,
    bind,
    current_path,
    use,
)

if TYPE_CHECKING:
    from webview import Window

logger = logging.getLogger(__name__)


def on_gui_thread(work):
    """Run something that touches AppKit, and wait for its answer.

    AppKit is main-thread-only, and it does not warn: "NSWindow should only be
    instantiated on the main thread" is a hard exception that takes the request
    with it. Most of what asks the user a question arrives on a request thread,
    so it has to come back here first.

    Already on it? Call it. Dispatching to the thread we are standing on and
    then waiting for it is a deadlock.
    """
    if threading.current_thread() is threading.main_thread():
        return work()

    from PyObjCTools import AppHelper

    done = threading.Event()
    answer: list = [None]

    def run():
        try:
            answer[0] = work()
        finally:
            done.set()

    AppHelper.callAfter(run)
    done.wait()
    return answer[0]


SESSION_BY_WINDOW: dict[str, str] = {}
WINDOW_SIZE = (1400, 900)


def _window(title: str, url: str) -> Window:
    """A window, or a clear failure instead of a None nobody checks.

    pywebview types create_window as `Window | None`, and the callers all went
    straight on to `window.uid` -- correct in practice and a crash in the one
    case the type is there to describe. Saying so once beats five unchecked
    dereferences.
    """
    import webview

    width, height = WINDOW_SIZE
    window = webview.create_window(title, url, width=width, height=height)
    if window is None:
        msg = f"pywebview could not make a window for {title}"
        raise NotReadyError(msg)
    return window


START_WINDOW: list = []


def close_start_window() -> None:
    """The start window has done its job once a document is on screen.

    LibreOffice's Start Center behaves this way, and the alternative -- leaving
    it open behind every document -- means a window nobody asked for is the one
    keeping the application alive.
    """
    for window in START_WINDOW:
        window.destroy()
    START_WINDOW.clear()


def front_session() -> str:
    """The session of the window a menu item would act on."""
    window = front_window()
    if window is None:
        return ""
    return SESSION_BY_WINDOW.get(getattr(window, "uid", ""), "")


def front_window() -> Window | None:
    """The window a menu item or dialog should act on.

    pywebview's active_window() is keyWindow, which is None whenever the
    application is not frontmost -- and is the sheet, not the document, while
    a save panel is up. Fall through to the main window and then to the only
    window there is, because "no window" is never the right answer while one
    is open.
    """
    import webview

    if not webview.windows:
        return None
    # Annotated because it is empty everywhere but macOS: off a Mac the branch
    # below is pruned and there is nothing left to infer an element type from,
    # which mypy says and mypy-on-a-Mac never does.
    candidates: list[Any] = []
    if sys.platform == "darwin":
        import AppKit

        candidates = [AppKit.NSApp.keyWindow(), AppKit.NSApp.mainWindow()]
    for native in candidates:
        if native is None:
            continue
        for window in webview.windows:
            # Bound to a local rather than fetched twice: a checker cannot
            # narrow `getattr(x, "native", None)` across a second lookup, and
            # neither can a reader be sure it is the same object.
            its_native = getattr(window, "native", None)
            if its_native is not None and (
                its_native.windowNumber() == native.windowNumber()
            ):
                return window
    return webview.active_window() or webview.windows[0]


def untitled(blank: Path, base: Path | None = None) -> Path:
    """A fresh untitled document, copied out so the template is never edited.

    Named after the blank it came from, so File > New in Tables makes a
    spreadsheet and not an Untitled.docx that Tables cannot open.
    """
    import shutil

    base = base or payload_mod.state_dir()
    n = 1
    candidate = base / f"Untitled{blank.suffix}"
    while candidate.exists():
        n += 1
        candidate = base / f"Untitled {n}{blank.suffix}"
    base.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(blank, candidate)
    return candidate


def new_document(app: apps.App | None = None) -> Path:
    """The document File > New should make, for the window that asked.

    `app` names the editor when the caller knows it -- the start window asks
    for a spreadsheet from a session that is showing nothing. Without it the
    answer comes from the front window, which is what a menu item means.

    Separate from putting it in a window, and this is the whole reason: the
    decision is the part that has been wrong twice, and a window cannot be
    created in a test.

    It binds the front window's session first. File > New arrives on a request
    thread with the asking session already bound when the editor sends it, and
    on a thread of its own with nothing bound at all when the macOS menu does
    -- `H` is thread-local, so the second case raised rather than defaulting.
    Either way the answer is "the kind of document the front window holds",
    which is a property of the window and not of the thread.
    """
    bind(front_session())
    return untitled(H.blank_for(app), H.scratch)


def window_for(session: str):
    """The window showing that session, if it is still on screen."""
    import webview

    uid = next((u for u, s in SESSION_BY_WINDOW.items() if s == session), None)
    return next((w for w in webview.windows if w.uid == uid), None) if uid else None


def fold_changes_in() -> bool:
    """Put the edits into Editor.bin, so a reload does not undo them.

    The editor works on Editor.bin plus a log of changes it streams as it
    types; a reload hands it Editor.bin alone, which is the document as it was
    opened. Converting out and back in makes the edits part of the base, and
    leaves an empty log -- the same round trip a save does, without a
    destination.

    False when it does not work, and then reloading still beats a wedged
    window: the edits are in the log, and the log is what a save merges.
    """
    change_log = H.doc / "changes" / "changes0.json"
    if not change_log.is_file() or change_log.stat().st_size == 0:
        return True

    ext, fmt = H.editor.formats[0]
    H.out.mkdir(parents=True, exist_ok=True)
    staged = H.out / f"recovered.{ext}"
    if not convert.export(staged, fmt):
        logger.error("reload: could not fold in the edits")
        return False
    if not convert.convert_to_editor_bin(staged):
        logger.error("reload: could not reopen the folded document")
        return False
    logger.info("reload: folded the edits into %s", staged.name)
    return True


def reload_session(session: str, port: int) -> None:
    """Rebuild the editor in that window, keeping the edits.

    Folds the change log into Editor.bin first: the editor works on
    Editor.bin plus the log it streams as you type, and a reload hands it
    Editor.bin alone -- the document as it was *opened*. Without the fold,
    reloading would silently undo everything since.
    """
    window = window_for(session)
    if window is None:
        return
    use(SESSIONS[session], session)
    document = current_path()
    fold_changes_in()
    name = document.name if document else "document"
    window.load_url(server.editor_url(port, name, session))
    # Offerable again later, but not for the errors already on their way from
    # the page being torn down.
    threading.Timer(5.0, lambda: server.OFFERED.discard(session)).start()


def set_fullscreen(on: bool) -> None:
    """Take the front window fullscreen for a demonstration, or give it back.

    A setter, because that is what sdkjs asks for. pywebview offers only
    toggle_fullscreen(), which drifts out of step the first time a call is
    missed, so on macOS this reads the window's own style mask and acts only
    when the two disagree.
    """
    # One guard per thing, in order. Folding them into
    # `getattr(window, "native", None) if window else None` narrows `native`
    # and leaves `window` a `Window | None` that the non-macOS branch below
    # then dereferences -- which a checker on Linux says out loud and a
    # checker on macOS never sees, because it prunes that branch first.
    window = front_window()
    if window is None:
        return
    native = getattr(window, "native", None)
    if native is None:
        return

    if sys.platform != "darwin":
        # Nothing to read the state from, so the toggle is all there is.
        window.toggle_fullscreen()
        return

    import AppKit
    from PyObjCTools import AppHelper

    def apply() -> None:
        already = bool(native.styleMask() & AppKit.NSWindowStyleMaskFullScreen)
        if already != on:
            native.toggleFullScreen_(None)

    # The request arrives on a server thread; AppKit belongs to the GUI one.
    AppHelper.callAfter(apply)
