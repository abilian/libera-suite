"""What every toolkit answers, with pywebview's answers where they hold everywhere.

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
    from webview.guilib import GUIType


T = TypeVar("T")


class Answer(enum.Enum):
    """What somebody said to a question.

    Named for what it means rather than where the button was, because the
    toolkits do not agree on where buttons go. macOS puts Cancel between Save
    and Don't Save, GNOME puts the default rightmost, and a Win32 message box
    has Yes, No and Cancel and nothing else. A dialog dismissed without an
    answer (Escape, or the window manager) is CANCEL.
    """

    YES = "yes"
    NO = "no"
    CANCEL = "cancel"


@dataclass(frozen=True)
class Question:
    """What to ask and what to call each answer, the same on every platform.

    `cancel` is the third choice where there is one (the close prompt's), and
    absent from a yes-or-no question.
    """

    title: str
    message: str
    yes: str
    no: str
    cancel: str | None = None


class Toolkit(Protocol):
    """What a toolkit module answers. Each toolkit is a module, one of each;
    the type checkers hold a module to a Protocol as readily as a class."""

    # pywebview's backend for this toolkit, named rather than guessed: left to
    # itself pywebview tries Qt first in a KDE session, which we do not ship,
    # and every launch on Plasma printed Qt's import traceback before GTK.
    GUI: GUIType

    def run_on_gui_thread(self, work: Callable[[], T]) -> T:
        """Run work where the toolkit wants it, and return its answer."""

    def make_window(
        self, title: str, url: str, width: int, height: int, *, tabs: bool
    ) -> Window | None:
        """pywebview's create_window, made where the toolkit can make it.

        `tabs` says whether the window may join a tab group, where the
        toolkit has them."""

    def find_key_window(self, windows: Sequence[Window]) -> Window | None:
        """The window the toolkit says is in front, if it says."""

    def set_fullscreen(self, window: Window, on: bool) -> None:
        """A demonstration, on or off."""

    def close_window(self, window: Window) -> None:
        """Close it as its close button does: asking first about unsaved changes."""

    def show_edited(self, window: Window, edited: bool) -> None:
        """Mark the window's document as having unsaved edits, or not."""

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

    def on_quit(self, work: Callable[[], None]) -> None:
        """Run `work` when the application quits without start() returning."""

    def stay_open(self) -> None:
        """Once start() has returned: keep the application running, where that
        is the platform's way, until it quits."""


def run_on_gui_thread(work: Callable[[], T]) -> T:
    """Run it here.

    pywebview's GTK and WinForms backends marshal their own calls onto the GUI
    thread. What this application asks those toolkits directly (a GTK dialog,
    MessageBoxW) sees to its own thread.
    """
    return work()


def make_window(
    title: str, url: str, width: int, height: int, *, tabs: bool
) -> Window | None:
    """pywebview's own, which has no tabs, so `tabs` changes nothing."""
    del tabs
    return webview.create_window(title, url, width=width, height=height)


def find_key_window(windows: Sequence[Window]) -> Window | None:
    """Nothing beyond pywebview's own active_window(), which is asked next."""
    return None


def set_fullscreen(window: Window, on: bool) -> None:
    """Toggle: pywebview has nothing to read the state from, so a toggle is
    all there is, and sdkjs's explicit on and off cannot be honoured.

    Not for a window pywebview has not finished making: its methods wait for
    the window to be shown, while this is called from a request.
    """
    if window.native is not None:
        window.toggle_fullscreen()


def close_window(window: Window) -> None:
    """pywebview's destroy(), which on GTK emits delete-event and with it the
    `closing` event `app.run` wired to confirm_close: the question about
    unsaved changes comes by the same path as the title bar's button.
    """
    window.destroy()


# The mark of unsaved edits in a title on Linux and Windows: gedit, Notepad.
EDITED_MARK = "*"


def show_edited(window: Window, edited: bool) -> None:
    """A leading * in the title, the convention of both."""
    base = window.title.removeprefix(EDITED_MARK)
    window.set_title(f"{EDITED_MARK}{base}" if edited else base)


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
    """Run it: pywebview calls this as the GUI loop starts, with nothing else
    left to wait for."""
    then()


def on_quit(work: Callable[[], None]) -> None:
    """Nothing: there is no Quit but closing the last window, after which
    start() returns and its caller does the rest."""


def stay_open() -> None:
    """Nothing: closing the last window is quitting, here."""
