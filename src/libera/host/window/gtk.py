"""GTK: how Linux asks a question. Everything else is pywebview's.

One of the three toolkit modules `windows` chooses between, each a
`portable.Toolkit`; `portable` supplies all of it here but the two calls
that put a message on screen.

PyGObject is imported where a dialog is built rather than at the top. It is a
system package, so it can be missing wherever this module is merely imported
-- the test tier, `libera --serve` on a headless box -- and only a question on
screen needs it.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from libera.host.window.portable import (
    Answer,
    Question,
    complete_startup,
    find_key_window,
    prepare,
    run_on_gui_thread,
    run_save_panel,
    set_fullscreen,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from webview import Window

__all__ = [
    "ask",
    "complete_startup",
    "find_key_window",
    "prepare",
    "run_on_gui_thread",
    "run_save_panel",
    "set_fullscreen",
    "tell",
]


def ask(question: Question, parent: Window | None) -> Answer:
    """A modal question, laid out as GNOME does: the default rightmost.

    **Not `create_confirmation_dialog`.** pywebview's is two buttons, where
    the close prompt needs three, and it hands the work to the GTK thread and
    waits -- which deadlocks when the caller is already on that thread, as the
    `closing` handler is.
    """
    gtk = _import_gtk()
    yes_id, no_id = int(gtk.ResponseType.YES), int(gtk.ResponseType.NO)
    buttons = [(question.no, no_id)]
    if question.cancel is not None:
        buttons.append((question.cancel, int(gtk.ResponseType.CANCEL)))
    buttons.append((question.yes, yes_id))
    response = _run_dialog(
        question.title, question.message, buttons, parent, asking=True
    )
    return {yes_id: Answer.YES, no_id: Answer.NO}.get(response, Answer.CANCEL)


def tell(title: str, message: str, parent: Window | None) -> None:
    """A message with one button."""
    _run_dialog(
        title,
        message,
        [("OK", int(_import_gtk().ResponseType.OK))],
        parent,
        asking=False,
    )


def _import_gtk() -> Any:
    """Gtk, at the version pywebview's backend asks for."""
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    return Gtk


def _run_dialog(
    title: str,
    message: str,
    buttons: Sequence[tuple[str, int]],
    parent: Window | None,
    *,
    asking: bool,
) -> int:
    """Show a Gtk.MessageDialog where GTK can run it, and return the response.

    `dialog.run()` spins its own nested main loop, so it is safe on the GUI
    thread and only there; a request thread hands it over with idle_add and
    waits for the answer, which is the same shape as run_on_gui_thread on the
    macOS side.

    The questions this asks were macOS-only, and each one said so in a comment
    that ended "nowhere to ask". Two of them cost a user their work: closing a
    window with unsaved edits closed it, and the recovery offer that was
    supposed to catch that never appeared either, so the edits sat in the
    session directory with nothing to surface them.
    """
    gtk = _import_gtk()
    from gi.repository import GLib

    answer: list[int] = []
    done = threading.Event()

    def show() -> bool:
        dialog = gtk.MessageDialog(
            transient_for=getattr(parent, "native", None),
            modal=True,
            message_type=gtk.MessageType.QUESTION if asking else gtk.MessageType.INFO,
            text=title,
            secondary_text=message,
        )
        for label, response_id in buttons:
            dialog.add_button(label, response_id)
        dialog.set_default_response(buttons[-1][1])
        try:
            answer.append(int(dialog.run()))
        finally:
            dialog.destroy()
        done.set()
        return False  # idle_add repeats until its callback says otherwise

    if threading.current_thread() is threading.main_thread():
        # webview.start() runs the GTK loop on the main thread, so this is it.
        show()
    else:
        GLib.idle_add(show)
        # No timeout: a question is answered when somebody answers it, and the
        # macOS alert on the other side of this blocks in exactly the same way.
        done.wait()
    return answer[0] if answer else int(gtk.ResponseType.DELETE_EVENT)
