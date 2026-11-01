"""Which of Office's everyday keys each editor answers, counted.

One table per editor: the key Microsoft documents for Word, Excel or
PowerPoint, what it does there, and a check read off the editor once the key
is pressed. A row the editor does not answer says why, and stays in the table:
the test holds the table both ways, so a key that stops working fails it, and
so does an absent one that starts to.

`Mod` is Ctrl, or Cmd on a Mac, as Playwright's ControlOrMeta. The editor
reads Cmd for Ctrl on a Mac for nearly all of these, so a row says so only
when it does not.

What this measures is the page: the key reaches the editor through the bridge
and does its job. Whether the window lets it through first is the webview's
business and a real application's, out of a browser's reach; on Linux the GTK
menu owns Ctrl-N, Ctrl-O and Ctrl-W (menu/gtk.py), and test_keyboard.py has
those three.

Each row starts from the same state (`Editor`), so a row that fails does not
take the next with it.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass

import pytest

from libera import payload as payload_mod
from libera.host import apps

MAC = sys.platform == "darwin"


@dataclass(frozen=True)
class Key:
    keys: str
    does: str
    check: str
    before: str = ""
    absent: str = ""
    # The editor's key on a Mac, where it is not `keys` with Cmd for Ctrl.
    mac: str = ""

    @property
    def pressed(self) -> str:
        return self.mac if MAC and self.mac else self.keys


@dataclass(frozen=True)
class Editor:
    """One editor, and how to bring it back to the same state before a row.

    `restore` puts back through the editor's API what keys cannot undo, then
    `focus` is clicked, `clear` pressed, `text` typed and `select` pressed.
    """

    app: apps.App
    restore: str
    focus: tuple[str, dict]
    clear: str
    text: str
    select: str
    prelude: str
    keys: tuple[Key, ...]


# Word's heading keys. The editor's own are Alt-1 to Alt-3 off a Mac, and
# Ctrl-Option or Cmd-Option on one, where Cmd-Option does nothing: Option
# changes the character typed (Cmd-Option-1 is "¡"), and the editor reads that.
HEADINGS = "the editor's is Alt+1, or Ctrl-Option-1 on a Mac"

MODAL = "[...document.querySelectorAll('.modals-mask')].some(e => getComputedStyle(e).display !== 'none')"

WORDS = Editor(
    apps.WORDS,
    restore="Asc.editor.put_ShowParaMarks(false); Asc.editor.zoom100();",
    focus=("#id_viewer_overlay", {"x": 600, "y": 200}),
    clear="Mod+a Delete",
    text="Hello world",
    select="Mod+a",
    prelude=(
        "const A = Asc.editor, L = A.WordControl.m_oLogicDocument,"
        " t = L.GetCalculatedTextPr(), p = L.GetCalculatedParaPr();"
    ),
    keys=(
        Key("Mod+b", "Bold", "t.Bold"),
        Key("Mod+i", "Italic", "t.Italic"),
        Key("Mod+u", "Underline", "t.Underline"),
        Key(
            "Mod+Equal",
            "Subscript",
            "t.VertAlign === AscCommon.vertalign_SubScript",
            absent="the editor's zoom in; its subscript is Mod+Period",
        ),
        Key(
            "Mod+Shift+Equal",
            "Superscript",
            "t.VertAlign === AscCommon.vertalign_SuperScript",
            absent="its superscript is Mod+Comma",
        ),
        Key(
            "Mod+Period",
            "Subscript, the editor's key",
            "t.VertAlign === AscCommon.vertalign_SubScript",
        ),
        Key(
            "Mod+Comma",
            "Superscript, the editor's key",
            "t.VertAlign === AscCommon.vertalign_SuperScript",
        ),
        Key("Mod+BracketRight", "Font size up one point", "t.FontSize === 12"),
        Key("Mod+BracketLeft", "Font size down one point", "t.FontSize === 10"),
        Key(
            "Mod+Shift+Period",
            "Font size up a step",
            "t.FontSize > 11",
            absent="not bound; Mod+BracketRight goes up a point",
        ),
        Key("Mod+Space", "Clear character formatting", "!t.Bold", before="Mod+b"),
        Key("Mod+e", "Center", "p.Jc === AscCommon.align_Center"),
        Key("Mod+r", "Align right", "p.Jc === AscCommon.align_Right"),
        Key("Mod+j", "Justify", "p.Jc === AscCommon.align_Justify"),
        Key("Mod+l", "Align left", "p.Jc === AscCommon.align_Left", before="Mod+e"),
        Key("Mod+m", "Indent", "p.Ind.Left > 0"),
        Key("Mod+Shift+m", "Remove the indent", "p.Ind.Left === 0", before="Mod+m"),
        Key(
            "Mod+Shift+l",
            "Bulleted list",
            "L.Styles.Get(p.PStyle).Name === 'List Paragraph'",
        ),
        Key(
            "Mod+Alt+Digit1",
            "Heading 1",
            "L.Styles.Get(p.PStyle).Name === 'Heading 1'",
            absent=HEADINGS,
        ),
        Key(
            "Alt+Digit1",
            "Heading 1, the editor's key",
            "L.Styles.Get(p.PStyle).Name === 'Heading 1'",
            mac="Control+Alt+Digit1",
        ),
        Key(
            "Mod+Alt+Digit2",
            "Heading 2",
            "L.Styles.Get(p.PStyle).Name === 'Heading 2'",
            absent=HEADINGS,
        ),
        Key(
            "Alt+Digit2",
            "Heading 2, the editor's key",
            "L.Styles.Get(p.PStyle).Name === 'Heading 2'",
            mac="Control+Alt+Digit2",
        ),
        Key(
            "Mod+Alt+Digit3",
            "Heading 3",
            "L.Styles.Get(p.PStyle).Name === 'Heading 3'",
            absent=HEADINGS,
        ),
        Key(
            "Alt+Digit3",
            "Heading 3, the editor's key",
            "L.Styles.Get(p.PStyle).Name === 'Heading 3'",
            mac="Control+Alt+Digit3",
        ),
        Key("Mod+Enter", "Page break", "L.GetPagesCount() === 2"),
        Key(
            "Mod+Shift+Space",
            "Non-breaking space",
            "(L.SelectAll(), L.GetSelectedText().includes('\\u00a0'))",
            before="End",
        ),
        Key(
            "Mod+Alt+g",
            "Copyright sign, the editor's key",
            "(L.SelectAll(), L.GetSelectedText().includes('©'))",
            mac="Control+Alt+g",
        ),
        Key("Mod+z", "Undo", "!t.Bold", before="Mod+b"),
        Key("Mod+y", "Redo", "t.Bold", before="Mod+b Mod+z"),
        Key(
            "Mod+a",
            "Select all",
            "L.GetSelectedText() === 'Hello world\\r\\n'",
            before="End",
        ),
        Key("Mod+Shift+8", "Show formatting marks", "A.get_ShowParaMarks()"),
        Key("Mod+k", "Insert a link", MODAL),
        Key("Mod+f", "Find", "document.activeElement?.id === 'search-bar-text'"),
        Key(
            "Mod+h",
            "Replace",
            "!!document.querySelector('#search-adv-replace')?.offsetParent",
            mac="Control+h",
        ),
        Key("Mod+Minus", "Zoom out", "A.WordControl.m_nZoomValue < 100"),
    ),
)

TABLES = Editor(
    apps.TABLES,
    restore=(
        "const A = Asc.editor; A.asc_EditSelectAll();"
        " A.asc_emptyCells(Asc.c_oAscCleanOptions.All); A.asc_setZoom(1);"
    ),
    focus=("#ws-canvas-overlay", {"x": 300, "y": 200}),
    clear="Mod+Home",
    text="12",
    select="Enter ArrowUp",
    prelude=(
        "const A = Asc.editor, c = A.asc_getCellInfo(), f = c.asc_getXfs(),"
        " cell = (r, col) => A.wb.getWorksheet().model.getCell3(r, col).getValueWithFormat();"
    ),
    keys=(
        Key("Mod+b", "Bold", "f.asc_getFontBold()"),
        Key("Mod+i", "Italic", "f.asc_getFontItalic()"),
        Key("Mod+u", "Underline", "f.asc_getFontUnderline()"),
        Key("Mod+Digit5", "Strikethrough", "f.asc_getFontStrikeout()"),
        Key("Mod+Shift+Digit4", "Currency format", "cell(0, 0) === '$12.00'"),
        Key("Mod+Shift+Digit5", "Percent format", "cell(0, 0) === '1200.00%'"),
        Key("Mod+Shift+Digit1", "Number format", "cell(0, 0) === '12.00'"),
        # Enter, because the date is typed into the cell, not yet entered.
        Key("Mod+Semicolon Enter", "Today's date", "/\\d+\\/\\d+/.test(cell(0, 0))"),
        Key("F2", "Edit the cell", "A.asc_getCellEditMode()"),
        Key("Mod+Space", "Select the column", "A.asc_getActiveRangeStr() === 'A:A'"),
        Key("Shift+Space", "Select the row", "A.asc_getActiveRangeStr() === '1:1'"),
        Key(
            "Mod+Home",
            "Go to A1",
            "A.asc_getActiveRangeStr() === 'A1'",
            before="ArrowDown ArrowRight",
        ),
        Key("Mod+z", "Undo", "!f.asc_getFontBold()", before="Mod+b"),
        Key("Mod+y", "Redo", "f.asc_getFontBold()", before="Mod+b Mod+z"),
        Key("Mod+Shift+l", "Filter", "!!c.asc_getAutoFilterInfo()"),
        Key("Mod+1", "Format cells", MODAL),
        Key("Mod+k", "Insert a link", MODAL),
        Key(
            "Alt+Equal",
            "AutoSum",
            "A.asc_getCellEditMode()",
            before="ArrowDown",
            mac="Control+Alt+Equal",
        ),
        Key(
            "Mod+d",
            "Fill down",
            "cell(1, 0) === '12'",
            before="ArrowDown",
            absent="not bound",
        ),
        Key(
            "Mod+r",
            "Fill right",
            "cell(0, 1) === '12'",
            before="ArrowRight",
            absent="not bound",
        ),
        Key(
            "Mod+Digit9",
            "Hide the row",
            "A.wb.getWorksheet().model.getRowHidden(0)",
            absent="not bound",
        ),
        Key(
            "Mod+Digit0",
            "Hide the column",
            "A.wb.getWorksheet().model.getColHidden(0)",
            absent="the editor's zoom to 100%",
        ),
        Key(
            "Shift+F11",
            "New sheet",
            "A.asc_getWorksheetsCount() === 2",
            absent="not bound",
        ),
        Key("Mod+Equal", "Zoom in", "A.asc_getZoom() > 1"),
    ),
)

SLIDES = Editor(
    apps.SLIDES,
    restore=(
        "const A = Asc.editor; if (A.isSlideShow()) A.EndDemonstration();"
        " while (A.getCountPages() > 1) { A.goToPage(A.getCountPages() - 1); A.DeleteSlide(); }"
        " A.goToPage(0); A.zoom100();"
    ),
    focus=("#id_thumbnails", {"x": 120, "y": 60}),
    clear="",
    text="",
    select="",
    prelude="const A = Asc.editor, n = A.getCountPages(), at = A.getCurrentPage();",
    keys=(
        Key("Mod+m", "New slide", "n === 2"),
        Key("Mod+d", "Duplicate the slide", "n === 2"),
        Key("Delete", "Delete the slide", "n === 1", before="Mod+m"),
        Key("PageDown", "Next slide", "at === 1", before="Mod+m Home"),
        Key("PageUp", "Previous slide", "at === 0", before="Mod+m"),
        Key("Home", "First slide", "at === 0", before="Mod+m Mod+m"),
        Key("End", "Last slide", "at === 2", before="Mod+m Mod+m Home"),
        Key("Mod+z", "Undo", "n === 1", before="Mod+m"),
        Key("Mod+y", "Redo", "n === 2", before="Mod+m Mod+z"),
        Key("F5", "Start the slide show", "A.isSlideShow()", absent="not bound"),
        Key("Mod+Equal", "Zoom in", "A.WordControl.m_nZoomValue > 100"),
    ),
)


def play(page, keys: str) -> None:
    for key in keys.split():
        page.keyboard.press(key.replace("Mod+", "ControlOrMeta+"))


def answers(editor, table: Editor, key: Key) -> bool:
    page, frame = editor.page, editor.frame
    play(page, "Escape Escape")
    frame.evaluate(f"() => {{ {table.restore} }}")
    selector, position = table.focus
    frame.locator(selector).click(position=position, force=True)
    play(page, table.clear)
    page.keyboard.type(table.text)
    play(page, table.select)
    play(page, key.before)
    play(page, key.pressed)
    page.wait_for_timeout(300)
    return frame.evaluate(f"() => {{ {table.prelude} return !!({key.check}); }}")


@pytest.mark.parametrize("table", [WORDS, TABLES, SLIDES], ids=lambda t: t.app.name)
def test_the_keys_each_editor_answers(editor_with, tmp_path, table):
    blank = payload_mod.resolve().root / "empty" / table.app.blank
    document = tmp_path / f"keys.{table.app.ext}"
    shutil.copyfile(blank, document)
    editor = editor_with([], document=document)

    answered = {key.keys: answers(editor, table, key) for key in table.keys}

    wrong = [
        f"{key.pressed} ({key.does}): "
        + (
            f"works, but the table says {key.absent!r}"
            if key.absent
            else "does nothing"
        )
        for key in table.keys
        if answered[key.keys] == bool(key.absent)
    ]
    assert not wrong, "\n".join(wrong)
