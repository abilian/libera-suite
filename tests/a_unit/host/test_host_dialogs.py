"""What the close prompt decides, once somebody has answered it.

The GTK dialog itself is checked in the container, under Xvfb, by
`make dialog-linux`: whether a window appears and whether the answer gets back
across a thread is a thing only a display can settle. The Windows message box
is `_win_ask`, and what its Yes, No and Cancel mean is pinned below. What is here is the half
that can be wrong on any platform -- which button means keep the window, and
what happens when the save the user asked for fails.

That mapping is worth pinning because every one of its three answers has a
different cost, and two of them lose work if they are wrong.
"""

from __future__ import annotations

import pytest

from libera.host import convert
from libera.host.window import dialogs


@pytest.fixture
def document(tmp_path):
    """The document in the prompt.

    No session: `_confirm_close` is reached once `confirm_close` has
    already decided there are unsaved edits, and takes the document from it.
    Building one here would suggest this function reads session state, which
    is the thing that would make the test lie.
    """
    doc = tmp_path / "Report.docx"
    doc.write_bytes(b"x")
    return doc


@pytest.mark.parametrize(
    ("answered", "closes"),
    [
        pytest.param(dialogs.CLOSE_DISCARD, True, id="Don't Save closes"),
        pytest.param(dialogs.CLOSE_CANCEL, False, id="Cancel keeps the window"),
        pytest.param(-1, False, id="a dismissed dialog keeps the window"),
    ],
)
def test_the_answer_that_cannot_lose_anything_is_the_default(
    monkeypatch, document, answered, closes
):
    """A dialog dismissed with the window manager is not consent to discard."""
    monkeypatch.setattr(dialogs, "_ask", lambda *_, **__: answered)

    assert dialogs._confirm_close(document) is closes


def test_save_closes_the_window(monkeypatch, document):
    monkeypatch.setattr(dialogs, "_ask", lambda *_, **__: dialogs.CLOSE_SAVE)
    monkeypatch.setattr(convert, "save_document", lambda _params: {})

    assert dialogs._confirm_close(document) is True


def test_a_failed_save_keeps_the_window_and_says_why(monkeypatch, document):
    """The window closing here would take the edits the save did not write.

    It is the one path where answering the question correctly still loses the
    document, so the failure has to stop the close rather than be reported
    after it.
    """
    said = []
    monkeypatch.setattr(dialogs, "_ask", lambda *args, **_: said.append(args) or 0)
    monkeypatch.setattr(
        convert, "save_document", lambda _params: {"error": "no such directory"}
    )

    assert dialogs._confirm_close(document) is False
    assert said[-1][0] == "Libera Suite could not save the document"


@pytest.mark.parametrize(
    ("clicked", "means"),
    [
        pytest.param(dialogs.IDYES, dialogs.CLOSE_SAVE, id="Yes saves"),
        pytest.param(dialogs.IDNO, dialogs.CLOSE_DISCARD, id="No discards"),
        pytest.param(dialogs.IDCANCEL, dialogs.CLOSE_CANCEL, id="Cancel keeps it"),
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
    monkeypatch.setattr(dialogs.sys, "platform", "win32")
    monkeypatch.setattr(dialogs, "front_window", lambda: None)
    monkeypatch.setattr(
        ctypes, "windll", type("windll", (), {"user32": user32}), raising=False
    )

    chosen = dialogs._ask(
        "Save changes?",
        "detail",
        ("Save", "Cancel", "Don't Save"),
        windows=(dialogs.CLOSE_SAVE, dialogs.CLOSE_DISCARD, dialogs.CLOSE_CANCEL),
    )

    assert chosen == means
    assert "Yes: Save    No: Don't Save    Cancel: Cancel" in shown[0]
