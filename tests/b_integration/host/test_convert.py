"""x2t, run out of the payload for real.

The unit tests can check what job file we write; only this can check that x2t
accepts it. Every conversion here starts from the Editor.bin the `opened`
fixture produced, which is the same thing a save does.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import zipfile
from typing import TYPE_CHECKING

import pytest
from support import ScriptedShell, repo_root
from support.blank import with_body
from support.charts import linked_as_chart_docx, sunburst_docx
from support.make_sample_docx import solid_png
from support.pictures import (
    RELATIONSHIPS,
    thin_pen_wmf,
    wmf_docx,
    write_pic_bullet_docx,
)
from support.protected import make_protected
from support.render import colour_box

from libera import payload as payload_mod
from libera.host import apps, hooks, opening, session as sessions
from libera.host.convert import ConversionError, export
from libera.host.saving import SaveRequest, save_document
from libera.host.session import Session

if TYPE_CHECKING:
    import pathlib


def test_opening_a_document_produces_an_editor_bin(opened: Session):
    assert opened.editor_bin.stat().st_size > 0


# From each editor's blank, so an editor without one, the PDF editor's, is not
# here: tests/c_e2e/host/test_pdf.py saves a PDF.
OFFERED = [(app, ext) for app in apps.ALL if app.blank for _, ext in app.save_formats]


SENTENCE = "Libera keeps this sentence"


def _write_source(app: apps.App, tmp_path: pathlib.Path) -> pathlib.Path:
    """A document of `app`'s kind holding SENTENCE.

    Words reads it from a .txt and Tables from a .csv: x2t's Editor.bin from a
    .txt has no section properties, the shape that made Save As RTF write no
    text through payloads 0.2 to 0.4. Slides has no plain-text source, so the
    sentence goes into the blank's title.
    """
    if app.name == "words":
        source = tmp_path / "source.txt"
        source.write_text(SENTENCE + "\n", encoding="utf-8")
        return source
    if app.name == "tables":
        source = tmp_path / "source.csv"
        source.write_text(SENTENCE + "\n", encoding="utf-8")
        return source
    assert app.blank is not None
    blank = payload_mod.resolve().root / "empty" / app.blank
    source = tmp_path / f"source.{app.ext}"
    empty_title = '<a:p><a:endParaRPr lang="en-US" dirty="0"/></a:p>'
    titled = f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{SENTENCE}</a:t></a:r></a:p>'
    with zipfile.ZipFile(blank) as zin, zipfile.ZipFile(source, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item)
            if item.filename == "ppt/slides/slide1.xml":
                xml = data.decode("utf-8-sig")
                assert empty_title in xml, "the blank's title is not where it was"
                data = xml.replace(empty_title, titled, 1).encode()
            zout.writestr(item, data)
    return source


def _read_text(path: pathlib.Path) -> bytes:
    """Everything in `path` that can hold text, as bytes to search, with each
    run of whitespace made one space.

    A package's parts, unpacked; a
    PDF's text layer through pdftotext, which breaks a title across lines;
    RTF's text, out of its \\u escapes; anything else as it is.
    """
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            data = b"\n".join(z.read(name) for name in z.namelist())
    elif path.suffix == ".pdf":
        pdftotext = shutil.which("pdftotext")
        if pdftotext is None:
            pytest.skip("no pdftotext to read the PDF's text layer")
        run = subprocess.run(
            [pdftotext, str(path), "-"], capture_output=True, check=True
        )
        data = run.stdout
    elif path.suffix == ".rtf":
        data = read_rtf_text(path).encode()
    else:
        data = path.read_bytes()
    return re.sub(rb"\s+", b" ", data)


@pytest.mark.parametrize(
    ("app", "ext"), OFFERED, ids=[f"{a.name}-{e}" for a, e in OFFERED]
)
def test_every_format_every_editor_offers_keeps_the_text(
    tmp_path: pathlib.Path, app: apps.App, ext: str
):
    """The Save As popup promises these, for each editor in turn, and each
    one has to carry the document's text, not just exist.

    x2t refuses a fair few ids sitting right beside the ones it accepts -- xls
    (258), ppt (130), odg (140), every legacy binary and flat-XML format -- so
    the only way to know which is which is to ask it. And it exits 0 having
    written a well-formed file with no body: Save As RTF did that for three
    payloads while this test checked only that the file was not empty.
    """
    session = open_in(app, _write_source(app, tmp_path), tmp_path / app.name)
    out = tmp_path / f"out.{ext}"

    export(session, out, app.ids_by_ext[ext], None)

    assert SENTENCE.encode() in _read_text(out)


def test_an_xlsb_opens_with_its_text(tmp_path: pathlib.Path):
    """Tables opens .xlsb, Excel's binary workbook, and no longer saves one:
    x2t crashed writing it on Linux (SIGSEGV), in payloads 0.4.1 and 0.5.

    Opened as x2t opens a .xlsx, it came back an empty presentation, exit 0,
    for Excel's own files too. This one was written by x2t on macOS, where
    writing it does not crash."""
    document = tmp_path / "sentence.xlsb"
    shutil.copy(repo_root() / "tests/b_integration/host/data/sentence.xlsb", document)
    table = open_in(apps.TABLES, document, tmp_path / "session")
    out = tmp_path / "out.xlsx"

    export(table, out, apps.TABLES.ids_by_ext["xlsx"], None)

    assert SENTENCE.encode() in _read_text(out)


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_no_editor_offers_a_format_its_converter_does_not_know(app: apps.App):
    assert {ext for _, ext in app.save_formats} <= set(app.ids_by_ext)


def test_plain_save_overwrites_the_document_that_is_open(opened: Session):
    """fileType 0 means "whatever it already was", and no dialog is involved."""
    before = opened.document.stat().st_mtime_ns
    result = save_document(opened, SaveRequest())

    assert result == {"error": 0, "path": str(opened.document)}
    assert opened.document.stat().st_mtime_ns != before
    # Saved means nothing left to recover.
    assert not opened.unsaved_marker.is_file()


@pytest.mark.parametrize(
    ("name", "app"),
    [
        ("SimpleMacro.docm", apps.WORDS),
        ("SimpleMacro.xlsm", apps.TABLES),
        ("SimpleMacro.pptm", apps.SLIDES),
    ],
)
def test_a_plain_save_keeps_the_documents_vba(
    name: str, app: apps.App, tmp_path: pathlib.Path
):
    """Libera runs no VBA, and a save must not take it out of the file.

    A .docm had no format id here, so a plain Save asked for a new file in a
    format with nowhere to keep the macros, and the document's own was left as
    it was."""
    document = tmp_path / name
    shutil.copy(repo_root() / "tests/b_integration/host/data" / name, document)
    vba = _read_vba(document)
    opened = open_in(app, document, tmp_path / "session")

    result = save_document(opened, SaveRequest())

    assert result == {"error": 0, "path": str(document)}
    assert _read_vba(document) == vba


def _read_vba(document: pathlib.Path) -> bytes:
    with zipfile.ZipFile(document) as package:
        (name,) = (n for n in package.namelist() if n.endswith("/vbaProject.bin"))
        return package.read(name)


def test_save_as_follows_the_extension_the_user_typed(
    opened: Session, tmp_path: pathlib.Path, monkeypatch
):
    """The chooser's suffix wins over the format the editor asked for.

    The popup and the typed name can disagree; the name is what the user sees,
    so it decides, and the format follows it.
    """
    chosen = tmp_path / "elsewhere.odt"
    named: list[pathlib.Path] = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            choose_save_path=lambda _name, _formats, _start_in: str(chosen),
            show_document=lambda _session, document: named.append(document),
        ),
    )

    result = save_document(opened, SaveRequest(file_type=65, save_as=True))

    assert result == {"error": 0, "path": str(chosen)}
    assert chosen.read_bytes()[:2] == b"PK"  # an ODF package, not a docx
    # Save As moves the session onto the new file; a plain Save now goes there,
    # and the window (and its tab) is called after it.
    assert opened.current_file.read_text() == str(chosen)
    assert named == [chosen]


def test_a_failed_save_as_leaves_the_session_on_the_open_document(
    opened: Session, tmp_path: pathlib.Path, monkeypatch
):
    """Until the new file exists, the document is still where it was.

    The session used to move first, so after a failed Save As the next plain
    Save wrote to a path the user had abandoned, and the recovery marker
    named a file that did not exist.
    """
    elsewhere = str(tmp_path / "elsewhere.odt")
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(choose_save_path=lambda _name, _formats, _start_in: elsewhere),
    )

    def fails(*_a):
        msg = "x2t could not write elsewhere.odt (exit status 1)"
        raise ConversionError(msg)

    monkeypatch.setattr("libera.host.convert.export", fails)

    result = save_document(opened, SaveRequest(file_type=65, save_as=True))

    assert result["error"] == 2
    assert opened.current_file.read_text() == str(opened.document)


def test_a_cancelled_save_as_writes_nothing_and_says_nothing(
    opened: Session, monkeypatch
):
    """Error 1 is DesktopOfflineAppDocumentEndSave's "stay quiet"."""
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(choose_save_path=lambda _name, _formats, _start_in: ""),
    )
    before = opened.document.stat().st_mtime_ns

    assert save_document(opened, SaveRequest(file_type=65, save_as=True)) == {
        "error": 1
    }
    assert opened.document.stat().st_mtime_ns == before


