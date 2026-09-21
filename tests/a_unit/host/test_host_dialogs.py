"""What the close prompt decides, once somebody has answered it.

The GTK dialog itself is checked in the container, under Xvfb, by
`make dialog-linux`: whether a window appears and whether the answer gets back
across a thread is a thing only a display can settle. What is here is the half
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

    No session: `_gtk_confirm_close` is reached once `confirm_close` has
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
    monkeypatch.setattr(dialogs, "_gtk_ask", lambda *_: answered)

    assert dialogs._gtk_confirm_close(document) is closes


def test_save_closes_the_window(monkeypatch, document):
    monkeypatch.setattr(dialogs, "_gtk_ask", lambda *_: dialogs.CLOSE_SAVE)
    monkeypatch.setattr(convert, "save_document", lambda _params: {})

    assert dialogs._gtk_confirm_close(document) is True


def test_a_failed_save_keeps_the_window_and_says_why(monkeypatch, document):
    """The window closing here would take the edits the save did not write.

    It is the one path where answering the question correctly still loses the
    document, so the failure has to stop the close rather than be reported
    after it.
    """
    said = []
    monkeypatch.setattr(dialogs, "_gtk_ask", lambda *args: said.append(args) or 0)
    monkeypatch.setattr(
        convert, "save_document", lambda _params: {"error": "no such directory"}
    )

    assert dialogs._gtk_confirm_close(document) is False
    assert said[-1][0] == "Libera Suite could not save the document"
