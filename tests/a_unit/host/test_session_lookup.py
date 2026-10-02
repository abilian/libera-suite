"""A request names its session, and the registry answers for it.

Every request from a window carries its session's id in the query string; the
handler looks it up and hands the session to whatever answers. It used to be
bound to the thread serving the request instead, as `H`, and the thread bugs
in notes/lessons-learned.md all came from that.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from libera.host import apps
from libera.host.session import (
    SESSIONS,
    NotReadyError,
    Session,
    configure,
    create_session,
    drop_session,
    lookup,
)


@pytest.fixture
def two_sessions(tmp_path):
    SESSIONS.clear()
    configure(Session(payload=tmp_path, work=tmp_path / "0", document=Path("a.docx")))
    configure(Session(payload=tmp_path, work=tmp_path / "1", document=Path("b.xlsx")))
    yield
    SESSIONS.clear()


def test_an_id_reaches_that_session(two_sessions):
    assert lookup("1").editor is apps.TABLES


def test_no_id_means_the_first_session(two_sessions):
    """What a static request carries: nothing, and the payload is shared."""
    assert lookup("").editor is apps.WORDS


def test_an_id_that_matches_no_session_is_refused(two_sessions):
    """Not the first session instead: a request from a window that has closed
    would edit another window's document."""
    with pytest.raises(NotReadyError, match="no session 'gone'"):
        lookup("gone")


def test_a_closed_window_s_id_is_refused(two_sessions):
    drop_session("1")
    with pytest.raises(NotReadyError, match="no session '1'"):
        lookup("1")


def test_with_no_sessions_at_all_it_says_so():
    SESSIONS.clear()
    with pytest.raises(NotReadyError, match="no sessions"):
        lookup("")


def test_a_session_knows_the_id_its_requests_carry(two_sessions):
    """Its window's address is built from it; see server.make_editor_url."""
    assert lookup("1").id == "1"
    assert create_session(Path("c.pptx")).id in SESSIONS


def test_file_new_picks_the_blank_of_the_window_that_asked(two_sessions):
    """The bug: New in a Tables window made an Untitled.docx."""
    assert lookup("0").blank.name == apps.WORDS.blank
    assert lookup("1").blank.name == apps.TABLES.blank
