"""The menu bar, on every platform.

    actions   what an item does when it fires, and whether it is available
    macos     AppKit's bar, extended once the application runs
    gtk       pywebview's bar, for Linux and Windows

`macos` and `gtk` read `actions`; nothing goes the other way. They share every
item's behaviour and no code beyond it. AppKit wants selectors on an NSObject
and a delegate that rebuilds Open Recent on each opening; pywebview wants a
list of its own `Menu` objects handed to `start()` before the application
runs. Neither shape holds up once made to look like the other.

`native` is the one this platform uses, chosen here and nowhere else. Both
answer `make_menubar()`, what to hand `webview.start`, `install()`, what to do
once the application runs, and `show_keys()`, what to do to each window's bar.

The key equivalents and PAGE_YIELDS are in `host/shortcuts.py`: two modules
on either side of this one need them, and `server` reaching up here for
PAGE_YIELDS was half of a cycle.
"""

from __future__ import annotations

import sys

from libera.host.menu.actions import is_enabled

if sys.platform == "darwin":
    from libera.host.menu import macos as native
else:
    from libera.host.menu import gtk as native

__all__ = [
    "is_enabled",
    "native",
]