def test_printing_makes_a_pdf_beside_the_session_not_over_the_document(
    opened: Session, monkeypatch
):
    """Print is a PDF save with no destination: it must not touch the docx."""
    monkeypatch.setattr("libera.host.desktop.open_externally", lambda _p: True)
    before = opened.document.stat().st_mtime_ns

    result = save_document(opened, SaveRequest(file_type=513, printing=True))

    assert result["error"] == 0
    assert result["path"].endswith(f"{opened.document.stem}.pdf")
    assert opened.document.stat().st_mtime_ns == before


def printing_where(monkeypatch, answer):
    """A windowed shell whose save panel answers `answer`, recording what it
    was asked; and the viewer, recording what it was handed."""
    asked: list = []
    shown: list = []

    def choose(name, formats, start_in):
        asked.append((name, formats, start_in))
        return answer

    monkeypatch.setattr(hooks, "shell", ScriptedShell(choose_save_path=choose))
    monkeypatch.setattr(
        "libera.host.desktop.open_externally", lambda path: shown.append(path) or True
    )
    return asked, shown


def test_a_print_asks_where_starting_beside_the_document(
    opened: Session, monkeypatch, tmp_path
):
    chosen = tmp_path / "elsewhere" / "Printed.pdf"
    chosen.parent.mkdir()
    asked, shown = printing_where(monkeypatch, str(chosen))

    result = save_document(opened, SaveRequest(file_type=513, printing=True))

    [(name, formats, start_in)] = asked
    assert name == f"{opened.document.stem}.pdf"
    assert start_in == opened.document.parent
    assert [ext for _, ext in formats] == ["pdf"], "a print offers PDF only"
    assert chosen.read_bytes()[:5] == b"%PDF-"
    assert shown == [chosen], "the viewer is handed the file the user kept"
    assert result["path"] == str(chosen)
    assert opened.read_current_document() == opened.document, (
        "a print is not a Save As: the window stays on its document"
    )


def test_a_cancelled_print_makes_nothing(opened: Session, monkeypatch):
    _asked, shown = printing_where(monkeypatch, "")

    assert (
        save_document(opened, SaveRequest(file_type=513, printing=True))["error"] == 1
    )
    assert shown == []


def test_a_print_is_a_pdf_whatever_name_was_typed(
    opened: Session, monkeypatch, tmp_path
):
    _asked, shown = printing_where(monkeypatch, str(tmp_path / "Printed"))

    save_document(opened, SaveRequest(file_type=513, printing=True))

    assert shown == [tmp_path / "Printed.pdf"]
    assert (tmp_path / "Printed.pdf").read_bytes()[:5] == b"%PDF-"


def test_a_print_nothing_opens_is_a_failed_print(opened: Session, monkeypatch):
    """The PDF is made, but nothing will show it: that is not a print."""
    monkeypatch.setattr("libera.host.desktop.open_externally", lambda _p: False)

    assert (
        save_document(opened, SaveRequest(file_type=513, printing=True))["error"] == 2
    )


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_the_format_table_is_what_x2t_really_does(app: apps.App):
    """The tables are documented as measured, not copied out of the header."""
    for wanted, (ext, fmt) in app.formats.items():
        if wanted == 0:
            continue
        assert wanted == fmt, f"{ext} maps to a different id than it is asked for"


def test_a_viewer_refuses_to_save(opened: Session, tmp_path: pathlib.Path):
    """Diagrams has no format x2t will write, so saving stops at the door.

    Error 1 is DesktopOfflineAppDocumentEndSave's "not saved, say nothing".
    """
    viewer = Session(
        payload=opened.payload,
        work=tmp_path / "viewer",
        document=opened.document,
        app=apps.DIAGRAMS,
    )
    sessions.configure(viewer)
    assert save_document(viewer, SaveRequest()) == {"error": 1}


def open_in(app: apps.App, document: pathlib.Path, work: pathlib.Path) -> Session:
    session = Session(
        payload=payload_mod.resolve().root, work=work, document=document, app=app
    )
    sessions.configure(session)
    opening.open_document(session, document)
    return session


CSVS = {
    "utf8-commas.csv": ("Nom,Ville\nÉlodie,Besançon\nZoë,Łódź\n", "utf-8"),
    "cp1252-semicolons.csv": ("Nom;Ville\nÉlodie;Besançon\n", "cp1252"),
    "utf8-tabs.tsv": ("Nom\tVille\nÉlodie\tBesançon\n", "utf-8"),
}


@pytest.mark.parametrize("name", CSVS)
def test_a_csv_opens_and_saves_the_way_it_was_written(tmp_path, name):
    """x2t refused every CSV (rc 88) until it was told how the text is written.

    Saved twice, because x2t's UTF-8 reader took the NULs it leaves past the
    end of the text for one more row: every save added an empty line.
    """
    text, encoding = CSVS[name]
    document = tmp_path / name
    document.write_bytes(text.encode(encoding))

    for n in range(2):
        table = open_in(apps.TABLES, document, tmp_path / f"session{n}")
        assert table.editor_bin.read_bytes()[:5] == b"XLSY;"
        assert save_document(table, SaveRequest()) == {
            "error": 0,
            "path": str(document),
        }

    # x2t starts UTF-8 with a byte-order mark; the rest is what was there.
    assert document.read_bytes().removeprefix(b"\xef\xbb\xbf") == text.encode(encoding)


