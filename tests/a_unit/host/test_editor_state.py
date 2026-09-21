"""What the editor can do is pushed to the host, not asked for.

A menu is validated on the GUI thread, and asking the editor from there would
deadlock against the thread that would have to answer.
"""

from __future__ import annotations

import json

import pytest

from libera.host import server, session as sessions
from libera.host.session import Host


@pytest.fixture
def bound_session(tmp_path):
    sessions.EDITOR_STATE.clear()
    sessions.configure(Host(payload=tmp_path / "payload", work=tmp_path / "s"), "s")
    return sessions


class FakeHandler:
    def __init__(self, body: bytes):
        self._body = body
        self.status = None

    def body(self) -> bytes:
        return self._body

    def no_content(self):
        self.status = 204


def test_an_unknown_session_can_do_nothing_in_particular(bound_session):
    assert sessions.editor_state("nobody") == {}


def test_the_editor_reports_what_it_can_do(bound_session):
    server.post_can(FakeHandler(json.dumps({"undo": True}).encode()))
    assert sessions.editor_state("s") == {"undo": True}


def test_later_reports_merge_rather_than_replace(bound_session):
    server.post_can(FakeHandler(b'{"undo": true}'))
    server.post_can(FakeHandler(b'{"redo": true}'))

    assert sessions.editor_state("s") == {"undo": True, "redo": True}


def test_closing_a_window_forgets_its_state(bound_session):
    server.post_can(FakeHandler(b'{"undo": true}'))
    sessions.drop_session("s")

    assert sessions.editor_state("s") == {}
