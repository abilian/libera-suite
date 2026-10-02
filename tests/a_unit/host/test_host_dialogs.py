"""What the close prompt decides, once somebody has answered it.

The GTK dialog itself is checked in the container, under Xvfb, by
`make dialog-linux`: whether a window appears and whether the answer gets back
across a thread is a thing only a display can settle. The Windows message box
is `win32.ask`, and what its Yes, No and Cancel mean is pinned below. What is here is the half
that can be wrong on any platform -- which button means keep the window, and
what happens when the save the user asked for fails.

That mapping is worth pinning because every one of its three answers has a
different cost, and two of them lose work if they are wrong.
"""

from __future__ import annotations

import pytest

from libera.host import saving
from libera.host.window import Answer, Question, dialogs, win32

# Handed to the save, which every test here replaces.
PASSED_ON = object()


@pytest.fixture
def document(tmp_path):
    """The document in the prompt.

    No real session: `_confirm_close` is reached once `confirm_close` has
    already decided there are unsaved edits, and only hands the session on to
    the save, which these tests stand in for. Building one here would suggest
    this function reads session state, which is the thing that would make the
    test lie.
    """
    doc = tmp_path / "Report.docx"
    doc.write_bytes(b"x")
    return doc


@pytest.mark.parametrize(
    ("answered", "closes"),
    [
        pytest.param(Answer.NO, True, id="Don't Save closes"),
        pytest.param(
            Answer.CANCEL, False, id="Cancel, or a dismissed dialog, keeps it"
        ),
    ],
)
def test_the_answer_that_cannot_lose_anything_is_the_default(
    monkeypatch, document, answered, closes
):
    """A dialog dismissed with the window manager is not consent to discard."""
    monkeypatch.setattr(dialogs, "ask", lambda _question: answered)
    assert dialogs._confirm_close(PASSED_ON, document) is closes


def test_save_closes_the_window(monkeypatch, document):
    monkeypatch.setattr(dialogs, "ask", lambda _question: Answer.YES)
    monkeypatch.setattr(
        saving,
        "save_document",
        lambda _session, _params, **_: {"error": saving.SaveOutcome.SAVED, "path": "x"},
    )
    assert dialogs._confirm_close(PASSED_ON, document) is True


def test_a_failed_save_keeps_the_window_and_says_why(monkeypatch, document):
    """The window closing here would take the edits the save did not write.

    It is the one path where answering the question correctly still loses the
    document, so the failure has to stop the close rather than be reported
    after it.
    """
    said = []
    monkeypatch.setattr(dialogs, "ask", lambda _question: Answer.YES)
    monkeypatch.setattr(dialogs, "say", lambda heading, _detail: said.append(heading))
    monkeypatch.setattr(
        saving,
        "save_document",
        lambda _session, _params, **_: {"error": saving.SaveOutcome.FAILED},
    )
    assert dialogs._confirm_close(PASSED_ON, document) is False
    assert said == ["Libera Suite could not save the document"]


@pytest.mark.parametrize(
    ("clicked", "means"),
    [
        pytest.param(win32.IDYES, Answer.YES, id="Yes saves"),
        pytest.param(win32.IDNO, Answer.NO, id="No discards"),
        pytest.param(win32.IDCANCEL, Answer.CANCEL, id="Cancel keeps it"),
    ],
)
def test_windows_yes_no_cancel_mean_what_the_close_prompt_says(
    monkeypatch, clicked, means
):
    """A Win32 message box's three answers, read back as the close prompt's.

    Yes and No swapped would discard a document the user asked to save.
    """
    import ctypes

    shown = []

    def message_box(_owner, text, _caption, _style):
        shown.append(text)
        return clicked

    user32 = type("user32", (), {"MessageBoxW": staticmethod(message_box)})
    monkeypatch.setattr(win32.sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes, "windll", type("windll", (), {"user32": user32}), raising=False
    )

    chosen = win32.ask(
        Question(
            "Save changes?", "detail", yes="Save", no="Don't Save", cancel="Cancel"
        ),
        None,
    )

    assert chosen == means
    assert "Yes: Save    No: Don't Save    Cancel: Cancel" in shown[0]


def test_save_as_offers_the_formats_of_the_window_that_asked(tmp_path, monkeypatch):
    """Not the first window's.

    The panel is built on the GUI thread, which had the first window's session
    bound. Save As in a spreadsheet opened after a Words document offered
    Words formats, and wrote the spreadsheet under a .docx name. The save now
    hands the chooser the formats of the session it is saving.
    """

    from support import ScriptedShell

    from libera.host import apps, hooks, saving
    from libera.host.session import Session

    sheet = tmp_path / "budget.xlsx"
    sheet.write_bytes(b"PK")
    asking = Session(payload=tmp_path, work=tmp_path / "1", document=sheet)
    asking.work.mkdir()
    asking.write_current_document(sheet)
    offered: list = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            choose_save_path=lambda _name, formats, _start_in: offered.append(formats)
        ),
    )

    saving.save_document(asking, {"fileType": 257, "params": "saveas=true"})

    assert offered == [apps.TABLES.save_formats]


def test_save_as_starts_in_the_folder_the_document_is_in(tmp_path, monkeypatch):
    """It started wherever the last save went: Downloads, often, whatever
    folder the document had been opened from."""
    from support import ScriptedShell

    from libera.host import hooks, saving
    from libera.host.session import Session

    folder = tmp_path / "data"
    folder.mkdir()
    sheet = folder / "budget.csv"
    sheet.write_text("a,b\n", encoding="utf-8")
    asking = Session(payload=tmp_path, work=tmp_path / "1", document=sheet)
    asking.work.mkdir()
    asking.write_current_document(sheet)
    started: list = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            choose_save_path=lambda _name, _formats, start_in: started.append(start_in)
        ),
    )

    saving.save_document(asking, {"fileType": 0, "params": "saveas=true"})

    assert started == [folder]


def test_a_folder_that_has_gone_is_left_to_the_toolkit(tmp_path, monkeypatch):
    """An unmounted drive, a deleted directory: the panel starts where the last
    save went rather than somewhere that is not there."""
    handed: list = []
    monkeypatch.setattr(
        dialogs.native,
        "run_save_panel",
        lambda _name, _formats, start_in, _parent: handed.append(start_in),
    )

    dialogs.ask_save_path("budget.csv", [("CSV", "csv")], tmp_path / "unmounted")
    dialogs.ask_save_path("budget.csv", [("CSV", "csv")], tmp_path)

    assert handed == [None, tmp_path]
