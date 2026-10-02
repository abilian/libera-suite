"""What the editor can do is pushed to the host, not asked for.

A menu is validated on the GUI thread, and asking the editor from there would
deadlock against the thread that would have to answer.
"""

from __future__ import annotations

import json

import pytest

from libera.host import server, session as sessions
from libera.host.session import Session


@pytest.fixture
def bound_session(tmp_path) -> Session:
    found = Session(payload=tmp_path / "payload", work=tmp_path / "s")
    sessions.configure(found)
    return found


class FakeHandler:
    """A request from that session's window: what record_abilities reads of one."""

    def __init__(self, body: bytes, session: Session):
        self._body = body
        self.session = session
        self.status = None

    def read_body(self) -> bytes:
        return self._body

    def send_no_content(self):
        self.status = 204


def test_the_editor_reports_what_it_can_do(bound_session):
    server.record_abilities(
        FakeHandler(json.dumps({"undo": True}).encode(), bound_session)
    )
    assert sessions.SESSIONS["s"].abilities == {"undo": True}


def test_later_reports_merge_rather_than_replace(bound_session):
    server.record_abilities(FakeHandler(b'{"undo": true}', bound_session))
    server.record_abilities(FakeHandler(b'{"redo": true}', bound_session))

    assert sessions.SESSIONS["s"].abilities == {"undo": True, "redo": True}


def test_closing_a_window_forgets_everything_about_it(bound_session):
    """The editor's state, its window, the reload offer: all on the session.

    They were three dictionaries in three modules, and closing a window
    cleared one of them.
    """
    server.record_abilities(FakeHandler(b'{"undo": true}', bound_session))
    sessions.drop_session("s")

    assert "s" not in sessions.SESSIONS
