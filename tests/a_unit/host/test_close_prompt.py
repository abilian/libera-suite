"""Closing a window must not take unsaved edits with it.

The prompt itself needs a screen, so what is pinned here is the decision to
ask: an unmodified document closes without a word, and a session nobody knows
about cannot block a close.
"""

from __future__ import annotations

import pytest

from libera.host import convert, saving, session as sessions, window
from libera.host.session import Session
from libera.host.window import Answer


@pytest.fixture
def bound_session(tmp_path):
    host = Session(payload=tmp_path / "payload", work=tmp_path / "state" / "s")
    sessions.configure(host)
    (host.work / "doc").mkdir(parents=True, exist_ok=True)
    document = tmp_path / "note.docx"
    document.write_bytes(b"x")
    host.current_file.write_text(str(document))
    return host


def test_a_clean_document_closes_without_asking(bound_session):
    assert not bound_session.unsaved_marker.is_file()
    assert window.confirm_close("s") is True


def test_an_unknown_session_cannot_block_a_close(bound_session):
    assert window.confirm_close("nobody") is True


def test_a_document_with_unsaved_edits_is_asked_about(bound_session, monkeypatch):
    """The decision this file is about, from the side that asks: Cancel keeps
    the window, which is the answer that cannot lose anything."""
    asked = []
    monkeypatch.setattr(
        window.dialogs, "ask", lambda question: asked.append(question) or Answer.CANCEL
    )
    bound_session.mark_modified(True)

    assert window.confirm_close("s") is False
    assert [q.yes for q in asked] == ["Save"]


def test_a_saved_document_stops_being_dirty(bound_session, monkeypatch):
    """save_document clears the marker, which is what lets the second close
    attempt through after the user chose Save."""
    bound_session.mark_modified(True)
    assert bound_session.unsaved_marker.is_file()

    monkeypatch.setattr(convert, "export", lambda *_: True)
    monkeypatch.setattr(saving.shutil, "copyfile", lambda *_: None)
    result = saving.save_document(bound_session, {"fileType": 0, "params": ""})

    assert result["error"] == 0
    assert not bound_session.unsaved_marker.is_file()
