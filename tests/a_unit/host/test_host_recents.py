"""The Recent list outlives the session and never trusts the page.

Two things are load-bearing: it must survive an open (which rebuilds the
session directory from scratch), and the id the editor sends back is a path, so
the host has to check it against its own list rather than opening what it is
told to.
"""

from __future__ import annotations

import json

import pytest

from libera.host import recents, server as host, session
from libera.host.session import Host


@pytest.fixture
def server(tmp_path):
    session.configure(
        Host(payload=tmp_path / "payload", work=tmp_path / "state" / "session")
    )
    session.H.work.mkdir(parents=True, exist_ok=True)  # configure() may have
    return host


def make(tmp_path, name):
    f = tmp_path / name
    f.write_bytes(b"x")
    return f


def test_most_recent_first_and_no_duplicates(server, tmp_path):
    a, b = make(tmp_path, "a.docx"), make(tmp_path, "b.docx")
    recents.remember_recent(a)
    recents.remember_recent(b)
    recents.remember_recent(a)

    assert [e["path"] for e in recents.read_recents()] == [str(a), str(b)]


def test_records_a_format_the_editor_will_show(server, tmp_path):
    """Words drops anything outside FILE_DOCUMENT..FILE_PRESENTATION."""
    recents.remember_recent(make(tmp_path, "a.docx"))
    assert 64 < recents.read_recents()[0]["type"] <= 128


def test_a_deleted_document_drops_out(server, tmp_path):
    f = make(tmp_path, "gone.docx")
    recents.remember_recent(f)
    f.unlink()
    assert recents.read_recents() == []


@pytest.mark.parametrize(
    "content",
    [
        pytest.param('["/tmp/a.docx"]', id="a list of paths, as an older file was"),
        pytest.param('[{"path": "/tmp/a.docx"}]', id="an entry with no type"),
        pytest.param('{"recent": []}', id="an object where a list belongs"),
        pytest.param("[null]", id="a null entry"),
    ],
)
def test_a_file_this_version_did_not_write_reads_as_an_empty_list(server, content):
    """It parses as JSON and then fails on `e["path"]`, which is the trap.

    That killed the whole /__host__/recents request -- no response, connection
    closed -- so the start window reported a network failure and the Recent
    list looked broken from the outside.
    """
    session.H.recents.parent.mkdir(parents=True, exist_ok=True)
    session.H.recents.write_text(content, encoding="utf-8")

    assert recents.read_recents() == []
    body, _ctype = recents.get_recents()
    assert json.loads(body) == []


def test_the_list_is_capped(server, tmp_path):
    for i in range(recents.RECENT_LIMIT + 5):
        recents.remember_recent(make(tmp_path, f"doc{i}.docx"))
    assert len(recents.read_recents()) == recents.RECENT_LIMIT


def test_our_own_state_directory_is_not_offered_back(server):
    """The blank document lives beside the recents file; it is plumbing."""
    blank = session.H.recents.parent / "Untitled.docx"
    blank.parent.mkdir(parents=True, exist_ok=True)
    blank.write_bytes(b"x")
    recents.remember_recent(blank)
    assert recents.read_recents() == []


def test_served_records_carry_the_path_as_id(server, tmp_path):
    a = make(tmp_path, "a.docx")
    recents.remember_recent(a)
    body, _ = recents.get_recents()
    assert json.loads(body)[0]["id"] == str(a)


def unsaved_session(document):
    """A session directory that looks like a crash with unsaved edits.

    Reads `session.H` rather than a module's re-export of it: `server` is a
    package now and does not carry one, and the session is the same object
    whichever module you reach it through.
    """
    session.H.doc.mkdir(parents=True, exist_ok=True)
    session.H.editor_bin.write_bytes(b"bin")
    (session.H.doc / "changes").mkdir(exist_ok=True)
    (session.H.doc / "changes" / "changes0.json").write_text('"x",')
    session.H.current.write_text(str(document))
    session.set_modified(True)


def test_recovery_is_offered_only_for_the_same_document(server, tmp_path):
    """The marker names a document; opening a different one is not a recovery."""
    a, b = make(tmp_path, "a.docx"), make(tmp_path, "b.docx")
    unsaved_session(a)

    assert session.recoverable(a) == session.H.work
    assert session.recoverable(b) is None


def test_recovery_finds_another_window_s_session(server, tmp_path):
    """With a window per document, the session that crashed is rarely the one
    being opened now."""
    a = make(tmp_path, "a.docx")
    other = session.H.work.parent / "beef"
    (other / "doc" / "changes").mkdir(parents=True)
    (other / "doc" / "Editor.bin").write_bytes(b"bin")
    (other / "doc" / "changes" / "changes0.json").write_text('"x",')
    (other / "unsaved.json").write_text(json.dumps({"document": str(a)}))

    assert session.recoverable(a) == other


def test_sweep_keeps_what_holds_unsaved_edits(server, tmp_path):
    root = session.H.work.parent
    # A session that has been used: configure() makes doc/ and out/.
    litter = root / "litter"
    (litter / "doc").mkdir(parents=True)
    keeper = root / "keeper"
    (keeper / "doc").mkdir(parents=True)
    (keeper / "unsaved.json").write_text("{}")

    session.sweep_sessions(root, keep={"0"})

    assert not litter.exists()
    assert keeper.exists()


def test_sweep_leaves_alone_what_is_not_a_session(server):
    """The untitled documents live in here too, and are not litter.

    Deleting them would take somebody's unsaved new document with them, which
    is what happened when File > New started writing them here.
    """
    scratch = session.H.scratch
    scratch.mkdir(parents=True)
    (scratch / "Untitled.docx").write_bytes(b"someone's new document")

    session.sweep_sessions(session.H.work.parent, keep={"0"})

    assert (scratch / "Untitled.docx").is_file()


def test_saving_clears_the_offer(server, tmp_path):
    a = make(tmp_path, "a.docx")
    unsaved_session(a)

    assert session.recoverable(a)
    session.set_modified(False)  # the editor reports itself clean after a save
    assert session.recoverable(a) is None
