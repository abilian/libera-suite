"""The menu bar, on every platform.

    actions   what an item does when it fires, and whether it is available
    macos     AppKit's bar, extended once the application runs
    gtk       pywebview's bar, for Linux and Windows

`macos` and `gtk` read `actions`; nothing goes the other way. They share every
item's behaviour and no code beyond it: AppKit wants selectors on an NSObject
and a delegate that rebuilds Open Recent on each opening, pywebview wants a
list of its own `Menu` objects handed to `start()` before the application
runs, and neither shape survives being made to look like the other.

`native` is the one this platform uses, chosen here and nowhere else. Both
answer `make_menubar()`, what to hand `webview.start`, and `install()`, what to do
once the application runs.

COMMAND, SHIFT, Shortcut, NEW and PAGE_YIELDS come from `host/shortcuts.py`:
two modules on either side of this one need them, and `server` reaching up
here for PAGE_YIELDS was half of a cycle. Re-exported, so `menu.PAGE_YIELDS`
still reads the way it always did.
"""

from __future__ import annotations

import sys

from libera.host.menu.actions import (
    HELP_URL,
    is_enabled,
)
from libera.host.shortcuts import COMMAND, NEW, PAGE_YIELDS, SHIFT, Shortcut

if sys.platform == "darwin":
    from libera.host.menu import macos as native
else:
    from libera.host.menu import gtk as native

__all__ = [
    "COMMAND",
    "HELP_URL",
    "NEW",
    "PAGE_YIELDS",
    "SHIFT",
    "Shortcut",
    "is_enabled",
    "native",
]