def test_save_as_tsv_writes_tabs(tmp_path, monkeypatch):
    """The delimiter follows the file being written, not the one that is open."""
    text, encoding = CSVS["cp1252-semicolons.csv"]
    document = tmp_path / "a.csv"
    document.write_bytes(text.encode(encoding))
    chosen = tmp_path / "b.tsv"
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(choose_save_path=lambda _name, _formats, _start_in: str(chosen)),
    )
    table = open_in(apps.TABLES, document, tmp_path / "session")

    assert save_document(table, SaveRequest(save_as=True))["error"] == 0
    assert chosen.read_bytes().decode("cp1252") == text.replace(";", "\t")


@pytest.mark.parametrize(
    ("app", "ext"),
    [(apps.WORDS, "odt"), (apps.TABLES, "ods"), (apps.SLIDES, "odp")],
    ids=lambda v: getattr(v, "name", v),
)
def test_plain_save_writes_the_document_in_the_format_it_has(
    open_blank, tmp_path, app, ext
):
    """It used to go into the session as a .docx, and the .odt stayed as it was."""
    blank = open_blank(app)
    document = tmp_path / f"mine.{ext}"
    export(blank, document, app.ids_by_ext[ext], None)
    reopened = open_in(app, document, tmp_path / "reopened")
    before = document.stat().st_mtime_ns

    assert save_document(reopened, SaveRequest()) == {
        "error": 0,
        "path": str(document),
    }
    assert document.stat().st_mtime_ns != before


def test_closing_a_format_it_cannot_write_refuses_rather_than_asks(
    opened: Session, tmp_path
):
    """Closing saves on the GUI thread, where a save panel would wait for itself.

    x2t does not write .doc, so the save has to ask where; from there it fails
    instead, and the window stays open with the edits in it.
    """
    old = tmp_path / "Old.doc"
    old.write_bytes(b"")
    opened.current_file.write_text(str(old), encoding="utf-8")

    assert save_document(opened, SaveRequest(), may_ask=False) == {"error": 2}


def test_a_csv_with_an_emoji_saves_in_utf8(tmp_path):
    """A character outside the BMP, and x2t wrote one byte per character.

    Its converter to UTF-8 sized its buffer one unit per character, an emoji
    needs two, and the fallback wrote "é" as the single byte E9 throughout the
    file -- exiting 0. Patch 0030 fixes it; convert.export still refuses text
    that is not the UTF-8 it asked for, should it come back.
    """
    document = tmp_path / "list.csv"
    document.write_text("Nom,Description\nCleed,🎯 Échange sécurisé\n", "utf-8")
    table = open_in(apps.TABLES, document, tmp_path / "session")

    assert save_document(table, SaveRequest()) == {"error": 0, "path": str(document)}
    assert "Cleed,🎯 Échange sécurisé" in document.read_text(encoding="utf-8-sig")


def test_a_text_file_opens_past_an_emoji(tmp_path):
    """Without a byte-order mark, x2t's reader stopped at the first emoji: the
    same buffer as in the CSV writer, which patch 0030 sizes."""
    document = tmp_path / "notes.txt"
    document.write_text("avant\n🎯 cible\naprès\n", encoding="utf-8")
    notes = open_in(apps.WORDS, document, tmp_path / "session")
    docx = tmp_path / "out.docx"

    export(notes, docx, apps.WORDS.ids_by_ext["docx"], None)
    assert "après" in zipfile.ZipFile(docx).read("word/document.xml").decode()


def read_rtf_text(path: pathlib.Path) -> str:
    """The text of an RTF x2t wrote, which spells every character `\\uN*`."""
    body = path.read_text(encoding="ascii").split("\\fet2", 1)[1]
    return "".join(chr(int(n)) for n in re.findall(r"\\u(\d+)\*", body))


def write_docx_body(blank: pathlib.Path, document: pathlib.Path, body: str) -> None:
    """The blank's package, with `body` for the inside of its w:body."""
    with zipfile.ZipFile(blank) as src, zipfile.ZipFile(document, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == "word/document.xml":
                data = re.sub(
                    rb"<w:body>.*</w:body>",
                    f"<w:body>{body}</w:body>".encode(),
                    data,
                    flags=re.DOTALL,
                )
            dst.writestr(item, data)


PARAGRAPH = "<w:p><w:r><w:t>{}</w:t></w:r></w:p>"
BREAK = (
    '<w:p><w:pPr><w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:pPr></w:p>'
)
SECTIONLESS = {
    "no section": PARAGRAPH.format("après"),
    "a break, then none": BREAK + PARAGRAPH.format("après"),
}


@pytest.mark.parametrize("body", SECTIONLESS.values(), ids=list(SECTIONLESS))
def test_save_as_rtf_keeps_the_text_after_the_last_section(open_blank, tmp_path, body):
    """x2t's RTF writer read paragraphs into sections, made from w:sectPr only.

    A body with no closing w:sectPr lost what followed the last one, all of it
    when there was none, and exited 0 over an RTF of headers. Patch 0033.
    """
    document = tmp_path / "sectionless.docx"
    blank = open_blank(apps.WORDS)
    write_docx_body(blank.document, document, body)
    opened = open_in(apps.WORDS, document, tmp_path / "session")
    rtf = tmp_path / "out.rtf"

    export(opened, rtf, apps.WORDS.ids_by_ext["rtf"], None)
    assert "après" in read_rtf_text(rtf)


def test_a_text_file_saves_as_rtf_with_its_text(tmp_path):
    """x2t's plain text reader writes a body with no w:sectPr, the case above."""
    document = tmp_path / "notes.txt"
    document.write_text("avant\naprès\n", encoding="utf-8")
    notes = open_in(apps.WORDS, document, tmp_path / "session")
    rtf = tmp_path / "out.rtf"

    export(notes, rtf, apps.WORDS.ids_by_ext["rtf"], None)
    assert "après" in read_rtf_text(rtf)


ODF_NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'office:version="1.2"'
)


def test_an_odt_without_master_styles_keeps_its_styles(tmp_path):
    """x2t's ODF reader skipped every style when styles.xml had no
    office:master-styles, which is optional, and a generated FAQ came out
    all in the default style. Patch 0169."""
    document = tmp_path / "faq.odt"
    with zipfile.ZipFile(document, "w") as odt:
        odt.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        odt.writestr(
            "styles.xml",
            f"<office:document-styles {ODF_NS}><office:styles>"
            '<style:style style:name="Titre" style:family="paragraph">'
            '<style:text-properties fo:font-size="19pt" fo:font-weight="bold"/>'
            "</style:style></office:styles></office:document-styles>",
        )
        odt.writestr(
            "content.xml",
            f"<office:document-content {ODF_NS}><office:body><office:text>"
            '<text:p text:style-name="Titre">FAQ</text:p>'
            "</office:text></office:body></office:document-content>",
        )
    faq = open_in(apps.WORDS, document, tmp_path / "session")
    docx = tmp_path / "out.docx"

    export(faq, docx, apps.WORDS.ids_by_ext["docx"], None)
    styles = zipfile.ZipFile(docx).read("word/styles.xml").decode()
    titre = re.search(r'<w:name w:val="Titre"/>.*?</w:style>', styles)
    assert titre is not None
    assert '<w:sz w:val="38"' in titre.group()


