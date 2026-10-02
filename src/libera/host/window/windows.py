"""Windows: which ones exist, which is in front, and what is in them.

The lower half of the package. Nothing here puts a dialog on screen -- that is
`dialogs`, which is above this and calls into it.

`native` is chosen here, once: the toolkit module that draws this platform's
windows and dialogs -- `macos`, `gtk` or `win32`, each a `portable.Toolkit`.
Both halves of the package go through it, and nothing else tests the
platform.
"""

from __future__ import annotations

import logging
import shutil
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import webview

from libera.host import apps, convert, server
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
# Protocol: a call one toolkit lacks fails there, not on that platform.
native: Toolkit = _toolkit

logger = logging.getLogger(__name__)


WINDOW_SIZE = (1400, 900)


def _create_window(title: str, url: str, size: tuple[int, int] = WINDOW_SIZE) -> Window:
    """A window, or a clear failure instead of a None nobody checks.

    pywebview types create_window as `Window | None`, and the callers all went
    straight on to `window.uid` -- correct in practice and a crash in the one
    case the type is there to describe. Saying so once beats five unchecked
    dereferences.
    """
    width, height = size
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


def find_front_session() -> Session | None:
    """The session of the window a menu item would act on.

    None for no window, and for the start window, which shows no session.
    """
    window = find_front_window()
    if window is None:
        return None
    uid = getattr(window, "uid", None)
    return next((found for found in SESSIONS.values() if found.window == uid), None)


def find_front_window() -> Window | None:
    """The window a menu item or dialog should act on.

    What the toolkit says is in front, then pywebview's active window, then
    the only window there is, because "no window" is never the right answer
    while one is open.
    """
    if not webview.windows:
        return None
    return (
        native.find_key_window(webview.windows)
        or webview.active_window()
        or webview.windows[0]
    )


def copy_untitled(blank: Path, base: Path) -> Path:
    """A fresh untitled document, copied out so the template is never edited.

    Named after the blank it came from, so File > New in Tables makes a
    spreadsheet and not an Untitled.docx that Tables cannot open.
    """
    n = 1
    candidate = base / f"Untitled{blank.suffix}"
    while candidate.exists():
        n += 1
        candidate = base / f"Untitled {n}{blank.suffix}"
    base.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(blank, candidate)
    return candidate


def make_new_document(app: apps.App | None = None) -> Path:
    """The document File > New should make, for the window that asked.

    `app` names the editor when the caller knows it -- the start window asks
    for a spreadsheet from a session that is showing nothing. Without it the
    answer comes from the front window, which is what a menu item means.

    Separate from putting it in a window, and this is the whole reason: the
    decision is the part that has been wrong twice, and a window cannot be
    created in a test.

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


def fold_changes_in(session: Session) -> bool:
    """Put the edits into Editor.bin, so a reload does not undo them.

    The editor works on Editor.bin plus a log of changes it streams as it
    types; a reload hands it Editor.bin alone, which is the document as it was
    opened. Converting out and back in makes the edits part of the base, and
    leaves an empty log -- the same round trip a save does, without a
    destination.

    False when it does not work, and then the edits are still in the log,
    which is what a save merges.
    """
    if not session.change_log:
        return True

    ext, fmt = session.editor.formats[0]
    session.out_dir.mkdir(parents=True, exist_ok=True)
    staged = session.out_dir / f"recovered.{ext}"
    if not convert.export(session, staged, fmt, None):
        logger.error("reload: could not fold in the edits")
        return False
    if not convert.convert_to_editor_bin(session, staged):
        logger.error("reload: could not reopen the folded document")
        return False
    logger.info("reload: folded the edits into %s", staged.name)
    return True


def reload_session(session: Session, port: int) -> None:
    """Rebuild the editor in that window, keeping the edits.

    Folds the change log into Editor.bin first: the editor works on
    Editor.bin plus the log it streams as you type, and a reload hands it
    Editor.bin alone -- the document as it was *opened*. Without the fold,
    reloading would silently undo everything since.

    And not at all when the fold fails. The reloaded editor counts its changes
    from nought again, so its first one would cut the log -- the edits the
    fold could not keep -- back to nothing. The window as it is can still
    save them.
    """
    window = find_window(session)
    if window is None:
        return
    if not fold_changes_in(session):
        msg = "the edits could not be folded into the document"
        raise NotReadyError(msg)
    document = session.read_current_document()
    name = document.name if document else "document"
    window.load_url(server.make_editor_url(port, session, name))

    # Offerable again later, but not for the errors already on their way from
    # the page being torn down.
    def make_offerable_again() -> None:
        session.reload_offered = False

    threading.Timer(5.0, make_offerable_again).start()


def set_fullscreen(on: bool) -> None:
    """Take the front window fullscreen for a demonstration, or give it back.

    A setter, because that is what sdkjs asks for; how closely a toolkit can
    honour one is the toolkit's business.
    """
    window = find_front_window()
    if window is not None:
        native.set_fullscreen(window, on)
