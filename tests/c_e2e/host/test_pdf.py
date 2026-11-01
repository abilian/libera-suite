"""A PDF in the PDF editor, in a real browser: it opens, and a comment saves.

It could not open at all until sdkjs patch 0005: CPDFDoc assigned three fields
its prototype defines as getters, which strict mode refuses. Saving goes
through x2t, which replays the change log onto the original and appends the
result: an incremental update, measured on 2026-10-29
(notes/plans/release-0.7.md, item B).
"""

from __future__ import annotations

import re
import time

import pytest
from support import make_pdf, render

from libera import payload as payload_mod
from libera.host import convert, session as sessions

MARK = "zqx-annotation-4471"


@pytest.fixture
def needs_the_pdf_editor():
    root = payload_mod.resolve().root
    if not (root / "web-apps" / "apps" / "pdfeditor").is_dir():
        pytest.skip("this payload has no PDF editor (payload 0.7 ships one)")


def test_a_pdf_opens_and_shows_its_text(editor_with, tmp_path, needs_the_pdf_editor):
    pdf = tmp_path / "Report.pdf"
    make_pdf(pdf, "Hello from a PDF")

    editor = editor_with([], document=pdf)

    assert "pdfeditor" in editor.frame.url
    assert editor.report()["errors"] == []
    # What was drawn, not what was parsed: the document area only, so the
    # toolbar's icons cannot pass for text.
    shot = tmp_path / "page.png"
    editor.frame.locator("#id_viewer").screenshot(path=str(shot))
    assert render.bands(render.ink_rows(str(shot))), "nothing was drawn on the page"


def test_a_comment_saves_as_an_incremental_update(
    editor_with, tmp_path, needs_the_pdf_editor
):
    """The original's bytes first, then the comment, its text in /Contents in
    UTF-16, each byte pair written with the zero escaped."""
    pdf = tmp_path / "Report.pdf"
    make_pdf(pdf, "Hello from a PDF")
    original = pdf.read_bytes()
    editor = editor_with([], document=pdf)
    session = next(iter(sessions.SESSIONS.values()))

    editor.frame.evaluate(
        "(m) => { const d = new Asc.asc_CCommentDataWord(null); d.asc_putText(m);"
        " d.asc_putUserName('Tester'); return Asc.editor.asc_addComment(d); }",
        MARK,
    )
    deadline = time.monotonic() + 10
    while not session.change_log and time.monotonic() < deadline:
        time.sleep(0.2)
    saved = tmp_path / "saved.pdf"
    convert.export(session, saved, 513, None)

    data = saved.read_bytes()
    assert data.startswith(original)
    update = data[len(original) :]
    assert b"/Subtype /Text" in update
    contents = re.search(rb"/Contents \((.*?)\)\s*/", update, re.DOTALL)
    assert contents is not None
    text = contents.group(1).replace(b"\\000", b"\0").decode("utf-16")
    assert MARK in text
