"""The change log is fiddly and loses edits silently when wrong.

Edits reach the host on a separate channel from the document, and the format is
a bare comma-separated list with a trailing comma. Appending, empty flushes and
undo indices are all load-bearing; each of these tests pins one of them.
"""

from __future__ import annotations

import pytest

from libera.host import convert, server as host, session
from libera.host.session import Host


@pytest.fixture
def server(tmp_path):
    """A configured host whose session state lives in tmp_path."""
    session.configure(Host(payload=tmp_path / "payload", work=tmp_path / "work"))
    session.H.doc.mkdir(parents=True)
    return host


def log_text(_mod) -> str:
    """The change log as it stands.

    Reads `session.H` rather than the module's own re-export: `server` is a
    package now and does not carry one, and the session is the same object
    whichever module you reach it through.
    """
    f = session.H.doc / "changes" / "changes0.json"
    return f.read_text() if f.is_file() else "<missing>"


def test_appends_rather_than_replacing(server):
    convert.save_changes("a", None, 1)
    convert.save_changes("b", None, 1)
    assert log_text(server) == '"a","b",'


def test_empty_flush_keeps_the_log(server):
    """The editor sends count 0 after saving; that must not erase anything."""
    convert.save_changes("a", None, 1)
    convert.save_changes("", None, 0)
    assert log_text(server) == '"a",'


def test_empty_flush_creates_nothing(server):
    convert.save_changes("", None, 0)
    assert log_text(server) == "<missing>"


def test_undo_truncates_back_to_index(server):
    convert.save_changes("a", None, 1)
    convert.save_changes("b", None, 1)
    convert.save_changes("c", 1, 1)  # index rewinds: b is undone
    assert log_text(server) == '"a","c",'


def test_ordinary_flush_has_no_index_and_truncates_nothing(server):
    """sdkjs passes a null index while simply typing.

    Coercing it to 0 (which is what CEF's GetIntValue does) would read as
    "truncate everything" and drop the log on every batch.
    """
    convert.save_changes("a", None, 1)
    convert.save_changes("b", None, 1)
    convert.save_changes("c", None, 1)
    assert log_text(server) == '"a","b","c",'
