"""What every toolkit answers, and what pywebview answers the same everywhere.

The bottom of the window package. Three toolkit modules draw windows and
dialogs -- `macos`, `gtk`, `win32` -- and `windows` picks one of them, once, as
`native`, typed as the `Toolkit` below: `make lint` checks each platform's
module against it on that platform's pass.

AppKit has an answer of its own to every call. GTK and Win32 differ only in
how they ask a question, and take the rest from here: pywebview's own file
dialog and fullscreen toggle, and its own hand-over to the GUI thread.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeVar

import webview

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from webview import Window


T = TypeVar("T")


class Answer(enum.Enum):
    """What somebody said to a question.

    Named for what it means rather than where the button was, because the
    toolkits do not agree on where buttons go: macOS puts Cancel between Save
    and Don't Save, GNOME puts the default rightmost, and a Win32 message box
    has Yes, No and Cancel and nothing else. A dialog dismissed without an
    answer -- Escape, or the window manager -- is CANCEL.
    """

    YES = "yes"
    NO = "no"
    CANCEL = "cancel"


@dataclass(frozen=True)
class Question:
    """What to ask, and what to call each answer, the same on every platform.

    `cancel` is the third choice where there is one -- the close prompt's --
    and absent from a yes-or-no question.
    """

    title: str
    message: str
    yes: str
    no: str
    cancel: str | None = None


class Toolkit(Protocol):
    """What a toolkit module answers. A module, not a class: there is one of
    each, and the type checkers hold a module to a Protocol as readily."""

    def run_on_gui_thread(self, work: Callable[[], T]) -> T:
        """Run work where the toolkit wants it, and return its answer."""

    def find_key_window(self, windows: Sequence[Window]) -> Window | None:
        """The window the toolkit says is in front, if it says."""

    def set_fullscreen(self, window: Window, on: bool) -> None:
        """A demonstration, on or off."""

    def ask(self, question: Question, parent: Window | None) -> Answer:
        """The question, drawn the toolkit's way."""

    def tell(self, title: str, message: str, parent: Window | None) -> None:
        """A message with one button."""

    def run_save_panel(
        self,
        suggested: str,
        formats: Sequence[tuple[str, str]],
        start_in: Path | None,
        parent: Window | None,
    ) -> str | None:
        """Where to save, starting in `start_in`, or None if cancelled."""

    def prepare(self) -> None:
        """What the toolkit reads once, before the application exists."""

    def complete_startup(self, then: Callable[[], None]) -> None:
        """Once the application runs: `then`, which installs the menus."""


def run_on_gui_thread(work: Callable[[], T]) -> T:
    """Run it here.

    pywebview's GTK and WinForms backends marshal their own calls onto the GUI
    thread, and what this application asks those toolkits directly -- a GTK
    dialog, MessageBoxW -- sees to its own thread.
    """
    return work()


def find_key_window(windows: Sequence[Window]) -> Window | None:
    """Nothing beyond pywebview's own active_window(), which is asked next."""
    return None


def set_fullscreen(window: Window, on: bool) -> None:
    """Toggle: pywebview has nothing to read the state from, so a toggle is
    all there is, and sdkjs's explicit on and off cannot be honoured.

    Not for a window pywebview has not finished making: its methods wait for
    the window to be shown, and this is called from a request.
    """
    if window.native is not None:
        window.toggle_fullscreen()


def run_save_panel(
    suggested: str,
    formats: Sequence[tuple[str, str]],
    start_in: Path | None,
    parent: Window | None,
) -> str | None:
    """pywebview's save dialog. It takes no format list, so the name decides."""
    if parent is None:
        return None
    return pick_path(
        parent.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=str(start_in) if start_in else "",
            save_filename=suggested,
        )
    )


def pick_path(chosen: Sequence[str] | None) -> str | None:
    """What create_file_dialog returns, as one path or none.

    pywebview types it `Sequence[str] | None` and a `str` satisfies that, so
    the isinstance is doing real work: a save dialog answers with the path
    itself and an open dialog with a tuple of them.
    """
    if not chosen:
        return None
    return chosen if isinstance(chosen, str) else chosen[0]


def prepare() -> None:
    """Nothing to do before the application exists."""


def complete_startup(then: Callable[[], None]) -> None:
    """Run it: pywebview calls this as the GUI loop starts, and there is
    nothing else to wait for."""
    then()
