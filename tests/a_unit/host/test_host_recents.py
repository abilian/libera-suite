"""The Recent list outlives the session and never trusts the page.

Two things are load-bearing: it must survive an open (which rebuilds the
session directory from scratch), and the id the editor sends back is a path, so
the host has to check it against its own list rather than opening what it is
told to.
"""

from __future__ import annotations

import json

import pytest

from libera.host import convert, opening, recents, session
from libera.host.session import Session


@pytest.fixture
def here(tmp_path) -> Session:
    """A configured session, its state in tmp_path."""
    found = Session(payload=tmp_path / "payload", work=tmp_path / "state" / "session")
    session.configure(found)
    return found


def make(tmp_path, name):
    f = tmp_path / name
    f.write_bytes(b"x")
    return f


def test_most_recent_first_and_no_duplicates(here, tmp_path):
    a, b = make(tmp_path, "a.docx"), make(tmp_path, "b.docx")
    recents.remember_recent(here, a)
    recents.remember_recent(here, b)
    recents.remember_recent(here, a)

    assert [e["path"] for e in recents.read_recents(here)] == [str(a), str(b)]


def test_records_a_format_the_editor_will_show(here, tmp_path):
    """Words drops anything outside FILE_DOCUMENT..FILE_PRESENTATION."""
    recents.remember_recent(here, make(tmp_path, "a.docx"))
    assert 64 < recents.read_recents(here)[0]["type"] <= 128


def test_a_diagram_is_remembered_under_a_diagram_id(here, tmp_path):
    """Diagrams has no format x2t writes, and remembering one raised KeyError
    -- after the conversion had worked, so no .vsdx could be opened at all.

    The Diagrams list accepts the six FILE_DRAW ids, 16385 to 16390, and
    drops anything else without a word.
    """
    recents.remember_recent(here, make(tmp_path, "plan.vsdx"))
    assert 16385 <= recents.read_recents(here)[0]["type"] <= 16390


def test_a_deleted_document_drops_out(here, tmp_path):
    f = make(tmp_path, "gone.docx")
    recents.remember_recent(here, f)
    f.unlink()
    assert recents.read_recents(here) == []


@pytest.mark.parametrize(
    "content",
    [
        pytest.param('["/tmp/a.docx"]', id="a list of paths, as an older file was"),
        pytest.param('[{"path": "/tmp/a.docx"}]', id="an entry with no type"),
        pytest.param('{"recent": []}', id="an object where a list belongs"),
        pytest.param("[null]", id="a null entry"),
    ],
)
def test_a_file_this_version_did_not_write_reads_as_an_empty_list(here, content):
    """It parses as JSON and then fails on `e["path"]`, which is the trap.

    That killed the whole /__host__/recents request -- no response, connection
    closed -- so the start window reported a network failure and the Recent
    list looked broken from the outside.
    """
    here.recents.parent.mkdir(parents=True, exist_ok=True)
    here.recents.write_text(content, encoding="utf-8")

    assert recents.read_recents(here) == []
    body, _ctype = recents.read_recents_for_editor(here)
    assert json.loads(body) == []


def test_the_list_is_capped(here, tmp_path):
    for i in range(recents.RECENT_LIMIT + 5):
        recents.remember_recent(here, make(tmp_path, f"doc{i}.docx"))
    assert len(recents.read_recents(here)) == recents.RECENT_LIMIT


def test_our_own_state_directory_is_not_offered_back(here):
    """The blank document lives beside the recents file; it is plumbing."""
    blank = here.recents.parent / "Untitled.docx"
    blank.parent.mkdir(parents=True, exist_ok=True)
    blank.write_bytes(b"x")
    recents.remember_recent(here, blank)
    assert recents.read_recents(here) == []


def test_served_records_carry_the_path_as_id(here, tmp_path):
    a = make(tmp_path, "a.docx")
    recents.remember_recent(here, a)
    body, _ = recents.read_recents_for_editor(here)
    assert json.loads(body)[0]["id"] == str(a)


def unsaved_session(here: Session, document) -> None:
    """A session directory that looks like a crash with unsaved edits."""
    here.doc.mkdir(parents=True, exist_ok=True)
    here.editor_bin.write_bytes(b"bin")
    here.change_log.record("x", None, 1)
    here.write_current_document(document)
    here.mark_modified(True)


def test_recovery_is_offered_only_for_the_same_document(here, tmp_path):
    """The marker names a document; opening a different one is not a recovery."""
    a, b = make(tmp_path, "a.docx"), make(tmp_path, "b.docx")
    unsaved_session(here, a)

    assert opening.find_recoverable(here, a) == here.work
    assert opening.find_recoverable(here, b) is None


def test_recovery_finds_another_window_s_session(here, tmp_path):
    """With a window per document, the session that crashed is rarely the one
    being opened now."""
    a = make(tmp_path, "a.docx")
    other = here.work.parent / "beef"
    (other / "doc" / "changes").mkdir(parents=True)
    (other / "doc" / "Editor.bin").write_bytes(b"bin")
    (other / "doc" / "changes" / "changes0.json").write_text('"x",')
    (other / "unsaved.json").write_text(json.dumps({"document": str(a)}))

    assert opening.find_recoverable(here, a) == other


def test_a_window_still_open_is_not_a_crash(here, tmp_path):
    """Its edits are live. Recovering them deleted its directory while the
    window was still writing there: opening a document twice did that."""
    a = make(tmp_path, "a.docx")
    live = Session(payload=here.payload, work=here.work.parent / "live")
    session.configure(live)
    unsaved_session(live, a)

    assert opening.find_recoverable(here, a) is None


def test_open_saved_version_declines_the_edits_for_good(here, tmp_path, monkeypatch):
    """Not only for this open: they were offered again every time after."""
    a = make(tmp_path, "a.docx")
    crashed = Session(payload=here.payload, work=here.work.parent / "crashed")
    unsaved_session(crashed, a)
    monkeypatch.setattr(convert, "convert_to_editor_bin", lambda *_: True)

    opening.open_document(here, a)  # the headless shell answers "no"

    assert opening.find_recoverable(here, a) is None


def test_sweep_keeps_what_holds_unsaved_edits(here, tmp_path):
    root = here.work.parent
    # A session that has been used: configure() makes doc/ and out/.
    litter = root / "litter"
    (litter / "doc").mkdir(parents=True)
    keeper = root / "keeper"
    (keeper / "doc").mkdir(parents=True)
    (keeper / "unsaved.json").write_text("{}")

    session.sweep_sessions(root, keep={"0"})

    assert not litter.exists()
    assert keeper.exists()


def test_sweep_leaves_alone_what_is_not_a_session(here):
    """The untitled documents live in here too, and are not litter.

    Deleting them would take somebody's unsaved new document with them, which
    is what happened when File > New started writing them here.
    """
    scratch = here.scratch
    scratch.mkdir(parents=True)
    (scratch / "Untitled.docx").write_bytes(b"someone's new document")

    session.sweep_sessions(here.work.parent, keep={"0"})

    assert (scratch / "Untitled.docx").is_file()


def test_saving_clears_the_offer(here, tmp_path):
    a = make(tmp_path, "a.docx")
    unsaved_session(here, a)

    assert opening.find_recoverable(here, a)
    here.mark_modified(False)  # the editor reports itself clean after a save
    assert opening.find_recoverable(here, a) is None
