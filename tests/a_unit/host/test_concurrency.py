"""What happens when several windows do things at once.

Every request has a thread of its own, and nothing here used to coordinate
them. Each test below was a probe first, and each failed every time it ran:
twelve documents opened together left one to four of them in the Recent list;
a reader of the list could see it empty, half-written, and then save that over
everyone else's entries; walking the session registry while windows opened and
closed raised "dictionary keys changed during iteration".
"""

from __future__ import annotations

import pathlib
import threading
import time
from types import SimpleNamespace

import pytest

from libera.host import convert, recents, session as sessions
from libera.host.session import Session, configure

TOGETHER = 12


def run_together(work, args) -> None:
    """Start `work` on every argument at the same instant, and wait for all."""
    start = threading.Barrier(len(args))
    failures: list[BaseException] = []

    def one(arg):
        start.wait()
        try:
            work(arg)
        except BaseException as e:  # reported below, not hidden
            failures.append(e)

    threads = [threading.Thread(target=one, args=(a,)) for a in args]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not failures, failures


@pytest.fixture
def session(tmp_path):
    made = Session(payload=tmp_path / "payload", work=tmp_path / "state" / "0")
    configure(made)
    return made


def test_documents_opened_together_are_all_remembered(session, tmp_path):
    documents = []
    for i in range(TOGETHER):
        d = tmp_path / "docs" / f"doc{i}.docx"
        d.parent.mkdir(exist_ok=True)
        d.write_bytes(b"a document")
        documents.append(d)

    run_together(lambda d: recents.remember_recent(session, d), documents)

    assert len(recents.read_recents(session)) == TOGETHER


def test_a_state_file_is_never_seen_half_written(session, tmp_path):
    """A reader sees the old contents or the new, never an empty file.

    And neither side fails: on Windows, replacing a file a reader has open, or
    opening one being replaced, is a PermissionError."""
    long_path = tmp_path / ("x" * 200) / "doc.docx"
    seen: list[pathlib.Path | None] = []
    stop = time.monotonic() + 0.5

    def write(_):
        while time.monotonic() < stop:
            session.write_current_document(long_path)

    def read(_):
        while time.monotonic() < stop:
            seen.append(session.read_current_document())

    session.write_current_document(long_path)
    run_together(lambda f: f(None), [write, read, read])

    assert seen
    assert set(seen) == {long_path}


def test_the_registry_can_be_walked_while_windows_open_and_close(session, tmp_path):
    stop = time.monotonic() + 1.0

    def churn(_):
        i = 0
        while time.monotonic() < stop:
            other = Session(payload=tmp_path, work=tmp_path / f"w{i % 50}")
            sessions.SESSIONS[other.id] = other
            sessions.SESSIONS.pop(f"w{(i + 25) % 50}", None)
            i += 1

    def walk(_):
        while time.monotonic() < stop:
            sessions.find_session_showing(tmp_path / "absent.docx")
            sessions.lookup("")

    run_together(lambda f: f(None), [churn, walk, walk, walk])


def test_only_so_many_converters_run_at_once(session, monkeypatch):
    """Each x2t holds tens to hundreds of MB: 71 MB for a 3 MB docx, 117 MB
    for a 2.9 MB xlsx (measured 2026-10-04). A dozen documents opened at once
    ran a dozen."""
    running = 0
    most = 0
    guard = threading.Lock()
    # The first converters hold their slots until every slot is taken, so a
    # thread scheduled late under load cannot make the count come out short.
    full = threading.Event()

    def slow_run(*_a, **_k):
        nonlocal running, most
        with guard:
            running += 1
            most = max(most, running)
            if running == convert.X2T_AT_ONCE:
                full.set()
        full.wait(5)
        time.sleep(0.05)
        with guard:
            running -= 1

    monkeypatch.setattr(convert.subprocess, "run", slow_run)

    # More than may run, whatever this machine's core count: a fixed dozen let
    # every one through on 24 cores, where X2T_AT_ONCE is 12.
    asking = convert.X2T_AT_ONCE + 4
    run_together(lambda _: convert.run_x2t(session, "job.xml"), range(asking))

    # Equal, not at most: zero would also be at most, and is what a run_x2t
    # that stopped calling subprocess.run would give.
    assert most == convert.X2T_AT_ONCE


def test_an_edit_during_a_save_neither_waits_nor_is_half_read(session, monkeypatch):
    """The editor posts every edit and waits for the answer, so an edit that
    waited for a save froze the editor for the whole conversion: 0.8 s on a
    3 MB document, 3.6 s while other windows held the converter (measured
    2026-10-04). And x2t, reading the log the editor was still appending to,
    could read the last edit half-written. A save converts a snapshot taken at
    the moment it starts: the edit lands at once, in the live log, and the
    save reads the log as it stood."""
    from libera.host.server import document
    from libera.host.server.api import Request

    session.doc.mkdir()  # what opening the document made
    (session.doc / "Editor.bin").write_bytes(b"DOCY;v10;0;")
    session.change_log.record("before", None, 1)
    reading = threading.Event()
    release = threading.Event()
    seen: list[str] = []

    saved = session.out_dir / "saved.docx"

    def x2t_reading_the_log(_session, job):
        reading.set()
        release.wait(5)
        log = pathlib.Path(job).parent / "doc" / "changes" / "changes0.json"
        seen.append(log.read_text(encoding="utf-8"))
        saved.write_bytes(b"the saved document")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(convert, "run_x2t", x2t_reading_the_log)
    saving = threading.Thread(
        target=convert.export,
        args=(session, saved, 65, None),
    )
    saving.start()
    assert reading.wait(5)

    edit = Request(session, b"during", {"index": [""], "count": ["1"]})
    editing = threading.Thread(target=document.record_changes, args=(edit,))
    editing.start()
    editing.join(1)
    assert not editing.is_alive(), "the edit waited for the save"

    release.set()
    saving.join(5)
    assert seen == ['"before",'], "x2t did not read the log as it stood"
    assert session.change_log.path.read_text(encoding="utf-8") == '"before","during",'
    assert list(session.work.glob("export-*")) == [], "the snapshot was left behind"
