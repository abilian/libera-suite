"""Whether a menu item is available, decided without AppKit.

This lived inside validateMenuItem_ on a pyobjc class, where it did this:

    session = find_front_session()          # a str
    host = session.SESSIONS.get(session)

-- a local shadowing the imported `session` module, so every Undo, Redo and
Save validation raised AttributeError. Inside an ObjC callback, where nobody
reads the exception, the only symptom was menu items behaving oddly.

`ty` found it. These tests keep it found: they need no menu, no window and no
macOS, so they run everywhere.
"""

from __future__ import annotations

import pytest

from libera.host import menu
from libera.host.session import Session


@pytest.fixture
def front(tmp_path) -> Session:
    """The front window's session, with nothing unsaved."""
    found = Session(payload=tmp_path / "payload", work=tmp_path / "work")
    found.work.mkdir(parents=True)
    return found


def test_an_action_nobody_conditions_is_always_available():
    assert menu.is_enabled("openDocument:", None) is True
    assert menu.is_enabled("", None) is True


def test_save_is_greyed_out_when_there_is_nothing_to_save(front):
    assert menu.is_enabled("saveDocument:", front) is False


def test_save_lights_up_when_the_document_has_unsaved_edits(front):
    front.unsaved_marker.write_text("{}", encoding="utf-8")

    assert menu.is_enabled("saveDocument:", front) is True


def test_save_with_no_window_in_front():
    """A menu can be validated while no window is front."""
    assert menu.is_enabled("saveDocument:", None) is False


@pytest.mark.parametrize("action", ["undo:", "redo:"])
def test_undo_follows_what_the_editor_last_said(front, action):
    front.abilities[action.rstrip(":")] = False

    assert menu.is_enabled(action, front) is False

    front.abilities[action.rstrip(":")] = True

    assert menu.is_enabled(action, front) is True


@pytest.mark.parametrize("action", ["undo:", "redo:"])
def test_an_editor_that_has_not_said_yet_leaves_it_available(front, action):
    """Greying out something that would have worked is the worse mistake."""
    assert menu.is_enabled(action, front) is True