def test_markdown_opens_and_saves(tmp_path):
    """x2t refused every .md without an encoding (rc 88)."""
    document = tmp_path / "notes.md"
    document.write_text("Un *mot* et cœur 🎯\n", encoding="utf-8")
    notes = open_in(apps.WORDS, document, tmp_path / "session")

    assert save_document(notes, SaveRequest()) == {"error": 0, "path": str(document)}
    assert "cœur 🎯" in document.read_text(encoding="utf-8")


def test_markdown_puts_no_style_of_its_own_in_the_gallery(tmp_path):
    """x2t reads Markdown as HTML, and its HTML reader names a style after
    each CSS id it compiles, text-3, text-5, and flagged every one for the
    style gallery: a document converted from Markdown offered "text-5" and
    "text-3" beside Normal (core 0198)."""
    document = tmp_path / "notes.md"
    document.write_text("# Title\n\nBody.\n\n## Part\n\nMore.\n", encoding="utf-8")
    notes = open_in(apps.WORDS, document, tmp_path / "session")
    docx = tmp_path / "notes.docx"

    export(notes, docx, apps.WORDS.ids_by_ext["docx"], None)

    styles = zipfile.ZipFile(docx).read("word/styles.xml").decode()
    gallery = [
        re.findall(r'<w:name w:val="([^"]+)"', style)[0]
        for style in re.findall(r"<w:style .*?</w:style>", styles, re.DOTALL)
        if "<w:qFormat/>" in style
    ]
    assert "Normal" in gallery
    assert not [name for name in gallery if name.startswith("text-")], gallery


MHT = (
    b"MIME-Version: 1.0\r\n"
    b'Content-Type: multipart/related; type="text/html"; boundary="b"\r\n\r\n'
    b"--b\r\nContent-Type: text/html\r\n"
    b"Content-Transfer-Encoding: quoted-printable\r\n"
    b"Content-Location: https://example.invalid/\r\n\r\n"
    b'<html><head><meta charset=3D"utf-8"></head>'
    b"<body><p>Un mot et c=C5=93ur</p></body></html>\r\n--b--\r\n"
)
FB2 = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">'
    "<description><title-info><book-title>T</book-title></title-info>"
    "</description><body><section><p>Un mot et cœur</p></section></body>"
    "</FictionBook>"
).encode()


@pytest.mark.parametrize(("ext", "content"), [("mht", MHT), ("fb2", FB2)])
def test_a_format_that_needs_an_encoding_opens(tmp_path, ext, content):
    """Words listed .mht and .fb2 and never opened either: x2t refused them
    without an encoding (rc 88), as it did .md. A web page as a browser saves
    it, quoted-printable UTF-8, and a FictionBook; Words writes neither, so
    each goes out as text."""
    document = tmp_path / f"page.{ext}"
    document.write_bytes(content)
    page = open_in(apps.WORDS, document, tmp_path / "session")
    text = tmp_path / "page.txt"

    export(page, text, apps.WORDS.ids_by_ext["txt"], None)

    assert "Un mot et cœur" in text.read_text(encoding="utf-8-sig")


def test_an_epub_opens(tmp_path):
    """Words listed .epub and never opened one either (rc 88). The EPUB is
    one Words wrote, from a text file."""
    source = tmp_path / "book.txt"
    source.write_text("Un mot et cœur\n", encoding="utf-8")
    book = tmp_path / "book.epub"
    export(
        open_in(apps.WORDS, source, tmp_path / "first"),
        book,
        apps.WORDS.ids_by_ext["epub"],
        None,
    )
    text = tmp_path / "book-again.txt"

    export(
        open_in(apps.WORDS, book, tmp_path / "second"),
        text,
        apps.WORDS.ids_by_ext["txt"],
        None,
    )

    assert "Un mot et cœur" in text.read_text(encoding="utf-8-sig")


ODF_FLAT = (
    '<?xml version="1.0" encoding="UTF-8"?><office:document'
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"'
    ' xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' office:version="1.2" office:mimetype="application/vnd.oasis.opendocument.{kind}">'
    "<office:body>{body}</office:body></office:document>"
)
FODS = ODF_FLAT.format(
    kind="spreadsheet",
    body='<office:spreadsheet><table:table table:name="S"><table:table-row>'
    '<table:table-cell office:value-type="string"><text:p>Un mot et cœur</text:p>'
    "</table:table-cell></table:table-row></table:table></office:spreadsheet>",
)
FODP = ODF_FLAT.format(
    kind="presentation",
    body='<office:presentation><draw:page draw:name="P">'
    '<draw:frame svg:x="2cm" svg:y="2cm" svg:width="10cm" svg:height="3cm">'
    "<draw:text-box><text:p>Un mot et cœur</text:p></draw:text-box></draw:frame>"
    "</draw:page></office:presentation>",
)


# What each editor saves to, for the test to read back.
SAVED_AS = {"word": "docx", "cell": "xlsx", "slide": "pptx"}


@pytest.mark.parametrize(
    ("app", "name", "content", "expected"),
    [
        (apps.WORDS, "fdo59530.doc", None, "ccc"),
        (apps.TABLES, "sheet.fods", FODS, "Un mot et cœur"),
        (apps.SLIDES, "deck.fodp", FODP, "Un mot et cœur"),
    ],
    ids=["doc", "fods", "fodp"],
)
def test_a_listed_format_opens_as_its_editors_kind(
    tmp_path, app, name, content, expected
):
    """Words listed .doc and refused every one (rc 88); Tables and Slides
    opened a flat ODF file as a text document, which saved as nothing but
    PDF. Each now opens as its editor's own kind and saves its text."""
    document = tmp_path / name
    if content is None:
        shutil.copy(repo_root() / "tests/b_integration/host/data" / name, document)
    else:
        document.write_text(content, encoding="utf-8")
    opened = open_in(app, document, tmp_path / "session")
    saved = tmp_path / f"saved.{SAVED_AS[app.doctype]}"

    export(opened, saved, app.ids_by_ext[saved.suffix[1:]], None)

    assert expected.encode() in _read_text(saved)


# --- x2t's CSV reader skipped a character every 500,000 --------------------
#
# CSVReader drops the text it has read once it passes 500,000 characters, and
# until patch 0029 never looked at the first character after the cut: a quote,
# a delimiter or a newline there split a cell or merged two. Payload 0.3's
# host modelled the loop to name the damaged rows; 0.4's converter reads them.

# 5000 rows of 100 characters: the last newline is character 499,999.
LONG = ("x" * 99 + "\n") * 5000
CUTS = {
    "a quoted cell": LONG + 'k,"a,b",z\n',
    "an empty cell": LONG + "k,,z\n",
    "a quoted row": LONG + 'k\n"a,b",z\n',
    "a blank line": LONG + "k\n\nlast\n",
    "a letter": LONG + "k,yes,z\n",
}


