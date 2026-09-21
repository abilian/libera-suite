"""Whether a menu item is available, decided without AppKit.

This lived inside validateMenuItem_ on a pyobjc class, where it did this:

    session = front_session()          # a str
    host = session.SESSIONS.get(session)

-- a local shadowing the imported `session` module, so every Undo, Redo and
Save validation raised AttributeError. Inside an ObjC callback, where nobody
reads the exception, the only symptom was menu items behaving oddly.

`ty` found it. These tests keep it found: they need no menu, no window and no
macOS, so they run everywhere.
"""

from __future__ import annotations

import pytest

from libera.host import menu, session
from libera.host.session import Host


@pytest.fixture
def a_session(tmp_path):
    """One registered session, with nothing unsaved."""
    host = Host(payload=tmp_path / "payload", work=tmp_path / "work")
    host.work.mkdir(parents=True)
    session.SESSIONS["s1"] = host
    yield "s1", host
    session.SESSIONS.pop("s1", None)
    session.EDITOR_STATE.pop("s1", None)


def test_an_action_nobody_conditions_is_always_available():
    assert menu.enabled_for("openDocument:", "") is True
    assert menu.enabled_for("", "") is True


def test_save_is_greyed_out_when_there_is_nothing_to_save(a_session):
    session_id, _host = a_session

    assert menu.enabled_for("saveDocument:", session_id) is False


def test_save_lights_up_when_the_document_has_unsaved_edits(a_session):
    session_id, host = a_session
    host.unsaved.write_text("{}", encoding="utf-8")

    assert menu.enabled_for("saveDocument:", session_id) is True


def test_save_on_a_session_that_is_not_there(a_session):
    """A menu can be validated while no window is front."""
    assert menu.enabled_for("saveDocument:", "gone") is False


@pytest.mark.parametrize("action", ["undo:", "redo:"])
def test_undo_follows_what_the_editor_last_said(a_session, action):
    session_id, _ = a_session
    session.EDITOR_STATE[session_id] = {action.rstrip(":"): False}

    assert menu.enabled_for(action, session_id) is False

    session.EDITOR_STATE[session_id] = {action.rstrip(":"): True}

    assert menu.enabled_for(action, session_id) is True


@pytest.mark.parametrize("action", ["undo:", "redo:"])
def test_an_editor_that_has_not_said_yet_leaves_it_available(a_session, action):
    """Greying out something that would have worked is the worse mistake."""
    session_id, _ = a_session

    assert menu.enabled_for(action, session_id) is True
