"""A document's own text never runs as markup in the editor's page.

The page holds the bridge, so a script a document gets into it can do what
`AscDesktopEditor` does. Each document here carries an image tag whose error
handler records that it ran, in a place the editor shows when the cursor
enters it; the test finds the record empty. notes/plans/converter-hardening.md
has the plan.

Each document starts with a plain paragraph and the cursor is moved from it
into the second: the editor tells its panels about a tracked change or a
comment when the cursor arrives, and a document opens with the cursor already
inside its first paragraph, before anything is listening.
"""

from __future__ import annotations

import html
import re
import zipfile
from typing import TYPE_CHECKING

import pytest

from libera import payload

if TYPE_CHECKING:
    import pathlib

# Run, it appends its label to a list on the top window, which the test reads.
MARK = "__libera_ran"
DATE = "2026-10-29T00:00:00Z"
PLAIN = "<w:p><w:r><w:t>Plain text first.</w:t></w:r></w:p>"
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
# How long the editor takes to show a panel once the cursor is in place.
SHOWN = 3_000


def markup(label: str) -> str:
    """Markup that records `label` if it runs, escaped for an XML attribute
    or text, which is how a document carries it."""
    tag = f"<img src=x onerror=\"top.{MARK}=(top.{MARK}||[]).concat('{label}')\">"
    return html.escape(tag, quote=True)


def text(words: str) -> str:
    return f'<w:t xml:space="preserve">{words}</w:t>'


def tracked_font() -> dict:
    font = markup("font")
    return {
        "body": (
            f'<w:p><w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>'
            f'<w:rPrChange w:id="1" w:author="A" w:date="{DATE}"><w:rPr/>'
            f"</w:rPrChange></w:rPr>{text('A font, tracked.')}</w:r></w:p>"
        )
    }


def tracked_style() -> dict:
    return {
        "body": (
            '<w:p><w:pPr><w:pStyle w:val="Hostile"/>'
            f'<w:pPrChange w:id="1" w:author="A" w:date="{DATE}"><w:pPr/>'
            f"</w:pPrChange></w:pPr><w:r>{text('A style, tracked.')}</w:r></w:p>"
        ),
        "style": markup("style"),
    }


def tracked_author() -> dict:
    return {
        "body": (
            f'<w:p><w:ins w:id="1" w:author="{markup("author")}" w:date="{DATE}">'
            f"<w:r>{text('Inserted, tracked.')}</w:r></w:ins></w:p>"
        )
    }


def comment() -> dict:
    return {
        "body": (
            '<w:p><w:commentRangeStart w:id="0"/>'
            f"<w:r>{text('Commented text.')}</w:r>"
            '<w:commentRangeEnd w:id="0"/>'
            '<w:r><w:commentReference w:id="0"/></w:r></w:p>'
        ),
        "comment": (
            f'<w:comment w:id="0" w:author="{markup("comment author")}" '
            f'w:date="{DATE}" w:initials="X"><w:p><w:r>'
            f"{text(markup('comment text'))}</w:r></w:p></w:comment>"
        ),
    }


def link() -> dict:
    return {
        "body": (
            f'<w:p><w:hyperlink w:anchor="{markup("link anchor")}" '
            f'w:tooltip="{markup("link tooltip")}"><w:r>{text("A link.")}</w:r>'
            "</w:hyperlink></w:p>"
        )
    }


