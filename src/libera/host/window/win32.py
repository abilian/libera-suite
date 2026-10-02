"""Win32: how Windows asks a question. Everything else is pywebview's.

One of the three toolkit modules `windows` chooses between, each a
`portable.Toolkit`; `portable` supplies all of it here but the two calls
that put a message on screen.

A Win32 message box has Yes, No, Cancel and OK and no other buttons -- the
dialog that takes custom labels needs Common Controls v6, which python.exe
does not declare -- so under the question it says what each button means, in
the words the other platforms put on the buttons themselves: "Yes: Save".
Every question asked here reads as one; "Save changes to Report.docx before
closing?" Yes, No, Cancel is the classic Windows form of it.
"""

from __future__ import annotations

import ctypes
import sys
from typing import TYPE_CHECKING

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

# MessageBoxW's styles and answers, which Python does not name.
MB_OK, MB_YESNOCANCEL, MB_YESNO = 0x0, 0x3, 0x4
MB_ICONQUESTION, MB_ICONWARNING, MB_ICONINFORMATION = 0x20, 0x30, 0x40
MB_SETFOREGROUND = 0x10000
IDOK, IDCANCEL, IDYES, IDNO = 1, 2, 6, 7


def ask(question: Question, parent: Window | None) -> Answer:
    """MessageBoxW: Yes, No and, when there is one, Cancel, each explained."""
    choices = [
        ("Yes", question.yes, IDYES, Answer.YES),
        ("No", question.no, IDNO, Answer.NO),
    ]
    if question.cancel is not None:
        choices.append(("Cancel", question.cancel, IDCANCEL, Answer.CANCEL))
    legend = "    ".join(f"{button}: {label}" for button, label, _, _ in choices)
    style = (
        MB_YESNOCANCEL | MB_ICONWARNING
        if question.cancel is not None
        else MB_YESNO | MB_ICONQUESTION
    )
    text = f"{question.title}\n\n{question.message}\n\n{legend}"
    clicked = _show_message_box(text, style, parent)
    return next((answer for _, _, i, answer in choices if i == clicked), Answer.CANCEL)


def tell(title: str, message: str, parent: Window | None) -> None:
    """MessageBoxW with OK."""
    _show_message_box(f"{title}\n\n{message}", MB_OK | MB_ICONINFORMATION, parent)


def _show_message_box(text: str, style: int, parent: Window | None) -> int:
    """MessageBoxW, owned by the parent window so that it is modal to it.

    Safe from any thread: MessageBoxW runs its own message loop, on the GUI
    thread and off it, so this needs none of the hand-over GTK and AppKit do.
    """
    # For the type checkers as much as the runtime: `make lint` checks this
    # module for every platform, and `ctypes.windll` exists on one. A block
    # and not an early return, because pyrefly narrows on the first only.
    if sys.platform == "win32":
        owner = None
        handle = getattr(getattr(parent, "native", None), "Handle", None)
        if handle is not None:
            owner = int(handle.ToInt64())
        return ctypes.windll.user32.MessageBoxW(
            owner, text, "Libera Suite", style | MB_SETFOREGROUND
        )
    return IDCANCEL
