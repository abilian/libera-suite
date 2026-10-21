"""Windows: which ones exist, which is in front and what is in them.

The lower half of the package. Nothing here puts a dialog on screen:
`dialogs` does, from above, calling into this module.

`native` is chosen here, once: the toolkit module that draws this platform's
windows and dialogs (`macos`, `gtk` or `win32`, each a `portable.Toolkit`).
`windows` and `dialogs` both go through it, and nothing else tests the
platform.
"""

from __future__ import annotations

import logging
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

import webview
import webview.dom

from libera.host import apps, convert, language, server
from libera.host.session import SESSIONS, NotReadyError, lookup

if sys.platform == "darwin":
    from libera.host.window import macos as _toolkit
elif sys.platform == "win32":
    from libera.host.window import win32 as _toolkit
else:
    from libera.host.window import gtk as _toolkit

if TYPE_CHECKING:
    from webview import Window

    from libera.host.session import Session
    from libera.host.window.portable import Toolkit

# Typed, so each platform's pass of `make lint` holds its module to the
# Protocol: a call one toolkit lacks fails in lint, before it can fail at run
# time on that platform.
native: Toolkit = _toolkit

logger = logging.getLogger(__name__)


WINDOW_SIZE = (1400, 900)


def create_window(
    title: str, url: str, size: tuple[int, int] = WINDOW_SIZE, *, tabs: bool = True
) -> Window:
    """A window, or a NotReadyError where pywebview would return None.

    pywebview types create_window as `Window | None`; the callers all went
    straight on to `window.uid`, correct in practice and a crash in the one
    case the type is there to describe. Saying so once beats five unchecked
    dereferences.
    """
    width, height = size
    window = native.make_window(title, url, width, height, tabs=tabs)
    if window is None:
        msg = f"pywebview could not make a window for {title}"
        raise NotReadyError(msg)
    return window


# The start window while it is on screen: one at most, and only this module
# reads or changes the list. A test that patched it from `app` once left this
# module reading the original.
_start_windows: list[Window] = []


def remember_start_window(window: Window) -> None:
    _start_windows.append(window)


def forget_start_window(window: Window) -> None:
    """Closed by hand, it leaves the list too, or the next request to show it
    would find a dead window."""
    if window in _start_windows:
        _start_windows.remove(window)


def bring_start_window_forward() -> bool:
    """Show the start window if there is one; False when there is none."""
    if not _start_windows:
        return False
    _start_windows[0].show()
    return True


def close_start_window() -> None:
    """The start window has done its job once a document is on screen.

    LibreOffice's Start Center behaves this way. Leaving it open behind every
    document would make a window the user never asked for the one keeping the
    application alive.
    """
    for window in _start_windows:
        window.destroy()
    _start_windows.clear()


def find_front_session() -> Session | None:
    """The session of the window a menu item would act on.

    None for no window, and for the start window, which shows no session.
    """
    window = find_front_window()
    if window is None:
        return None
    uid = getattr(window, "uid", None)
    return next(
        (found for found in list(SESSIONS.values()) if found.window == uid), None
    )


def find_front_window() -> Window | None:
    """The window a menu item or dialog should act on.

    The window the toolkit says is in front, then pywebview's active window,
    then the only window there is, because "no window" is never the right answer
    while one is open.
    """
    if not webview.windows:
        return None
    # The key window is AppKit's to say, and AppKit is main-thread-only; the
    # menu, a new document and full screen ask from other threads.
    key = native.run_on_gui_thread(lambda: native.find_key_window(webview.windows))
    return key or webview.active_window() or webview.windows[0]


def copy_untitled(blank: Path, base: Path) -> Path:
    """A fresh untitled document, copied out so the template is never edited.

    Named after the blank it came from, so File > New in Tables makes a
    spreadsheet and not an Untitled.docx that Tables cannot open.
    """
    n, untitled = 1, language.translate("Untitled")
    candidate = base / f"{untitled}{blank.suffix}"
    while candidate.exists():
        n += 1
        candidate = base / f"{untitled} {n}{blank.suffix}"
    base.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(blank, candidate)
    return candidate


def make_new_document(app: apps.App | None = None) -> Path:
    """The document File > New should make, for the window that asked.

    `app` names the editor when the caller knows it: the start window asks
    for a spreadsheet from a session that is showing nothing. Without it the
    answer comes from the front window, which is what a menu item means.

    Separate from putting it in a window, because the decision is the part
    that has been wrong twice and a window cannot be created in a test.

    It asks the front window's session, or the first when nothing is in
    front. File > New arrives on a request thread when the editor sends it,
    and on a thread of its own when the macOS menu does; either way the answer
    is "the kind of document the front window holds", which is a property of
    the window and not of the thread.
    """
    asking = find_front_session() or lookup("")
    return copy_untitled(asking.choose_blank(app), asking.scratch)


