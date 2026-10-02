"""Everything that puts a question on screen and waits for the answer.

The close prompt, the recovery offer, the reload offer, Save As, Open, and a
plain message. What each one asks and what each answer does are decided here,
the same on every platform; drawing them is `native`'s, which `windows` chose.
Above `windows`: a dialog needs a window to hang from.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import webview

from libera.host import saving
from libera.host.session import SESSIONS, NotReadyError, Session
from libera.host.window.portable import Answer, Question, pick_path
from libera.host.window.windows import (
    find_front_window,
    find_window,
    native,
    reload_session,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)


def ask(question: Question) -> Answer:
    """A question, from whichever thread asks, on whichever toolkit is here.

    The front window is its parent where the toolkit has a use for one.
    """
    parent = find_front_window()
    return native.run_on_gui_thread(lambda: native.ask(question, parent))


def say(heading: str, detail: str) -> None:
    """Tell the user something, with one button.

    A menu item that silently does nothing is the hardest kind of bug to
    report, and `show_help` was one: it asked `webbrowser` to open the
    documentation, ignored the False it got back on a machine with no browser,
    and left the user looking at a menu that had apparently done nothing.

    Falls back to a log line rather than raising when the toolkit cannot be
    loaded: GTK's `gi` is imported only when a dialog is built, and is a system
    package a virtualenv may not see. Nothing here is worth failing over.
    """
    try:
        parent = find_front_window()
        native.run_on_gui_thread(lambda: native.tell(heading, detail, parent))
    except (ImportError, ValueError):
        logger.warning("%s: %s", heading, detail)


def ask_to_recover(document: Path) -> bool:
    """Offer back edits that never reached the file.

    Asked before the document is converted, because converting is the step
    that discards the session those edits live in. Called from a request
    thread whenever a window opens a document.
    """
    answer = ask(
        Question(
            f"Recover unsaved changes to “{document.name}”?",
            "Libera Suite has changes to this document that were never saved. "
            "Recover them, or open the document as it is on disk?",
            yes="Recover",
            no="Open Saved Version",
        )
    )
    return answer is Answer.YES


def confirm_close(session_id: str) -> bool:
    """Ask before a window takes unsaved edits with it. False keeps it open.

    The editor is not asked to save: pywebview's evaluate_js hands work to the
    GUI thread and waits, and this runs *on* the GUI thread, so calling it here
    would deadlock. It is not needed either -- Editor.bin and the change log
    the editor streams as you type are both already on disk, which is what the
    host converts from on an ordinary save.
    """
    closing = SESSIONS.get(session_id)
    if closing is None:
        return True
    document = closing.read_current_document()
    if document is None or not closing.unsaved_marker.is_file():
        return True
    return _confirm_close(closing, document)


def _confirm_close(session: Session, document: Path) -> bool:
    """The close prompt, once there are edits to lose. False keeps the window.

    "Don't Save" leaves the unsaved marker where it is, so the edits are
    offered back the next time this document is opened.
    """
    answer = ask(
        Question(
            f"Save changes to “{document.name}” before closing?",
            "Your changes will be lost if you don't save them.",
            yes="Save",
            no="Don't Save",
            cancel="Cancel",
        )
    )
    if answer is Answer.YES:
        return _save_or_say_why(session, document)
    # Cancel, or a dialog dismissed without an answer, keeps the window: the
    # answer that cannot lose anything.
    return answer is Answer.NO


def _save_or_say_why(session: Session, document: Path) -> bool:
    """Save, and answer whether the window may now close.

    A window that closed on a failed save would take the edits with it --
    which is the whole reason this asks at all -- so a failure keeps it open
    and says why.
    """
    # On the GUI thread, so a save that would ask where fails instead.
    saved = saving.save_document(session, {"fileType": 0, "params": ""}, may_ask=False)
    if saved["error"] == saving.SaveOutcome.SAVED:
        return True
    say(
        "Libera Suite could not save the document",
        f"“{document.name}” was not written, so the window has been left open. "
        "Try File ▸ Save As somewhere else.",
    )
    return False


def offer_reload(session: Session, message: str, port: int) -> None:
    """The editor threw. Offer the window back rather than leave it wedged.

    Reloading costs the editor's undo history and where the cursor was, and
    keeps the edits -- so it is an offer, not something done behind the user's
    back. The reload itself belongs to the GUI thread.
    """
    if find_window(session) is None:
        return
    first_line = message.partition("\n")[0][:200]
    answer = ask(
        Question(
            "Libera Suite ran into a problem",
            "The editor stopped working properly and may not respond.\n\n"
            "Reloading keeps your edits. It loses the undo history and where "
            f"the cursor was.\n\n{first_line}",
            yes="Reload",
            no="Leave It",
        )
    )
    if answer is not Answer.YES:
        logger.info("reload declined")
        return
    reload(session, port)


def reload(session: Session, port: int) -> None:
    """Rebuild the editor in that window, or say why it is left as it was."""
    try:
        native.run_on_gui_thread(lambda: reload_session(session, port))
    except NotReadyError:
        say(
            "Libera Suite could not reload the document",
            "Your edits are still in the window. Save them with File ▸ Save, "
            "then reload.",
        )


def ask_save_path(
    suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None
) -> str | None:
    """Where to save: the windowed shell's choose_save_path.

    The formats come from the save, which knows whose document it is. Read
    off the GUI thread's session instead, they were the first window's: Save
    As in a spreadsheet offered a word processor's formats, and wrote a .docx.

    A folder that has gone -- an unmounted drive, a deleted directory -- is
    left to the toolkit, which starts where the last save went.
    """
    if start_in is not None and not start_in.is_dir():
        start_in = None
    return native.run_save_panel(suggested, formats, start_in, find_front_window())


def ask_open_path(_filter: str) -> str | None:
    """What to open: the windowed shell's choose_open_path.

    pywebview's own dialog on every platform: an open dialog wants no format
    popup, so pywebview's lacks nothing.
    """
    window = find_front_window()
    if window is None:
        return None
    return pick_path(window.create_file_dialog(webview.FileDialog.OPEN))