def make_docx(path: pathlib.Path, case: dict) -> pathlib.Path:
    """The payload's blank, with a plain paragraph then the case's."""
    blank = payload.resolve().root / "empty" / "new.docx"
    with zipfile.ZipFile(blank) as z:
        parts = {n: z.read(n).decode() for n in z.namelist()}
    body = PLAIN + case["body"]
    parts["word/document.xml"], n = re.subn(
        r"(<w:body>).*?(<w:sectPr\b)",
        lambda m: m.group(1) + body + m.group(2),
        parts["word/document.xml"],
        flags=re.DOTALL,
    )
    assert n == 1, "the blank's body has changed shape"
    if "style" in case:
        parts["word/styles.xml"] = parts["word/styles.xml"].replace(
            "</w:styles>",
            '<w:style w:type="paragraph" w:styleId="Hostile">'
            f'<w:name w:val="{case["style"]}"/><w:basedOn w:val="Normal"/>'
            "</w:style></w:styles>",
        )
    if "comment" in case:
        parts["word/comments.xml"] = f"<w:comments {W}>{case['comment']}</w:comments>"
        parts["word/_rels/document.xml.rels"] = parts[
            "word/_rels/document.xml.rels"
        ].replace(
            "</Relationships>",
            '<Relationship Id="rIdComments" Type="http://schemas.openxmlformats'
            '.org/officeDocument/2006/relationships/comments" '
            'Target="comments.xml"/></Relationships>',
        )
        parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
            "</Types>",
            '<Override PartName="/word/comments.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>'
            "</Types>",
        )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return path


def ran(editor) -> list[str]:
    return editor.page.evaluate(f"() => window.{MARK} || []")


@pytest.mark.parametrize(
    "case",
    [tracked_font, tracked_style, tracked_author, comment, link],
    ids=lambda c: c.__name__,
)
def test_what_a_document_names_is_shown_as_text(editor_with, tmp_path, case):
    document = make_docx(tmp_path / f"{case.__name__}.docx", case())
    editor = editor_with([], document=document)

    editor.press("ControlOrMeta+Home")
    editor.page.keyboard.press("ArrowDown")
    editor.page.keyboard.press("ArrowRight")
    # A comment opens on a click in its text, not on the cursor arriving.
    if case is comment:
        editor.page.locator("iframe").first.click(position={"x": 380, "y": 305})
    # A link's tooltip comes with the pointer over it.
    if case is link:
        editor.page.mouse.move(345, 305)
        editor.page.mouse.move(350, 305)
    editor.page.wait_for_timeout(SHOWN)

    assert ran(editor) == []
    # Shown, as text: a panel that never opened would pass the line above.
    assert "onerror" in editor.frame.evaluate("() => document.body.innerText")


# Under Excel's 31 characters for a sheet name; sets a flag `ran` also reads.
SHORT = html.escape("<img src=x onerror=top.Z=1>", quote=True)


def sheet_name() -> dict:
    return {"sheet": SHORT, "cells": ""}


def formula_result() -> dict:
    tag = markup("formula")
    return {
        "sheet": "Sheet1",
        "cells": (
            '<row r="1"><c r="A1" t="str"><f>CONCATENATE(A2)</f></c></row>'
            f'<row r="2"><c r="A2" t="inlineStr"><is><t>{tag}</t></is></c></row>'
        ),
    }


def make_xlsx(path: pathlib.Path, case: dict) -> pathlib.Path:
    """The payload's blank workbook, its sheet named and filled by the case."""
    blank = payload.resolve().root / "empty" / "new.xlsx"
    with zipfile.ZipFile(blank) as z:
        parts = {n: z.read(n).decode() for n in z.namelist() if not n.endswith("/")}
    parts["xl/workbook.xml"] = parts["xl/workbook.xml"].replace(
        'name="Sheet1"', f'name="{case["sheet"]}"'
    )
    parts["xl/worksheets/sheet1.xml"] = parts["xl/worksheets/sheet1.xml"].replace(
        "<sheetData/>", f"<sheetData>{case['cells']}</sheetData>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return path


@pytest.mark.parametrize("case", [sheet_name, formula_result], ids=lambda c: c.__name__)
def test_what_a_workbook_names_is_shown_as_text(editor_with, tmp_path, case):
    document = make_xlsx(tmp_path / f"{case.__name__}.xlsx", case())
    editor = editor_with([], document=document)

    # The Formula Wizard shows the selected cell's formula and its result.
    if case is formula_result:
        editor.frame.click("#ce-func-label")
    editor.page.wait_for_timeout(SHOWN)

    assert ran(editor) == []
    assert not editor.page.evaluate("() => window.Z")
    assert "onerror" in editor.frame.evaluate("() => document.body.innerText")