def find_window(session: Session) -> Window | None:
    """The window showing that session, if it is still on screen."""
    uid = session.window
    return next((w for w in webview.windows if w.uid == uid), None) if uid else None


def fold_changes_in(session: Session) -> None:
    """Put the edits into Editor.bin, so a reload does not undo them.

    The editor works on Editor.bin plus a log of changes it streams as it
    types; a reload hands it Editor.bin alone, which is the document as it was
    opened. Converting out and back in makes the edits part of the base, and
    leaves an empty log: the same round trip a save does, without a
    destination.

    Raises ConversionError when it does not work; the edits are then still in
    the log, which is what a save merges.
    """
    if not session.change_log:
        return

    ext, fmt = session.editor.formats[0]
    session.out_dir.mkdir(parents=True, exist_ok=True)
    staged = session.out_dir / f"recovered.{ext}"
    # Both under the lock: the export reads the log, and the conversion back
    # replaces it, so an edit taken between the two was deleted with it.
    with session.lock:
        convert.export(session, staged, fmt, None)
        convert.convert_to_editor_bin(session, staged)
    logger.info("reload: folded the edits into %s", staged.name)


def reload_session(session: Session, port: int) -> None:
    """Rebuild the editor in that window, keeping the edits.

    Folds the change log into Editor.bin first: the editor works on
    Editor.bin plus the log it streams as you type, and a reload hands it
    Editor.bin alone, the document as it was *opened*. Without the fold,
    reloading would silently undo everything since.

    It does not reload at all when the fold fails. The reloaded editor counts
    its changes from nought again, so its first one would cut the log (the
    edits the fold could not keep) back to nothing. The window as it is can still
    save them.
    """
    window = find_window(session)
    if window is None:
        return
    fold_changes_in(session)
    document = session.read_current_document()
    name = document.name if document else "document"
    window.load_url(server.make_editor_url(port, session, name))

    # Offerable again later, but not for the errors already on their way from
    # the page being torn down.
    def make_offerable_again() -> None:
        session.reload_offered = False

    threading.Timer(5.0, make_offerable_again).start()


def close_session_window(session: Session) -> None:
    """Close the window showing that session, as its close button would."""
    window = find_window(session)
    if window is not None:
        native.close_window(window)


def document_title(session: Session, document: Path) -> str:
    """What a document window is called, and its tab on macOS."""
    return f"{document.name} — {session.editor.title}"


def show_session_document(session: Session, document: Path) -> None:
    """Retitle the window showing that session after a Save As."""
    window = find_window(session)
    if window is not None:
        window.set_title(document_title(session, document))


def show_session_edited(session: Session, edited: bool) -> None:
    """Mark the window showing that session as edited, or not."""
    window = find_window(session)
    if window is not None:
        native.show_edited(window, edited)


def set_fullscreen(on: bool) -> None:
    """Take the front window fullscreen for a demonstration, or give it back.

    A setter, because that is what sdkjs asks for; how closely a toolkit can
    honour one is the toolkit's business.
    """
    window = find_front_window()
    if window is not None:
        native.set_fullscreen(window, on)


# How long a drop waits for its paths. On macOS and GTK the native layer records
# them before the page sees the drop; on Windows they come in a message the
# page itself posts just before asking, handled on another thread.
DROP_WAIT = 1.0
DROP_POLL = 0.02


class _DropRecord(TypedDict):
    """`webview.dom._dnd_state`, which pywebview leaves untyped."""

    num_listeners: int
    paths: list[tuple[str, str]]  # (name, full path), oldest first


def _read_drop_record() -> _DropRecord:
    return cast("_DropRecord", webview.dom._dnd_state)


def listen_for_drops() -> None:
    """Have pywebview record the full path of every file dropped on a window.

    A page is only told a dropped file's name. pywebview's native layer reads
    the paths off the drag on all three platforms, but only while a drop
    listener is registered; it counts the listeners in `webview.dom._dnd_state`.
    Registering one through pywebview's DOM API would also put its handler on
    the top document, which consumes those paths and races the bridge, which
    asks for them itself (`take_dropped`). So the count, directly: private, and
    `tests/a_unit/host/test_drops.py` checks its shape against the installed
    pywebview.
    """
    _read_drop_record()["num_listeners"] += 1


def take_dropped(names: list[str]) -> list[Path]:
    """The full paths of the files just dropped, by the names the page saw.

    The newest record of a name wins and every record of it goes: a drop the
    page never asked about (one that missed every frame) must not answer for
    the next file of the same name.
    """
    record = _read_drop_record()["paths"]
    deadline = time.monotonic() + DROP_WAIT
    while not set(names) <= {name for name, _ in record}:
        if time.monotonic() > deadline:
            break
        time.sleep(DROP_POLL)
    found = []
    for name in names:
        matches = [path for recorded, path in record if recorded == name]
        if matches:
            found.append(Path(matches[-1]))
        record[:] = [entry for entry in record if entry[0] != name]
    return found
