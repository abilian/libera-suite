"""Callbacks the window layer installs, and the host calls.

A file dialog needs a window to hang from, and a second document needs
somewhere to put it -- neither of which the HTTP host knows anything about. It
asks through these instead.

They are read through the module (`hooks.SAVE_PATH_CHOOSER`), never imported
by name: `from .hooks import SAVE_PATH_CHOOSER` would bind whatever None was
there at import time and never see the real one.

All None is a valid state: `libera --serve` and the regression harness have one
window and no way to make another, and both behave accordingly.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from libera.host.apps import App


# Each of these is "that callback, or nobody installed one". Spelling it out
# matters more than it looks: declared as a bare `= None`, the inferred type of
# every hook is None -- so a checker reads `hooks.SAVE_PATH_CHOOSER = chooser`
# as assigning a function to a None, and `if hooks.SAVE_PATH_CHOOSER:` as a
# condition that is always false. Fourteen diagnostics came from that, and they
# hid the ones that meant something.
class WindowOpener(Protocol):
    """Put a document on screen in a window of its own.

    A Protocol rather than a Callable alias, because the editor asks for a
    window in two ways -- `WINDOW_OPENER(path)` from a menu, and
    `WINDOW_OPENER(None, app)` from the start window -- and
    `Callable[[A, B], None]` has no way to say that the second is optional.
    """

    def __call__(self, document: Path | None, app: App | None = None) -> None: ...


PathChooser = Callable[[str], str | None]
Fullscreen = Callable[[bool], None]
Reload = Callable[[str], None]
Broken = Callable[[str, str], None]
RecoveryChooser = Callable[[Path], bool]

# Set by whoever owns windows, so the host can ask for another one. None means
# there is nowhere to put a second document -- the harness, or `libera --serve`
# -- and File > Open replaces what is open, as it used to.
WINDOW_OPENER: WindowOpener | None = None


# File dialogs need a window, so the host installs them here; run.sh check
# leaves them None (saves to a fixed path, picks no file, never recovers).
#   SAVE_PATH_CHOOSER(suggested_name) -> chosen path, or None if cancelled
#   OPEN_PATH_CHOOSER(filter)         -> chosen path, or None if cancelled
SAVE_PATH_CHOOSER: PathChooser | None = None


OPEN_PATH_CHOOSER: PathChooser | None = None


# Slides takes the window fullscreen for a demonstration and gives it back
# afterwards. A setter rather than a toggle, because sdkjs sends true and
# false explicitly. None means the window cannot do it -- `libera --serve`
# has no window -- and the slideshow runs in the window it has.
FULLSCREEN: Fullscreen | None = None


# Rebuild the editor in a window that has stopped behaving, keeping the edits.
# The way out when the editor has wedged and said so itself, which is when the
# host stays quiet -- see server.broken.
#   RELOAD(session) -> None
RELOAD: Reload | None = None


# Called when the editor throws where nobody caught it, so its state is no
# longer trustworthy. The window layer offers to reload; None means nobody can
# ask, and the error is only logged -- which is what `libera --serve` wants.
#   BROKEN(session, message) -> None
BROKEN: Broken | None = None


# Asked before a session is thrown away, when it still holds unsaved edits.
# None means never recover, which is what the harness wants: a check that
# sometimes resumes the previous run is not a check.
RECOVERY_CHOOSER: RecoveryChooser | None = None
