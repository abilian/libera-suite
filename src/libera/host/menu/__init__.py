"""The menu bar, on both platforms.

    actions   what an item does when it fires, and whether it is available
    build     putting the macOS bar together at startup
    gtk       the same bar for pywebview, on Linux

`build` and `gtk` read `actions`; nothing goes the other way. They share every
item's behaviour and no code beyond it: AppKit wants selectors on an NSObject
and a delegate that rebuilds Open Recent on each opening, pywebview wants a
list of its own `Menu` objects handed to `start()` before the application
runs, and neither shape survives being made to look like the other.

COMMAND, SHIFT, Shortcut, NEW and PAGE_YIELDS come from `host/shortcuts.py`:
two modules on either side of this one need them, and `server` reaching up
here for PAGE_YIELDS was half of a cycle. Re-exported, so `menu.PAGE_YIELDS`
still reads the way it always did.
"""

from __future__ import annotations

from libera.host.menu.actions import (
    HELP_URL,
    enabled_for,
)
from libera.host.menu.build import install, name_the_application, quieten_system_items
from libera.host.menu.gtk import menubar as gtk_menubar
from libera.host.shortcuts import COMMAND, NEW, PAGE_YIELDS, SHIFT, Shortcut

__all__ = [
    "COMMAND",
    "HELP_URL",
    "NEW",
    "PAGE_YIELDS",
    "SHIFT",
    "Shortcut",
    "enabled_for",
    "gtk_menubar",
    "install",
    "name_the_application",
    "quieten_system_items",
]