def read_rows(path: pathlib.Path) -> list[list[str]]:
    """The rows, without the empty cells x2t pads a short row with on saving."""
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    for row in rows:
        while row and not row[-1]:
            row.pop()
    return rows


def rows_x2t_changes(document: pathlib.Path, work: pathlib.Path) -> list[int]:
    """The first row x2t's round trip reads differently from the file, if any."""
    table = open_in(apps.TABLES, document, work)
    out = work / "out.csv"
    export(table, out, apps.TABLES.ids_by_ext["csv"], document)
    wanted, got = read_rows(document), read_rows(out)
    for number, row in enumerate(wanted, 1):
        if number > len(got) or got[number - 1] != row:
            return [number]
    return [] if len(got) == len(wanted) else [len(wanted) + 1]


@pytest.mark.parametrize("case", CUTS)
def test_x2t_reads_every_row_of_a_large_csv(tmp_path, case):
    document = tmp_path / "list.csv"
    document.write_text(CUTS[case], encoding="utf-8")

    assert rows_x2t_changes(document, tmp_path / "s") == []


def test_a_hexadecimal_value_in_a_csv_stays_text(tmp_path):
    """x2t read a cell as a number with wcstod, which reads C99 hexadecimal too:
    0x1234 came back as 4660 and an Ethereum address as 9.2233720368547758e+18,
    from an open and a save (core 0199)."""
    document = tmp_path / "addresses.csv"
    document.write_text(
        "address\n0x52908400098527886E0F7030069857D2E4169EE7\n0x1234\n-0x10\n42\n",
        encoding="utf-8",
    )

    assert rows_x2t_changes(document, tmp_path / "s") == []


BOXED = (
    '<w:p><w:r><w:t xml:space="preserve">Before </w:t></w:r><w:r><w:rPr>{}</w:rPr>'
    '<w:t>boxed</w:t></w:r><w:r><w:t xml:space="preserve"> after.</w:t></w:r></w:p>'
)
BORDER = '<w:bdr w:val="single" w:sz="8" w:space="0" w:color="000000"/>'


def open_boxed(tmp_path: pathlib.Path, rpr: str) -> Session:
    tmp_path.mkdir(exist_ok=True)
    document = tmp_path / "boxed.docx"
    write_docx_body(
        payload_mod.resolve().root / "empty" / apps.WORDS.blank,
        document,
        BOXED.format(rpr),
    )
    return open_in(apps.WORDS, document, tmp_path / "session")


def test_a_character_border_is_kept_through_a_save(tmp_path):
    """A run's border, w:bdr, had no place in the editor's binary format: a
    document read and written again lost it, in .docx and in .odt (ElixirOffice's
    #66, their fix, core 0201 and sdkjs 0008)."""
    words = open_boxed(tmp_path, BORDER)
    docx, odt = tmp_path / "out.docx", tmp_path / "out.odt"

    export(words, docx, apps.WORDS.ids_by_ext["docx"], None)
    export(words, odt, apps.WORDS.ids_by_ext["odt"], None)

    assert '<w:bdr w:val="single"' in zipfile.ZipFile(docx).read(
        "word/document.xml"
    ).decode("utf-8")
    assert 'fo:border="' in zipfile.ZipFile(odt).read("content.xml").decode("utf-8")


