"""What the host asks of whoever owns the windows.

A file dialog needs a window to hang from; a second document needs a window
to go in. The HTTP host knows nothing about either, so it asks `shell`.

`shell` starts as `HeadlessShell`, which is what `libera --serve` and the regression
harness run with: one window, no way to make another, no one to ask. `app.run`
replaces it with one that has windows. Read it through the module
(`hooks.shell`), never imported by name: `from .hooks import shell` would keep
the headless one after run() has replaced it.

A headless shell mostly declines -- no file chosen, nothing recovered, nothing
offered. Where having no window changes what the host itself does -- a
document opened in place, a save that goes into the session -- the caller
says so on `shell.windowed`, rather than leave it to a default no one sees.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from libera.host.apps import App
    from libera.host.session import Session

logger = logging.getLogger(__name__)


class Shell(Protocol):
    """What the host asks of whoever owns the windows."""

    # Whether there are windows at all, and so a menu bar and dialogs.
    windowed: bool

    def open_window(self, document: Path | None, app: App | None = None) -> bool:
        """A document in a window of its own. None is a new one of `app`'s kind.

        Whether it is on screen. When it is not, the user has been told why.
        """

    def show_start_window(self) -> None:
        """The start window: a second launch with no document asked for it."""

    def choose_save_path(
        self, suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None
    ) -> str | None:
        """Where to save, as one of `formats`, or None if the user cancelled.

        Starting in `start_in`, or where the toolkit chooses when it is None.
        """

    def choose_open_path(self, kind: str) -> str | None:
        """What to open, or None if the user cancelled."""

    def set_fullscreen(self, on: bool) -> None:
        """Slides, starting or ending a demonstration."""

    def close_window(self, session: Session) -> None:
        """The editor's File > Close: close that window, asking about unsaved
        changes as its close button does."""

    def offer_reload(self, session: Session, message: str) -> None:
        """The editor threw where nothing caught it: offer to rebuild it."""

    def reload(self, session: Session) -> None:
        """File > Reload: rebuild the editor in that window, keeping the edits."""

    def ask_to_recover(self, document: Path) -> bool:
        """Whether to open the edits that never reached this document's file."""

    def tell(self, heading: str, detail: str) -> None:
        """Something the user should know, with nothing to decide."""

    def show_edited(self, session: Session, edited: bool) -> None:
        """Mark that session's window as holding unsaved edits, or not."""

    def take_dropped(self, names: list[str]) -> list[Path]:
        """The full paths of files just dropped on a window, which the page
        knows only by name. Those it cannot account for are left out."""


class HeadlessShell:
    """No windows and no one to ask.

    Every answer is the one that changes nothing. Recovery in particular stays
    off: a check that sometimes resumes the previous run is not a check.
    """

    windowed = False

    def open_window(self, document: Path | None, app: App | None = None) -> bool:
        logger.info("no window to open %s in", document or "a new document")
        return False

    def show_start_window(self) -> None:
        logger.info("no start window to show")

    def choose_save_path(
        self, suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None
    ) -> str | None:
        return None

    def choose_open_path(self, kind: str) -> str | None:
        return None

    def set_fullscreen(self, on: bool) -> None:
        pass

    def close_window(self, session: Session) -> None:
        logger.warning("close: no window to close")

    def offer_reload(self, session: Session, message: str) -> None:
        pass

    def reload(self, session: Session) -> None:
        logger.warning("reload: no window to reload")

    def ask_to_recover(self, document: Path) -> bool:
        return False

    def tell(self, heading: str, detail: str) -> None:
        logger.warning("%s: %s", heading, detail)

    def show_edited(self, session: Session, edited: bool) -> None:
        pass

    def take_dropped(self, names: list[str]) -> list[Path]:
        return []


shell: Shell = HeadlessShell()
