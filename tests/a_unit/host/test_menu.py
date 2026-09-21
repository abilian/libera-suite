"""A menu item wired to a selector nobody implements does nothing, silently.

That is the hardest kind of bug to notice and the easiest to introduce: rename
a method, or mistype a selector, and the item stays in the menu looking
perfectly normal.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

from libera.host import menu

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="the menu bar is macOS only"
)

# Sent to the responder chain rather than to us: AppKit or the web view
# implements them, and they must have no target.
STANDARD = ("perform", "toggle", "arrangeInFront", "submenuAction")


def selectors_the_menu_uses() -> set[str]:
    """Every selector named anywhere in the menu package.

    The whole package, not `menu.__file__`: that is `__init__.py` now and
    names no selectors at all, so reading it would have found none and the
    check would have passed by being empty. test_there_are_actually_some_to_check
    is the guard that would have caught it -- this is the fix it asks for.
    """
    package = pathlib.Path(menu.__file__).parent
    source = "".join(
        f.read_text(encoding="utf-8") for f in sorted(package.glob("*.py"))
    )
    found = set(re.findall(r'"(\w+:)"', source))
    return {s for s in found if not s.startswith(STANDARD)}


def test_the_target_answers_every_selector_the_menu_sends_it():
    target = menu.actions.target_class().alloc().init()
    missing = [
        s for s in selectors_the_menu_uses() if not target.respondsToSelector_(s)
    ]
    assert not missing, f"menu items wired to nothing: {missing}"


def test_there_are_actually_some_to_check():
    """Guard the guard: a regex that matches nothing would pass silently."""
    assert len(selectors_the_menu_uses()) >= 8


def test_the_recent_menu_delegate_answers_appkit():
    delegate = menu.actions.recent_delegate_class().alloc().init()
    assert delegate.respondsToSelector_("menuNeedsUpdate:")


def test_the_target_validates_its_own_items():
    """Save, Undo and Redo decline silently when there is nothing to do, so
    the menu has to say so before the user presses them."""
    target = menu.actions.target_class().alloc().init()
    assert target.respondsToSelector_("validateMenuItem:")
