"""The change log is fiddly and loses edits silently when wrong.

Edits reach the host on a separate channel from the document, and the format is
a bare comma-separated list with a trailing comma. Appending, empty flushes and
undo indices are all load-bearing; each of these tests pins one of them.
"""

from __future__ import annotations

import pytest

from libera.host.changelog import ChangeLog


@pytest.fixture
def log(tmp_path) -> ChangeLog:
    """Where a session keeps one: its doc/ exists, and changes/ not yet."""
    (tmp_path / "doc").mkdir()
    return ChangeLog(tmp_path / "doc" / "changes" / "changes0.json")


def text(log: ChangeLog) -> str:
    return log.path.read_text() if log.path.is_file() else "<missing>"


def test_appends_rather_than_replacing(log):
    log.record("a", None, 1)
    log.record("b", None, 1)
    assert text(log) == '"a","b",'


def test_empty_flush_keeps_the_log(log):
    """The editor sends count 0 after saving; that must not erase anything."""
    log.record("a", None, 1)
    log.record("", None, 0)
    assert text(log) == '"a",'


def test_empty_flush_creates_nothing(log):
    log.record("", None, 0)
    assert text(log) == "<missing>"


def test_undo_truncates_back_to_index(log):
    log.record("a", None, 1)
    log.record("b", None, 1)
    log.record("c", 1, 1)  # index rewinds: b is undone
    assert text(log) == '"a","c",'


def test_ordinary_flush_has_no_index_and_truncates_nothing(log):
    """sdkjs passes a null index while simply typing.

    Coercing it to 0 (which is what CEF's GetIntValue does) would read as
    "truncate everything" and drop the log on every batch.
    """
    log.record("a", None, 1)
    log.record("b", None, 1)
    log.record("c", None, 1)
    assert text(log) == '"a","b","c",'


def test_undo_past_everything_empties_the_log(log):
    log.record("a", None, 1)
    log.record("b", None, 1)
    log.record("", 0, 0)
    assert not text(log)


def test_undo_to_where_the_log_already_ends_cuts_nothing(log):
    log.record("a", None, 1)
    log.record("b", 2, 1)
    assert text(log) == '"a","b",'


def test_a_write_that_fails_leaves_the_earlier_edits_alone(log):
    """The log is what a crash leaves behind, so adding to it must not put
    what is already there at risk.

    It used to be rewritten whole on every keystroke: emptied, then filled.
    A write that dies partway -- a full disk, a crash -- stands in here as
    text that cannot be encoded, and it found the file already emptied.
    """
    log.record("a", None, 1)

    with pytest.raises(UnicodeEncodeError):
        log.record("\ud800", None, 1)

    assert text(log) == '"a",'
