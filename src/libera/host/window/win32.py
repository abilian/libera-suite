"""Win32: how Windows asks a question. Everything else is pywebview's.

One of the three toolkit modules `windows` chooses between, each a
`portable.Toolkit`; `portable` supplies all of it here but the two calls
that put a message on screen.

A Win32 message box has Yes, No, Cancel and OK and no other buttons. The
dialog that takes custom labels needs Common Controls v6, which python.exe
does not declare. Under the question, the box therefore says what each button
means, in the words the other platforms put on the buttons themselves:
"Yes: Save".
Every question asked here reads as one; "Save changes to Report.docx before
closing?" Yes, No, Cancel is the classic Windows form of it.
"""

from __future__ import annotations

import ctypes
import sys
from typing import TYPE_CHECKING, Any

from libera.host import language
from libera.host.window import portable
from libera.host.window.portable import (
    Answer,
    Question,
    close_window,
    complete_startup,
    find_key_window,
    on_quit,
    prepare,
    run_on_gui_thread,
    run_save_panel,
    set_fullscreen,
    show_edited,
    stay_open,
)

if TYPE_CHECKING:
    from webview import Window
    from webview.guilib import GUIType

__all__ = [
    "GUI",
    "ask",
    "close_window",
    "complete_startup",
    "find_key_window",
    "make_window",
    "on_quit",
    "prepare",
    "run_on_gui_thread",
    "run_save_panel",
    "set_fullscreen",
    "show_edited",
    "stay_open",
    "tell",
]

# MessageBoxW's styles and answers, which Python does not name.
MB_OK, MB_YESNOCANCEL, MB_YESNO = 0x0, 0x3, 0x4
MB_ICONQUESTION, MB_ICONWARNING, MB_ICONINFORMATION = 0x20, 0x30, 0x40
MB_SETFOREGROUND = 0x10000

IDOK, IDCANCEL, IDYES, IDNO = 1, 2, 6, 7

GUI: GUIType = "edgechromium"


def make_window(
    title: str, url: str, width: int, height: int, *, tabs: bool
) -> Window | None:
    """pywebview's, kept on the screen: it scales the size it is given by the
    display's and places the window where Windows would next, and neither looks
    at what fits. At 150% on 1920x1080 the close button was off the screen."""
    window = portable.make_window(title, url, width, height, tabs=tabs)
    if window is None:
        return None
    if window.native is None:
        # The first: listed for start() to make. On the form's own thread, before
        # it is shown.
        window.events.before_show += lambda: _keep_on_screen(window.native)
    else:
        # Any later one: create_window has made and shown it already.
        _keep_shown_form_on_screen(window.native)
    return window


def _keep_shown_form_on_screen(form: Any) -> None:
    if sys.platform == "win32":
        from System import Action

        form.Invoke(Action(lambda: _keep_on_screen(form)))


def _keep_on_screen(form: Any) -> None:
    if sys.platform == "win32":
        # Here, because this module is imported on every platform for `make
        # lint` and the tests, and pywebview has loaded the assembly by now.
        from System.Windows.Forms import FormStartPosition, Screen

        area = Screen.FromControl(form).WorkingArea
        bounds = form.Bounds
        x, y, width, height = fit_on_screen(
            (bounds.X, bounds.Y, bounds.Width, bounds.Height),
            (area.X, area.Y, area.Width, area.Height),
        )
        # Or showing the form places it again.
        form.StartPosition = FormStartPosition.Manual
        form.SetBounds(x, y, width, height)


def fit_on_screen(
    bounds: tuple[int, int, int, int], area: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """A window's x, y, width and height, shrunk and then moved only as far as
    it takes to lie inside the area, which is given the same way."""
    x, y, width, height = bounds
    left, top, area_width, area_height = area
    width, height = min(width, area_width), min(height, area_height)
    return (
        max(left, min(x, left + area_width - width)),
        max(top, min(y, top + area_height - height)),
        width,
        height,
    )


def ask(question: Question, parent: Window | None) -> Answer:
    """MessageBoxW: Yes, No and, when there is one, Cancel, each explained.

    Windows names its stock buttons in its interface language, the first of
    the ones `language` asks for, so the legend names them in ours.
    """
    choices = [
        (language.translate("Yes"), question.yes, IDYES, Answer.YES),
        (language.translate("No"), question.no, IDNO, Answer.NO),
    ]
    if question.cancel is not None:
        choices.append((
            language.translate("Cancel"),
            question.cancel,
            IDCANCEL,
            Answer.CANCEL,
        ))
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