def dark_pixels(pdf: pathlib.Path) -> int:
    """How many pixels of the PDF's first page, drawn at 72 dpi in grey, are
    darker than mid-grey."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        pytest.skip("no pdftoppm to draw the PDF's page")
    page = subprocess.run(
        [pdftoppm, "-r", "72", "-gray", "-f", "1", "-l", "1", str(pdf)],
        capture_output=True,
        check=True,
    ).stdout
    # P5, width, height, maximum value, then a byte a pixel.
    _, width, height, _ = page.split(maxsplit=4)[:4]
    return sum(1 for b in page[-int(width) * int(height) :] if b < 128)


def test_a_character_border_is_drawn(tmp_path):
    """The box around a run with w:bdr was not drawn, in the editor or in what
    it prints. The same text with and without one: the box is the difference,
    its four sides about 140 pixels at 72 dpi."""
    pdfs = []
    for name, rpr in (("plain", ""), ("boxed", BORDER)):
        words = open_boxed(tmp_path / name, rpr)
        pdfs.append(tmp_path / f"{name}.pdf")
        export(words, pdfs[-1], apps.WORDS.ids_by_ext["pdf"], None)

    plain, boxed = (dark_pixels(pdf) for pdf in pdfs)

    assert boxed - plain > 80


def word_boxes(pdf: pathlib.Path) -> str:
    """The PDF's words with their boxes, from Poppler's pdftotext -bbox. The
    pdftotext Git for Windows ships is xpdf's, which has no -bbox."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("no pdftotext to measure the PDF's words")
    # xpdf's exits 99 on -v, so its status says nothing.
    version = subprocess.run(
        [pdftotext, "-v"], capture_output=True, text=True, check=False
    )
    if "Poppler" not in version.stdout + version.stderr:
        pytest.skip("pdftotext is not Poppler's, which alone has -bbox")
    return subprocess.run(
        [pdftotext, "-bbox", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout


def test_a_font_is_found_whatever_the_case_of_its_name(tmp_path):
    """Word, like Windows, matches font names whatever their case, and the
    editor looked them up as spelt: "Open Sans SemiBold" and "Open Sans
    ExtraBold" were drawn in a substitute, Carlito here and regular Open Sans
    with more fonts installed, where the payload's faces are "Open Sans
    Semibold" and "Open Sans Extrabold" (ElixirOffice's #65, sdkjs 0006). The
    PDF names all three faces Open Sans, so this measures the word each one
    draws: a heavier face draws it wider."""
    names = ("Open Sans", "Open Sans SemiBold", "Open Sans ExtraBold")
    document = tmp_path / "weights.docx"
    write_docx_body(
        payload_mod.resolve().root / "empty" / apps.WORDS.blank,
        document,
        "".join(
            f'<w:p><w:r><w:rPr><w:rFonts w:ascii="{name}" w:hAnsi="{name}"/>'
            "</w:rPr><w:t>Hamburgefonstiv</w:t></w:r></w:p>"
            for name in names
        ),
    )
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "weights.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    boxes = word_boxes(pdf)
    widths = [
        float(right) - float(left)
        for left, right in re.findall(
            r'<word xMin="([\d.]+)" yMin="[\d.]+" xMax="([\d.]+)"', boxes
        )
    ]
    assert len(widths) == len(names)
    assert widths[0] < widths[1] < widths[2]


def test_an_empty_paragraph_of_size_0_still_has_a_height(tmp_path):
    """Word lays out a font size below half a point as half a point, and the
    editor took w:sz="0" at its word: an empty paragraph whose mark has it had
    no height, so a CV built on 43 of them, each the anchor of a block, had
    everything drift up the page (ElixirOffice's #73, their fix, sdkjs 0009).
    Twenty such paragraphs push the next line down; without them it starts at
    the top."""
    # No spacing before or after, as in the CV: the blank's Normal has some,
    # which would move the next line whatever the font size.
    empty = (
        '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/>'
        '<w:rPr><w:sz w:val="0"/></w:rPr></w:pPr></w:p>'
    )
    after = "<w:p><w:r><w:t>After</w:t></w:r></w:p>"
    blank = payload_mod.resolve().root / "empty" / apps.WORDS.blank
    tops = []
    for name, body in (("none", after), ("twenty", empty * 20 + after)):
        document = tmp_path / f"{name}.docx"
        write_docx_body(blank, document, body)
        words = open_in(apps.WORDS, document, tmp_path / name)
        pdf = tmp_path / f"{name}.pdf"
        export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)
        tops.append(
            float(
                re.findall(r'<word xMin="[\d.]+" yMin="([\d.]+)"', word_boxes(pdf))[0]
            )
        )

    assert tops[1] - tops[0] > 5


def test_a_superscript_s_underline_is_under_the_raised_text(tmp_path):
    """Word draws a superscript's underline under the raised text, and the
    editor drew it at the line's baseline, under nothing (ElixirOffice's #67,
    their fix, sdkjs 0010). The underline's row, in the columns under "sup",
    is found on the page and must lie within the raised text's own box."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        pytest.skip("no pdftoppm to draw the PDF's page")
    document = tmp_path / "sup.docx"
    write_docx_body(
        payload_mod.resolve().root / "empty" / apps.WORDS.blank,
        document,
        '<w:p><w:r><w:rPr><w:sz w:val="48"/></w:rPr><w:t xml:space="preserve">'
        'Base</w:t></w:r><w:r><w:rPr><w:u w:val="single"/>'
        '<w:vertAlign w:val="superscript"/><w:sz w:val="48"/></w:rPr>'
        "<w:t>sup</w:t></w:r></w:p>",
    )
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "sup.pdf"
    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    boxes = {
        word: tuple(float(v) for v in box)
        for *box, word in re.findall(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">'
            r"([^<]*)</word>",
            word_boxes(pdf),
        )
    }
    # At 144 dpi, two pixels a point. P5, width, height, maximum, then a byte
    # a pixel.
    page = subprocess.run(
        [pdftoppm, "-r", "144", "-gray", "-f", "1", "-l", "1", str(pdf)],
        capture_output=True,
        check=True,
    ).stdout
    width, height = (int(v) for v in page.split(maxsplit=4)[1:3])
    pixels = page[-width * height :]
    left, top, right, _ = (round(2 * v) for v in boxes["sup"])
    bottom = round(2 * boxes["Base"][3]) + 20
    underline = next(
        y
        for y in range(top, bottom)
        if sum(pixels[y * width + x] < 128 for x in range(left, right))
        > 0.8 * (right - left)
    )

    # Measured: 72.5 pt with the fix, 80.5 pt without, the box's foot at 77.5.
    assert underline < 2 * boxes["sup"][3]


ODF = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
    ' xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
)


def write_ods_with_a_footer(path: pathlib.Path) -> None:
    """One sheet on a page with 2 cm margins and a header and footer 0.75 cm
    high, as LibreOffice writes one."""
    hf = '<style:header-footer-properties fo:min-height="0.75cm"/>'
    styles = (
        f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {ODF}'
        ' office:version="1.3"><office:automatic-styles>'
        '<style:page-layout style:name="pm1"><style:page-layout-properties'
        ' fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm"'
        ' fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/>'
        f"<style:header-style>{hf}</style:header-style>"
        f"<style:footer-style>{hf}</style:footer-style></style:page-layout>"
        "</office:automatic-styles><office:master-styles>"
        '<style:master-page style:name="Default" style:page-layout-name="pm1">'
        "<style:header><text:p>Head</text:p></style:header><style:footer>"
        "<text:p>Foot</text:p></style:footer></style:master-page>"
        "</office:master-styles></office:document-styles>"
    )
    content = (
        f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {ODF}'
        ' office:version="1.3"><office:automatic-styles><style:style'
        ' style:name="ta1" style:family="table" style:master-page-name="Default"/>'
        "</office:automatic-styles><office:body><office:spreadsheet>"
        '<table:table table:name="Sheet1" table:style-name="ta1"><table:table-row>'
        '<table:table-cell office:value-type="string"><text:p>A</text:p>'
        "</table:table-cell></table:table-row></table:table></office:spreadsheet>"
        "</office:body></office:document-content>"
    )
    entry = '<manifest:file-entry manifest:full-path="{}" manifest:media-type="{}"/>'
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest='
        '"urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
        + entry.format("/", "application/vnd.oasis.opendocument.spreadsheet")
        + entry.format("content.xml", "text/xml")
        + entry.format("styles.xml", "text/xml")
        + "</manifest:manifest>"
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        z.writestr("META-INF/manifest.xml", manifest)
        z.writestr("content.xml", content)
        z.writestr("styles.xml", styles)


def test_an_ods_keeps_its_margins_through_saves(tmp_path):
    """x2t wrote an .ods's page margins measured to the body, where ODF
    measures them to the header and footer and adds their height: each save
    added the height again, 2 cm becoming 2.75, then 4.75, then 7.5 (core 0202,
    ElixirOffice's fix)."""
    document = tmp_path / "sheet.ods"
    write_ods_with_a_footer(document)

    for n in range(2):
        tables = open_in(apps.TABLES, document, tmp_path / f"session{n}")
        export(tables, document, apps.TABLES.ids_by_ext["ods"], document)

    layout = re.search(
        r"<style:page-layout-properties[^>]*>",
        zipfile.ZipFile(document).read("styles.xml").decode("utf-8"),
    )
    assert layout is not None
    assert 'fo:margin-top="2cm"' in layout[0]
    assert 'fo:margin-bottom="2cm"' in layout[0]


def test_a_picture_bullet_is_kept_through_a_save(tmp_path):
    """A list whose bullet is a picture lost it on a save: the editor's binary
    format had no place for w:numPicBullet, and the .docx came back with a
    text bullet (ElixirOffice's #66, their fix, core 0203 and sdkjs 0011)."""
    document = tmp_path / "bullets.docx"
    write_pic_bullet_docx(payload_mod.resolve().root, document)
    words = open_in(apps.WORDS, document, tmp_path / "session")
    saved = tmp_path / "saved.docx"

    export(words, saved, apps.WORDS.ids_by_ext["docx"], None)

    with zipfile.ZipFile(saved) as z:
        numbering = z.read("word/numbering.xml").decode("utf-8")
        rels = z.read("word/_rels/numbering.xml.rels").decode("utf-8")
        pictures = [z.read(n) for n in z.namelist() if n.startswith("word/media/")]
    assert "<w:numPicBullet " in numbering
    assert "<w:lvlPicBulletId " in numbering
    assert "/image" in rels
    assert pictures, "the bullet's picture was not kept"


def red_pixels(pdf: pathlib.Path) -> int:
    """How many pixels of the PDF's first page, drawn at 72 dpi, are red."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        pytest.skip("no pdftoppm to draw the PDF's page")
    page = subprocess.run(
        [pdftoppm, "-r", "72", "-f", "1", "-l", "1", str(pdf)],
        capture_output=True,
        check=True,
    ).stdout
    # P6, width, height, maximum value, then three bytes a pixel.
    width, height = (int(v) for v in page.split(maxsplit=4)[1:3])
    pixels = page[-width * height * 3 :]
    return sum(
        1
        for i in range(0, len(pixels), 3)
        if pixels[i] > 180 and pixels[i + 1] < 60 and pixels[i + 2] < 60
    )


def test_a_picture_bullet_is_drawn(tmp_path):
    """The picture of a picture bullet was not drawn: the list showed a text
    bullet. Three items with a 12 pt red square each: about 430 red pixels at
    72 dpi."""
    document = tmp_path / "bullets.docx"
    write_pic_bullet_docx(payload_mod.resolve().root, document)
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "bullets.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    assert red_pixels(pdf) > 100


def test_a_missing_font_is_drawn_in_its_alternate_name(tmp_path):
    """Word draws a font that is not installed in the alternate name the
    document's font table gives it, w:altName, when that one is; the editor
    never saw the font table and drew an unknown font in Carlito (sdkjs 0012
    and core 0204, ElixirOffice's: Marianne, alternate Times New Roman)."""
    pdffonts = shutil.which("pdffonts")
    if pdffonts is None:
        pytest.skip("no pdffonts to list the PDF's fonts")
    blank = payload_mod.resolve().root / "empty" / apps.WORDS.blank
    document = tmp_path / "marianne.docx"
    body = (
        '<w:p><w:r><w:rPr><w:rFonts w:ascii="Marianne" w:hAnsi="Marianne"/></w:rPr>'
        "<w:t>Marianne, as Word draws it</w:t></w:r></w:p>"
    )
    entry = (
        '<w:font w:name="Marianne"><w:altName w:val="Liberation Serif"/>'
        '<w:family w:val="roman"/></w:font>'
    )
    with zipfile.ZipFile(blank) as src, zipfile.ZipFile(document, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == "word/document.xml":
                data = re.sub(
                    rb"<w:body>.*?(<w:sectPr)",
                    b"<w:body>" + body.encode() + rb"\1",
                    data,
                    flags=re.DOTALL,
                )
            elif item.filename == "word/fontTable.xml":
                data, n = re.subn(rb"(</w:fonts>)", entry.encode() + rb"\1", data)
                assert n == 1
            dst.writestr(item, data)
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "marianne.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    fonts = subprocess.run(
        [pdffonts, str(pdf)], capture_output=True, text=True, check=True
    ).stdout
    assert "Liberation Serif" in fonts
    assert "Carlito" not in fonts


def test_an_extended_charts_title_is_not_bold(tmp_path):
    """Word draws an extended chart's title (a sunburst, a waterfall) in the
    chart style's regular face when its runs say nothing: the PDF Word made of
    ElixirOffice's #76 embeds no bold font. The editor made every chart title
    bold, and only a classic chart's default title is (sdkjs 0013, after
    ElixirOffice 0.9.0)."""
    pdffonts = shutil.which("pdffonts")
    if pdffonts is None:
        pytest.skip("no pdffonts to list the PDF's fonts")
    document = tmp_path / "sunburst.docx"
    sunburst_docx(payload_mod.resolve().root, document, "Sales by region")
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "sunburst.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    fonts = subprocess.run(
        [pdffonts, str(pdf)], capture_output=True, text=True, check=True
    ).stdout.splitlines()[2:]
    assert fonts, "the title was not drawn at all"
    # A name can hold a space ("BAAAAA+Liberation Sans-Bold"): the line, not
    # its first word.
    assert not [f for f in fonts if "Bold" in f], fonts


# A positional tab to the centre of the line, then one to its right margin.
PTABS = (
    "<w:p><w:r><w:t>Left</w:t></w:r>"
    '<w:r><w:ptab w:relativeTo="margin" w:alignment="center" w:leader="none"/>'
    "<w:t>Mid</w:t></w:r>"
    '<w:r><w:ptab w:relativeTo="margin" w:alignment="right" w:leader="none"/>'
    "<w:t>End</w:t></w:r></w:p>"
)


def test_a_positional_tab_moves_the_text_to_its_place(tmp_path):
    """A positional tab (`w:ptab`) goes to the centre or the edge of the area
    between the margins, whatever the tab stops. x2t wrote nothing for one, so
    the editor drew "LeftMidEnd" as one word (core 0207 and sdkjs 0017, after
    ElixirOffice 0.7.3)."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("no pdftotext to read the PDF's text layer")
    document = with_body(tmp_path, PTABS)
    with zipfile.ZipFile(document) as z:
        xml = z.read("word/document.xml").decode()
    width = int(re.search(r'<w:pgSz w:w="(\d+)"', xml)[1]) / 20
    left = int(re.search(r'<w:pgMar [^>]*w:left="(\d+)"', xml)[1]) / 20
    right = width - int(re.search(r'<w:pgMar [^>]*w:right="(\d+)"', xml)[1]) / 20
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "ptab.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    html = subprocess.run(
        [pdftotext, "-bbox", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    found = {
        word: (float(x0), float(x1))
        for x0, x1, word in re.findall(
            r'<word xMin="([\d.]+)" yMin="[\d.]+" xMax="([\d.]+)"[^>]*>([^<]+)</word>',
            html,
        )
    }
    assert {"Left", "Mid", "End"} <= found.keys(), found
    mid = sum(found["Mid"]) / 2
    assert abs(mid - (left + right) / 2) < 2, (found, left, right)
    assert abs(found["End"][1] - right) < 2, (found, right)


# A SET field holding its last result, as Word writes one.
SET_FIELD = (
    '<w:p><w:r><w:t xml:space="preserve">Before </w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> SET year "2001" </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    "<w:r><w:t>2001</w:t></w:r>"
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    "<w:r><w:t>after</w:t></w:r></w:p>"
)


def test_a_set_fields_result_is_not_drawn(tmp_path):
    """A SET field sets a bookmark, and Word draws nothing for it, though the
    file holds its result. The editor drew the result (sdkjs 0018, after
    ElixirOffice 0.7.3)."""
    words = open_in(apps.WORDS, with_body(tmp_path, SET_FIELD), tmp_path / "session")
    pdf = tmp_path / "set.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    text = _read_text(pdf).decode()
    assert "Before" in text, text
    assert "2001" not in text, text


EMU_PER_TWIP = 635
RED, BLUE = (220, 0, 0), (0, 0, 220)


def anchored(rid: str, n: int, size: tuple[int, int], h: str, wrap: str) -> str:
    """A floating picture, `h` its horizontal position, the top of the
    paragraph its vertical one."""
    cx, cy = size
    return (
        '<w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0"'
        f' simplePos="0" relativeHeight="{n}" behindDoc="0" locked="0"'
        ' layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
        f"{h}"
        '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset>'
        f'</wp:positionV><wp:extent cx="{cx}" cy="{cy}"/>{wrap}'
        f'<wp:docPr id="{n}" name="p{n}"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{n}" name="p{n}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip xmlns:r="{RELATIONSHIPS}" r:embed="{rid}"/>'
        "<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/>'
        '</a:xfrm><a:prstGeom prst="rect"/></pic:spPr></pic:pic></a:graphicData>'
        "</a:graphic></wp:anchor></w:drawing></w:r>"
    )


def test_a_picture_follows_its_paragraph_into_the_next_column(tmp_path):
    """A picture placed against its paragraph's column goes in the column the
    paragraph's text is in. A picture filling the first column pushes the
    text into the second, and the editor placed the second picture against
    the empty piece the paragraph left in the first, under the one that
    fills it (ElixirOffice's #57, sdkjs 0020, after their 0.9.0)."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        pytest.skip("no pdftoppm to draw the PDF")
    column = (12240 - 2 * 1440 - 720) // 2  # two columns, 720 between
    filler = anchored(
        "rIdRed",
        1,
        (column * EMU_PER_TWIP, 12960 * EMU_PER_TWIP),
        '<wp:positionH relativeFrom="margin"><wp:posOffset>0</wp:posOffset>'
        "</wp:positionH>",
        '<wp:wrapSquare wrapText="bothSides"/>',
    )
    follower = anchored(
        "rIdBlue",
        2,
        (1440 * EMU_PER_TWIP, 1440 * EMU_PER_TWIP),
        '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset>'
        "</wp:positionH>",
        "<wp:wrapNone/>",
    )
    body = (
        f"<w:p>{filler}</w:p>"
        f"<w:p>{follower}<w:r><w:t>Come and worship</w:t></w:r></w:p>"
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"'
        ' w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:cols w:num="2" w:space="720"/></w:sectPr>'
    )
    document = with_body(tmp_path, "")
    with zipfile.ZipFile(document) as z:
        package = {n: z.read(n) for n in z.namelist()}
    xml = package["word/document.xml"].decode()
    package["word/document.xml"] = re.sub(
        r"<w:body>.*</w:body>",
        lambda _: f"<w:body>{body}</w:body>",
        xml,
        flags=re.DOTALL,
    ).encode()
    package["word/_rels/document.xml.rels"] = (
        package["word/_rels/document.xml.rels"]
        .decode()
        .replace(
            "</Relationships>",
            f'<Relationship Id="rIdRed" Type="{RELATIONSHIPS}/image"'
            ' Target="media/red.png"/>'
            f'<Relationship Id="rIdBlue" Type="{RELATIONSHIPS}/image"'
            ' Target="media/blue.png"/></Relationships>',
        )
        .encode()
    )
    types = package["[Content_Types].xml"].decode()
    if 'Extension="png"' not in types:
        types = types.replace(
            "</Types>", '<Default Extension="png" ContentType="image/png"/></Types>'
        )
    package["[Content_Types].xml"] = types.encode()
    package["word/media/red.png"] = solid_png(8, 8, RED)
    package["word/media/blue.png"] = solid_png(8, 8, BLUE)
    with zipfile.ZipFile(document, "w") as z:
        for name, data in package.items():
            z.writestr(name, data)
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "columns.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            "20",
            "-f",
            "1",
            "-l",
            "1",
            str(pdf),
            str(tmp_path / "page"),
        ],
        check=True,
    )
    (page,) = tmp_path.glob("page*.png")
    red = colour_box(str(page), RED)
    blue = colour_box(str(page), BLUE)
    assert red is not None, "the picture that fills the first column is missing"
    assert blue is not None, "the second picture is hidden"
    # In the second column, at its top, where the paragraph's text is.
    assert blue[0] > red[2], (red, blue)
    assert blue[1] == red[1], (red, blue)


def test_an_extended_chart_linked_as_a_chart_is_drawn(tmp_path):
    """Apache POI links an extended chart's part as a classic chart, with a
    picture to fall back on. Word draws the chart; x2t read the part as a
    classic chart, found none, and drew neither it nor the picture
    (ElixirOffice's #76, core 0209, after their 0.7.3 and 0.8.0)."""
    document = tmp_path / "linked.docx"
    linked_as_chart_docx(payload_mod.resolve().root, document, "Sales by region")
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "linked.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    assert "Sales by region" in _read_text(pdf).decode()


DAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


def test_an_autofit_column_has_room_for_the_first_line_indent(tmp_path):
    """Word sizes an autofit table's columns so that a word fits beside its
    paragraph's first-line indent, in a document of every compatibility mode;
    the editor counted the indent from Word 2013's mode only. A Word 2007
    calendar whose cells inherit an indent from Normal came out with "Su" over
    "n" and "2" over "3" (ElixirOffice's #66, their fix, sdkjs 0007)."""

    def row(words) -> str:
        return (
            "<w:tr>"
            + "".join(
                '<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>'
                '<w:p><w:pPr><w:ind w:firstLine="432"/></w:pPr>'
                f"<w:r><w:t>{word}</w:t></w:r></w:p></w:tc>"
                for word in words
            )
            + "</w:tr>"
        )

    numbers = [str(n) for n in range(23, 30)]
    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tblGrid>'
        + '<w:gridCol w:w="600"/>' * 7
        + "</w:tblGrid>"
        + row(DAYS)
        + row(numbers)
        + "</w:tbl><w:p/>"
    )
    document = tmp_path / "calendar.docx"
    blank = payload_mod.resolve().root / "empty" / apps.WORDS.blank
    with zipfile.ZipFile(blank) as src, zipfile.ZipFile(document, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == "word/document.xml":
                data = re.sub(
                    rb"<w:body>.*?(<w:sectPr)",
                    b"<w:body>" + table.encode() + rb"\1",
                    data,
                    flags=re.DOTALL,
                )
            elif item.filename == "word/settings.xml":
                data, n = re.subn(
                    rb'(w:name="compatibilityMode"[^>]*w:val=")15"', rb'\g<1>12"', data
                )
                assert n == 1
            dst.writestr(item, data)
    words = open_in(apps.WORDS, document, tmp_path / "session")
    pdf = tmp_path / "calendar.pdf"

    export(words, pdf, apps.WORDS.ids_by_ext["pdf"], None)

    text = word_boxes(pdf)
    drawn = re.findall(r"<word [^>]*>([^<]*)</word>", text)
    assert drawn == [*DAYS, *numbers]


def test_a_metafile_s_thin_lines_are_drawn_a_pixel_wide(live_payload, tmp_path):
    """The editor draws a WMF or EMF from the SVG x2t writes of it on opening,
    and x2t scaled a pen one logical unit wide with the drawing: a CAD drawing's
    lines came out a fiftieth of a pixel wide and the picture looked empty
    (ElixirOffice's #61). GDI draws no line thinner than a pixel, and core 0200
    does the same."""
    document = tmp_path / "drawing.docx"
    wmf_docx(live_payload, document, thin_pen_wmf())

    words = open_in(apps.WORDS, document, tmp_path / "session")

    [svg] = words.media.glob("*.svg")
    lines = re.findall(r"<(?:polyline|line|path)\b[^>]*>", svg.read_text())
    assert len(lines) == 2
    assert all('vector-effect="non-scaling-stroke"' in line for line in lines)


def test_a_saved_presentation_has_nothing_for_a_handout_master_it_lacks(tmp_path):
    """x2t wrote one's relationships and its theme, and not the master itself, in
    every presentation without one: Microsoft's code then refused a signature over
    them (core 0196), and LibreOffice's never minded."""
    saved = make_protected(apps.SLIDES, "pptx", tmp_path, password="")

    names = zipfile.ZipFile(saved).namelist()

    owners = {
        name: name.replace("_rels/", "").removesuffix(".rels")
        for name in names
        if name.endswith(".rels") and name != "_rels/.rels"
    }
    assert [rels for rels, owner in owners.items() if owner not in names] == []
    assert "ppt/theme/theme0.xml" not in names
