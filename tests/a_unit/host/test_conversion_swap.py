"""A conversion replaces a session's document only once it has worked.

It used to delete Editor.bin and the change log first and convert second, so
a conversion that failed took the document it was replacing with it. The
worst of it was File > Reload: it folds the edits in by converting out and
back, and when the way back failed there was nothing left -- not the log, not
the Editor.bin -- and a window reloaded onto an empty editor.

x2t is stood in for here, so this runs without a payload.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from libera.host import apps, convert, window
from libera.host.session import Session, configure


@pytest.fixture
def edited(tmp_path) -> Session:
    """A session with a document open and one edit in its log."""
    document = tmp_path / "report.docx"
    document.write_bytes(b"x")
    found = Session(
        payload=tmp_path / "payload",
        work=tmp_path / "sessions" / "0",
        document=document,
        app=apps.WORDS,
    )
    configure(found)
    found.doc.mkdir(parents=True)
    found.editor_bin.write_bytes(b"as opened")
    found.change_log.record("an edit", None, 1)
    return found


def make_x2t_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        convert,
        "run_x2t",
        lambda _session, *_args: SimpleNamespace(returncode=1, stdout="", stderr="no"),
    )


def make_x2t_write(monkeypatch, content: bytes) -> None:
    """x2t's three-argument form: the second argument is what it writes."""

    def run(_session, *args):
        convert.pathlib.Path(args[1]).write_bytes(content)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(convert, "run_x2t", run)


def test_a_failed_conversion_leaves_the_session_as_it_was(edited, monkeypatch):
    make_x2t_fail(monkeypatch)

    assert convert.convert_to_editor_bin(edited, edited.document) is False

    assert edited.editor_bin.read_bytes() == b"as opened"
    assert edited.change_log


def test_a_conversion_that_works_replaces_the_document_and_its_log(edited, monkeypatch):
    make_x2t_write(monkeypatch, b"converted")

    assert convert.convert_to_editor_bin(edited, edited.document) is True

    assert edited.editor_bin.read_bytes() == b"converted"
    assert not edited.change_log


def test_a_reload_that_cannot_reopen_its_fold_keeps_the_edits(edited, monkeypatch):
    """The fold exports fine and then cannot read its own output back."""
    monkeypatch.setattr(
        convert, "export", lambda _s, staged, *_: staged.write_bytes(b"merged") or True
    )
    make_x2t_fail(monkeypatch)

    assert window.windows.fold_changes_in(edited) is False

    assert edited.editor_bin.read_bytes() == b"as opened"
    assert edited.change_log


def test_a_reload_whose_fold_fails_leaves_the_window_and_says_so(edited, monkeypatch):
    """Reloading anyway lost the edits on the next keystroke: the new editor
    counts from nought, and its first change cut the log back to nothing."""
    loaded: list[str] = []
    said: list[str] = []

    shown = SimpleNamespace(uid="shown", load_url=loaded.append)

    monkeypatch.setattr(window.windows, "find_window", lambda _session: shown)
    monkeypatch.setattr(window.windows, "fold_changes_in", lambda _session: False)
    monkeypatch.setattr(window.dialogs, "say", lambda heading, _: said.append(heading))

    window.dialogs.reload(edited, 8080)

    assert loaded == []
    assert said == ["Libera Suite could not reload the document"]
