"""File > New: which document, of which kind, named what.

This decision has been wrong twice -- once making an Untitled.docx in a Tables
window, once raising because the macOS menu runs every action on a thread of
its own and `H` is thread-local. Both are here now, without a window.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from support import ScriptedShell

from libera.host import apps, window
from libera.host.session import SESSIONS, Session


@pytest.fixture
def payload(tmp_path):
    """A payload with a blank for each editor, and nothing else."""
    empty = tmp_path / "payload" / "empty"
    empty.mkdir(parents=True)
    for app in apps.ALL:
        if app.blank:
            (empty / app.blank).write_bytes(b"PK\x03\x04 not really a document")
    return tmp_path / "payload"


@pytest.fixture
def windows(payload, tmp_path, monkeypatch):
    """Two windows: session 0 is Words, session 1 is Tables."""
    SESSIONS.clear()
    for name, document in (("0", "letter.docx"), ("1", "budget.xlsx")):
        SESSIONS[name] = Session(
            payload=payload, work=tmp_path / "s" / name, document=Path(document)
        )
    yield
    SESSIONS.clear()


def in_front(session_id: str, monkeypatch):
    """Pretend that session's window is the front one.

    Patched on `window.windows`, where make_new_document looks it up, and not on
    the `window` package, which only re-exports it: replacing the re-export
    leaves the definition its caller actually reads untouched.
    """
    monkeypatch.setattr(
        window.windows, "find_front_session", lambda: SESSIONS.get(session_id)
    )


def test_new_makes_the_kind_of_document_the_front_window_holds(windows, monkeypatch):
    in_front("1", monkeypatch)
    assert window.make_new_document().suffix == ".xlsx"

    in_front("0", monkeypatch)
    assert window.make_new_document().suffix == ".docx"


def test_new_works_on_a_thread_that_never_bound_a_session(windows, monkeypatch):
    """The macOS menu runs every action on a fresh thread. This raised."""
    in_front("1", monkeypatch)
    out: list = []

    def run():
        try:
            out.append(("ok", window.make_new_document()))
        except BaseException as e:
            out.append(("raised", e))

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=5)
    kind, value = out[0]
    if kind == "raised":
        raise value
    assert value.suffix == ".xlsx"


def test_no_front_window_still_makes_something(windows, monkeypatch):
    """find_front_session returns None when no window matches; New must still work."""
    in_front("", monkeypatch)
    assert window.make_new_document().suffix == ".docx"


def test_the_template_itself_is_never_edited(windows, monkeypatch):
    in_front("0", monkeypatch)
    made = window.make_new_document()
    assert made.parent != (SESSIONS["0"].payload / "empty")
    assert (
        made.read_bytes() == (SESSIONS["0"].payload / "empty" / "new.docx").read_bytes()
    )


def test_a_second_new_does_not_overwrite_the_first(windows, monkeypatch):
    in_front("0", monkeypatch)
    names = [window.make_new_document().name for _ in range(3)]
    assert names == ["Untitled.docx", "Untitled 2.docx", "Untitled 3.docx"]
    assert len(set(names)) == 3


def test_the_numbering_follows_the_editor_not_the_suffix(windows, monkeypatch):
    """Words and Tables number independently, because the names differ."""
    in_front("0", monkeypatch)
    window.make_new_document()
    in_front("1", monkeypatch)
    assert window.make_new_document().name == "Untitled.xlsx"


def test_a_viewer_cannot_make_a_new_document(windows, monkeypatch, tmp_path):
    """Diagrams has no blank. NotReadyError, not a stray .vsdx."""
    from libera.host.session import NotReadyError

    SESSIONS["2"] = Session(
        payload=SESSIONS["0"].payload,
        work=tmp_path / "s" / "2",
        document=Path("plan.vsdx"),
    )
    in_front("2", monkeypatch)
    with pytest.raises(NotReadyError, match="cannot create"):
        window.make_new_document()


def test_an_untitled_document_never_reaches_the_recent_list(windows, monkeypatch):
    """It is our plumbing, and the start window puts Recent in front of you.

    remember_recent refuses anything under the recents file's own directory,
    so untitled documents have to be written there -- which they were not.
    """
    from libera.host.session import is_inside

    in_front("0", monkeypatch)
    made = window.make_new_document()
    plumbing = SESSIONS["0"].recents.parent
    assert is_inside(plumbing, made), f"{made} would be offered back as recent"


@pytest.fixture
def new_document_open(windows, monkeypatch) -> Session:
    """What File > New leaves behind: an Untitled.docx, open in a window.

    Converting is stubbed to fail the test, because converting is the one
    thing a first save must not get to before it has asked where.
    """
    from libera.host import convert
    from libera.host.session import configure

    in_front("0", monkeypatch)
    made = window.make_new_document()
    work = made.parent.parent / "new"
    opened = Session(payload=SESSIONS["0"].payload, work=work, document=made)
    configure(opened)
    monkeypatch.setattr(
        convert, "export", lambda *_: pytest.fail(f"saved over {made.name} in place")
    )
    return opened


def test_saving_a_new_document_asks_where(new_document_open, monkeypatch):
    """Not a plain Save into the state directory it was made in.

    It is a real file, so plain Save overwrote it: the editor said "saved",
    and the document sat where nobody would look, kept out of Recent too.
    """
    from libera.host import hooks, saving

    asked: list = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            choose_save_path=lambda name, _formats, start_in: asked.append((
                name,
                start_in,
            ))
        ),
    )

    result = saving.save_document(new_document_open, {"fileType": 0, "params": ""})

    # And not in the folder it was made in, which is our own state directory:
    # where the toolkit chooses.
    assert asked == [("Untitled.docx", None)], "plain Save did not ask where"
    assert result == {"error": 1}  # cancelled: nothing written, nothing said


def test_closing_a_new_document_cannot_save_it_in_place(new_document_open):
    """The close prompt runs on the GUI thread, where a save panel would wait
    for itself, so it cannot ask. Failing keeps the window open and says so."""
    from libera.host import saving

    assert (
        saving.save_document(new_document_open, {"fileType": 0}, may_ask=False)["error"]
        == 2
    )


def test_the_recovery_prompt_goes_to_the_gui_thread(monkeypatch):
    """AppKit is main-thread-only and says so by raising.

    File > New opens a document from a request thread, and that path asks
    whether to recover unsaved edits. Building the NSAlert where the request
    happens to be raises NSInternalInconsistencyException -- "NSWindow should
    only be instantiated on the main thread" -- and takes the request with it.
    """
    marshalled: list = []
    # On the toolkit module itself, which `dialogs` reaches through `native`
    # at the moment it asks. A patch that leaves the real one in place lets it
    # build an alert nobody can click -- so this hangs rather than fails,
    # which is how it was found.
    monkeypatch.setattr(
        window.native,
        "run_on_gui_thread",
        lambda work: marshalled.append(work) or window.Answer.NO,
    )

    assert window.ask_to_recover(Path("note.docx")) is False
    assert marshalled, "the alert was built without going to the GUI thread"


def test_work_already_on_the_gui_thread_is_not_dispatched_again():
    """Dispatching to the thread we are standing on and waiting is a deadlock."""
    assert threading.current_thread() is threading.main_thread()
    assert window.native.run_on_gui_thread(lambda: "ran here") == "ran here"


def test_a_failure_on_the_gui_thread_reaches_the_thread_that_asked(monkeypatch):
    """Not None in its place.

    The recovery prompt read None as "Open Saved Version", so a prompt that
    failed to appear went on to discard the edits it was there to offer back.
    """
    app_helper = pytest.importorskip("PyObjCTools.AppHelper")
    from libera.host.window import macos

    # pytest runs no GUI loop, so a thread of its own stands in for it.
    monkeypatch.setattr(
        app_helper, "callAfter", lambda work: threading.Thread(target=work).start()
    )

    def fail():
        msg = "no alert today"
        raise ValueError(msg)

    outcome: list = []

    def ask():
        try:
            outcome.append(macos.run_on_gui_thread(fail))
        except ValueError as e:
            outcome.append(e)

    asker = threading.Thread(target=ask)
    asker.start()
    asker.join(timeout=5)

    assert outcome, "the asking thread never came back"
    assert isinstance(outcome[0], ValueError), f"it answered {outcome[0]!r}"
