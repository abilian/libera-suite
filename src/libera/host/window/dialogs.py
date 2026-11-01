"""Everything that puts a question on screen and waits for the answer.

The close prompt, the recovery offer, the reload offer, Save As, Open, and a
plain message. This module decides what each one asks and what each answer
does, the same on every platform; `native`, which `windows` chose, draws them.
Above `windows`: a dialog needs a window to hang from.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import webview

from libera.host import language, saving
from libera.host.convert import ConversionError
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

    The front window is its parent where the toolkit has a use for one, and
    is looked up on the GUI thread too: asking AppKit which window is key is
    as main-thread-only as the dialog.
    """
    return native.run_on_gui_thread(lambda: native.ask(question, find_front_window()))


def say(heading: str, detail: str) -> None:
    """Tell the user something, with one button.

    A menu item that does nothing without a word is the hardest kind of bug
    to report. `show_help` was one: it asked `webbrowser` to open the
    documentation, ignored the False it got back on a machine with no browser,
    and left the user looking at a menu that had apparently done nothing.

    Falls back to a log line when the toolkit cannot be loaded: GTK's `gi` is
    imported only when a dialog is built, and is a system package a virtualenv
    may not see. A message that cannot be shown is no reason to raise.
    """
    try:
        native.run_on_gui_thread(
            lambda: native.tell(heading, detail, find_front_window())
        )
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
            language.translate(
                "Recover unsaved changes to “{name}”?", name=document.name
            ),
            language.translate(
                "Libera Suite has changes to this document that were never saved. "
                "Recover them, or open the document as it is on disk?"
            ),
            yes=language.translate("Recover"),
            no=language.translate("Open Saved Version"),
        )
    )
    return answer is Answer.YES


def confirm_close(session_id: str) -> bool:
    """Ask before a window takes unsaved edits with it. False keeps it open.

    The editor is not asked to save: pywebview's evaluate_js hands its call to
    the GUI thread and waits. This runs *on* the GUI thread, so calling it here
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
            language.translate(
                "Save changes to “{name}” before closing?", name=document.name
            ),
            language.translate("Your changes will be lost if you don't save them."),
            yes=language.translate("Save"),
            no=language.translate("Don't Save"),
            cancel=language.translate("Cancel"),
        )
    )
    if answer is Answer.YES:
        return _save_or_say_why(session, document)
    # Cancel, or a dialog dismissed without an answer, keeps the window: the
    # answer that cannot lose anything.
    return answer is Answer.NO


def _save_or_say_why(session: Session, document: Path) -> bool:
    """Save, and answer whether the window may now close.

    A window that closed on a failed save would take with it the edits this
    prompt is there to keep, so a failure keeps it open and says why.
    """
    # On the GUI thread, so a save that would ask where fails instead.
    saved = saving.save_document(session, saving.PLAIN_SAVE, may_ask=False)
    if saved["error"] == saving.SaveOutcome.SAVED:
        return True
    say(
        language.translate("Libera Suite could not save the document"),
        language.translate(
            "“{name}” was not written, so the window has been left open. "
            "Try {save_as} somewhere else.",
            name=document.name,
            save_as=f"{language.translate('File')} ▸ {language.translate('Save As…')}",
        ),
    )
    return False


def offer_reload(session: Session, message: str, port: int) -> None:
    """The editor threw and may have wedged the window: offer to reload it.

    Reloading costs the editor's undo history and where the cursor was, while
    keeping the edits, so the user decides. The reload itself belongs to the
    GUI thread.
    """
    if find_window(session) is None:
        return
    first_line = message.partition("\n")[0][:200]
    answer = ask(
        Question(
            language.translate("Libera Suite ran into a problem"),
            language.translate(
                "The editor stopped working properly and may not respond.\n\n"
                "Reloading keeps your edits. It loses the undo history and where "
                "the cursor was.\n\n{error}",
                error=first_line,
            ),
            yes=language.translate("Reload"),
            no=language.translate("Leave It"),
        )
    )
    if answer is not Answer.YES:
        logger.info("reload declined")
        return
    reload(session, port)


def reload(session: Session, port: int) -> None:
    """Rebuild the editor in that window, or say why it is left as it was.

    On the calling thread, which is never the GUI thread: the menu runs it in
    the background and the reload offer comes from a request. The fold runs
    x2t twice, and on the GUI thread it froze every window for that long;
    pywebview hands `load_url` to the GUI thread itself.
    """
    try:
        reload_session(session, port)
    except (ConversionError, NotReadyError):
        say(
            language.translate("Libera Suite could not reload the document"),
            language.translate(
                "Your edits are still in the window. Save them with {save}, "
                "then reload.",
                save=f"{language.translate('File')} ▸ {language.translate('Save')}",
            ),
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
    # The parent is found on the GUI thread; the panel hands itself over and
    # waits, so it must not be called from there.
    parent = native.run_on_gui_thread(find_front_window)
    return native.run_save_panel(suggested, formats, start_in, parent)


def ask_open_path(_filter: str) -> str | None:
    """What to open: the windowed shell's choose_open_path.

    pywebview's own dialog on every platform: an open dialog wants no format
    popup, so pywebview's lacks nothing.
    """
    window = native.run_on_gui_thread(find_front_window)
    if window is None:
        return None
    return pick_path(window.create_file_dialog(webview.FileDialog.OPEN))
