"""File > New: which document, of which kind, named what.

This decision has been wrong twice -- once making an Untitled.docx in a Tables
window, once raising because the macOS menu runs every action on a thread of
its own and `H` is thread-local. Both are here now, without a window.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from libera.host import apps, window
from libera.host.session import SESSIONS, Host, use


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
    window.SESSION_BY_WINDOW.clear()
    for name, document in (("0", "letter.docx"), ("1", "budget.xlsx")):
        SESSIONS[name] = Host(
            payload=payload, work=tmp_path / "s" / name, document=Path(document)
        )
    yield
    SESSIONS.clear()
    window.SESSION_BY_WINDOW.clear()


def in_front(session: str, monkeypatch):
    """Pretend that session's window is the front one.

    Patched on `window.windows`, where new_document looks it up, and not on
    the `window` package, which only re-exports it: replacing the re-export
    leaves the definition its caller actually reads untouched.
    """
    monkeypatch.setattr(window.windows, "front_session", lambda: session)


def test_new_makes_the_kind_of_document_the_front_window_holds(windows, monkeypatch):
    in_front("1", monkeypatch)
    assert window.new_document().suffix == ".xlsx"

    in_front("0", monkeypatch)
    assert window.new_document().suffix == ".docx"


def test_new_works_on_a_thread_that_never_bound_a_session(windows, monkeypatch):
    """The macOS menu runs every action on a fresh thread. This raised."""
    in_front("1", monkeypatch)
    out: list = []

    def run():
        try:
            out.append(("ok", window.new_document()))
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
    """front_session returns "" when no window matches; New must still work."""
    in_front("", monkeypatch)
    assert window.new_document().suffix == ".docx"


def test_the_template_itself_is_never_edited(windows, monkeypatch):
    in_front("0", monkeypatch)
    made = window.new_document()
    assert made.parent != (SESSIONS["0"].payload / "empty")
    assert (
        made.read_bytes() == (SESSIONS["0"].payload / "empty" / "new.docx").read_bytes()
    )


def test_a_second_new_does_not_overwrite_the_first(windows, monkeypatch):
    in_front("0", monkeypatch)
    names = [window.new_document().name for _ in range(3)]
    assert names == ["Untitled.docx", "Untitled 2.docx", "Untitled 3.docx"]
    assert len(set(names)) == 3


def test_the_numbering_follows_the_editor_not_the_suffix(windows, monkeypatch):
    """Words and Tables number independently, because the names differ."""
    in_front("0", monkeypatch)
    window.new_document()
    in_front("1", monkeypatch)
    assert window.new_document().name == "Untitled.xlsx"


def test_a_viewer_cannot_make_a_new_document(windows, monkeypatch, tmp_path):
    """Diagrams has no blank. NotReadyError, not a stray .vsdx."""
    from libera.host.session import NotReadyError

    SESSIONS["2"] = Host(
        payload=SESSIONS["0"].payload,
        work=tmp_path / "s" / "2",
        document=Path("plan.vsdx"),
    )
    in_front("2", monkeypatch)
    with pytest.raises(NotReadyError, match="cannot create"):
        window.new_document()


def test_binding_leaves_the_thread_on_the_window_that_asked(windows, monkeypatch):
    """open_document runs next and needs the same session bound."""
    from libera.host.session import current_session

    use(SESSIONS["0"], "0")
    in_front("1", monkeypatch)
    window.new_document()
    assert current_session() == "1"


def test_an_untitled_document_never_reaches_the_recent_list(windows, monkeypatch):
    """It is our plumbing, and the start window puts Recent in front of you.

    remember_recent refuses anything under the recents file's own directory,
    so untitled documents have to be written there -- which they were not.
    """
    from libera.host.session import H, contains

    in_front("0", monkeypatch)
    made = window.new_document()
    assert contains(H.recents.parent, made), f"{made} would be offered back as recent"


def test_the_recovery_prompt_goes_to_the_gui_thread(monkeypatch):
    """AppKit is main-thread-only and says so by raising.

    File > New opens a document from a request thread, and that path asks
    whether to recover unsaved edits. Building the NSAlert where the request
    happens to be raises NSInternalInconsistencyException -- "NSWindow should
    only be instantiated on the main thread" -- and takes the request with it.
    """
    import sys

    monkeypatch.setattr(sys, "platform", "darwin")
    marshalled: list = []
    # On `window.dialogs`, where _ask_to_recover looks it up. Patching the
    # package's re-export leaves the real one in place, and the real one
    # builds an NSAlert that nobody can click -- so this hangs rather than
    # fails, which is how it was found.
    monkeypatch.setattr(
        window.dialogs, "on_gui_thread", lambda work: marshalled.append(work) or False
    )

    assert window._ask_to_recover(Path("note.docx")) is False
    assert marshalled, "the alert was built without going to the GUI thread"


def test_work_already_on_the_gui_thread_is_not_dispatched_again():
    """Dispatching to the thread we are standing on and waiting is a deadlock."""
    assert threading.current_thread() is threading.main_thread()
    assert window.on_gui_thread(lambda: "ran here") == "ran here"
