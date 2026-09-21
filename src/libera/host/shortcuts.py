"""Key equivalents the native menu bar owns, and the page must not act on.

The lowest layer that has anything to do with the menu, and it is here rather
than in `menu.py` because two modules need it and they sit on either side of
that one: `server._get_bridge` injects the list into the page, and the menu
builds its items from it.

With the definition in `menu.py`, `server` reached upward for it with a
function-level import -- one of six that held a cycle apart. See
`host/__init__.py` for the order these modules are allowed to import in.
"""

from __future__ import annotations

from dataclasses import dataclass

# NSEventModifierFlagCommand and ...Shift, which pyobjc builds at import time
# and a checker cannot see. Written out because this module must not import
# AppKit: it is read on every platform, and only used on one.
COMMAND = 1 << 20
SHIFT = 1 << 17


@dataclass(frozen=True)
class Shortcut:
    """A key equivalent, in the two forms that need to agree.

    AppKit wants a character and a modifier mask; the page wants to recognise
    the same keystroke in a DOM event. Defining it once is the point -- see
    PAGE_YIELDS.
    """

    key: str
    shift: bool = False

    @property
    def mask(self) -> int:
        return COMMAND | SHIFT if self.shift else COMMAND

    def as_json(self) -> dict:
        return {"key": self.key, "shift": self.shift}


NEW = Shortcut("n")

# Key equivalents the page must not act on, because AppKit already does.
#
# A menu item's key fires whether or not the page also handles it: the web view
# is offered the event first, declines anything that is not a standard editing
# command, and the menu then fires too. Both ends of File > New make a window,
# so Cmd-N made two.
#
# The host injects this list into the page (server._get_bridge), and
# bridge-page.js yields exactly what is here. One definition, two readers:
# change the menu's shortcut and the page follows, which is the drift this
# exists to make impossible.
#
# Only what has been seen to double belongs here. The Edit-menu keys -- Cmd-Z,
# Cmd-C and the rest -- are claimed by the web view and never reach the menu.
PAGE_YIELDS: tuple[Shortcut, ...] = (NEW,)
