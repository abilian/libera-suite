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
from support import NESTED, make_nested_pdf, make_pdf, render

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


def test_pages_moved_keep_what_they_inherit(
    editor_with, tmp_path, needs_the_pdf_editor
):
    """Each page inherits its size and rotation from its own Pages node, and
    a moved page is written with them on itself. Reversing three pages takes
    two moves, and x2t took the second page's from the third's node: the
    page it read them from was the one at its position in the original, not
    the one it was writing (ElixirOffice's 0.2.2; core 0178)."""
    pdf = tmp_path / "Pages.pdf"
    make_nested_pdf(pdf)
    original = pdf.read_bytes()
    editor = editor_with([], document=pdf)
    session = next(iter(sessions.SESSIONS.values()))

    # What a drop in the thumbnails does (thumbnails.js, reorderPagesMultiple).
    editor.frame.evaluate(
        "() => { const d = Asc.editor.getPDFDoc();"
        " for (const [from, to] of [[2, 0], [2, 1]])"
        "   d.DoAction(() => d.MovePages([from], to),"
        "     AscDFH.historydescription_Pdf_MovePage, null, [0, 1, 2]); }"
    )
    deadline = time.monotonic() + 10
    while not session.change_log and time.monotonic() < deadline:
        time.sleep(0.2)
    saved = tmp_path / "saved.pdf"
    convert.export(session, saved, 513, None)

    data = saved.read_bytes()
    assert data.startswith(original)

    def latest(number: int) -> bytes:
        """An incremental update appends, so the last definition wins."""
        start = data.rindex(b"\n%d 0 obj" % number)
        return data[start : data.index(b"endobj", start)]

    def inherited(number: int, key: bytes) -> bytes | None:
        while True:
            found = re.search(rb"/%s\s*(\[[^\]]*\]|\d+)" % key, latest(number))
            if found:
                return b" ".join(found.group(1).strip(b"[] ").split())
            parent = re.search(rb"/Parent (\d+) 0 R", latest(number))
            if parent is None:
                return None
            number = int(parent.group(1))

    def pages(number: int) -> list[int]:
        kids = re.search(rb"/Kids\s*\[([^\]]*)\]", latest(number))
        if kids is None:
            return [number]
        refs = [int(n) for n in re.findall(rb"(\d+) 0 R", kids.group(1))]
        return [page for kid in refs for page in pages(kid)]

    # make_nested_pdf numbers page n's object 5 + 3n; its pages, reversed.
    order = pages(2)
    assert order == [5 + 3 * n for n in reversed(range(len(NESTED)))]
    found = [
        (inherited(page, b"MediaBox"), inherited(page, b"Rotate")) for page in order
    ]
    assert found == [
        (b"0 0 %d %d" % (width, height), b"%d" % rotate)
        for width, height, rotate in reversed(NESTED)
    ]
