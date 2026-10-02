"""x2t, run out of the payload for real.

The unit tests can check what job file we write; only this can check that x2t
accepts it. Every conversion here starts from the Editor.bin the `opened`
fixture produced, which is the same thing a save does.
"""

from __future__ import annotations

import csv
import io
import zipfile
from typing import TYPE_CHECKING

import pytest
from support import ScriptedShell

from libera import payload as payload_mod
from libera.host import apps, hooks, opening, session as sessions
from libera.host.convert import export, find_misread_rows
from libera.host.saving import save_document
from libera.host.session import Session

if TYPE_CHECKING:
    import pathlib


def test_opening_a_document_produces_an_editor_bin(opened: Session):
    assert opened.editor_bin.stat().st_size > 0


OFFERED = [
    (app, ext) for app in apps.ALL if app.editable for _, ext in app.save_formats
]


@pytest.mark.parametrize(
    ("app", "ext"), OFFERED, ids=[f"{a.name}-{e}" for a, e in OFFERED]
)
def test_every_format_every_editor_offers_is_one_x2t_writes(
    open_blank, tmp_path: pathlib.Path, app: apps.App, ext: str
):
    """The Save As popup promises these, for each editor in turn.

    x2t refuses a fair few ids sitting right beside the ones it accepts -- xls
    (258), ppt (130), odg (140), every legacy binary and flat-XML format -- so
    the only way to know which is which is to ask it.
    """
    blank = open_blank(app)
    out = tmp_path / f"out.{ext}"
    assert export(blank, out, app.ids_by_ext[ext], None), (
        f"x2t would not write .{ext} for {app.name}"
    )
    assert out.stat().st_size > 0


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_no_editor_offers_a_format_its_converter_does_not_know(app: apps.App):
    assert {ext for _, ext in app.save_formats} <= set(app.ids_by_ext)


def test_plain_save_overwrites_the_document_that_is_open(opened: Session):
    """fileType 0 means "whatever it already was", and no dialog is involved."""
    before = opened.document.stat().st_mtime_ns
    result = save_document(opened, {"fileType": 0})

    assert result == {"error": 0, "path": str(opened.document)}
    assert opened.document.stat().st_mtime_ns != before
    # Saved means nothing left to recover.
    assert not opened.unsaved_marker.is_file()


def test_save_as_follows_the_extension_the_user_typed(
    opened: Session, tmp_path: pathlib.Path, monkeypatch
):
    """The chooser's suffix wins over the format the editor asked for.

    The popup and the typed name can disagree; the name is what the user sees,
    so it decides, and the format follows it.
    """
    chosen = tmp_path / "elsewhere.odt"
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(choose_save_path=lambda _name, _formats, _start_in: str(chosen)),
    )

    result = save_document(opened, {"fileType": 65, "params": "saveas=true"})

    assert result == {"error": 0, "path": str(chosen)}
    assert chosen.read_bytes()[:2] == b"PK"  # an ODF package, not a docx
    # Save As moves the session onto the new file; a plain Save now goes there.
    assert opened.current_file.read_text() == str(chosen)


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
    monkeypatch.setattr("libera.host.convert.export", lambda *_: False)

    result = save_document(opened, {"fileType": 65, "params": "saveas=true"})

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

    assert save_document(opened, {"fileType": 65, "params": "saveas=true"}) == {
        "error": 1
    }
    assert opened.document.stat().st_mtime_ns == before


def test_printing_makes_a_pdf_beside_the_session_not_over_the_document(
    opened: Session, monkeypatch
):
    """Print is a PDF save with no destination: it must not touch the docx."""
    monkeypatch.setattr("libera.host.desktop.open_externally", lambda _p: True)
    before = opened.document.stat().st_mtime_ns

    result = save_document(opened, {"fileType": 513, "isPrint": True})

    assert result["error"] == 0
    assert result["path"].endswith(f"{opened.document.stem}.pdf")
    assert opened.document.stat().st_mtime_ns == before


def test_a_print_nothing_opens_is_a_failed_print(opened: Session, monkeypatch):
    """The PDF is made, but nothing will show it: that is not a print."""
    monkeypatch.setattr("libera.host.desktop.open_externally", lambda _p: False)

    assert save_document(opened, {"fileType": 513, "isPrint": True})["error"] == 2


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
    assert save_document(viewer, {"fileType": 0}) == {"error": 1}


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
        assert save_document(table, {"fileType": 0}) == {
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

    assert save_document(table, {"fileType": 0, "params": "saveas=true"})["error"] == 0
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
    assert export(blank, document, app.ids_by_ext[ext], None)
    reopened = open_in(app, document, tmp_path / "reopened")
    before = document.stat().st_mtime_ns

    assert save_document(reopened, {"fileType": 0}) == {
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

    assert save_document(opened, {"fileType": 0}, may_ask=False) == {"error": 2}


def test_text_x2t_would_garble_does_not_replace_the_document(tmp_path):
    """A character outside the BMP, and x2t writes one byte per character.

    Its converter to UTF-8 sizes its buffer one unit per character, an emoji
    needs two, and the fallback writes "é" as the single byte E9 throughout the
    file -- exiting 0. The save has to fail rather than write that over a CSV.
    """
    text = "Nom,Description\nCleed,🎯 Échange sécurisé\n".encode()
    document = tmp_path / "list.csv"
    document.write_bytes(text)
    table = open_in(apps.TABLES, document, tmp_path / "session")

    assert save_document(table, {"fileType": 0})["error"] == 2
    assert document.read_bytes() == text


def test_a_text_file_opens_past_an_emoji(tmp_path):
    """Without a byte-order mark, x2t's reader stopped at the first emoji."""
    document = tmp_path / "notes.txt"
    document.write_text("avant\n🎯 cible\naprès\n", encoding="utf-8")
    notes = open_in(apps.WORDS, document, tmp_path / "session")
    docx = tmp_path / "out.docx"

    assert export(notes, docx, apps.WORDS.ids_by_ext["docx"], None)
    assert "après" in zipfile.ZipFile(docx).read("word/document.xml").decode()


def test_markdown_opens_and_saves(tmp_path):
    """x2t refused every .md without an encoding (rc 88)."""
    document = tmp_path / "notes.md"
    document.write_text("Un *mot* et cœur 🎯\n", encoding="utf-8")
    notes = open_in(apps.WORDS, document, tmp_path / "session")

    assert save_document(notes, {"fileType": 0}) == {"error": 0, "path": str(document)}
    assert "cœur 🎯" in document.read_text(encoding="utf-8")


# --- x2t's CSV reader skips a character every 500,000 ----------------------
#
# CSVReader drops the text it has read once it passes 500,000 characters and
# never looks at the first character after the cut. Patch 0029 in
# build/patches/core fixes it, for payload 0.4; until then the host works out
# which rows that damages and says so when the file opens. These two tests turn
# over together when the payload does: the first stops matching, the second
# starts passing, and both mean the warning in opening.py can go.

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
    assert export(table, out, apps.TABLES.ids_by_ext["csv"], document)
    wanted, got = read_rows(document), read_rows(out)
    for number, row in enumerate(wanted, 1):
        if number > len(got) or got[number - 1] != row:
            return [number]
    return [] if len(got) == len(wanted) else [len(wanted) + 1]


@pytest.mark.parametrize("case", CUTS)
def test_the_rows_the_host_warns_about_are_the_rows_x2t_damages(tmp_path, case):
    """find_misread_rows is a model of x2t's loop, so it is checked against x2t."""
    document = tmp_path / "list.csv"
    document.write_text(CUTS[case], encoding="utf-8")

    assert find_misread_rows(document) == rows_x2t_changes(document, tmp_path / "s")


@pytest.mark.xfail(
    strict=True,
    reason="x2t skips the character after each 500,000-character cut: "
    "patch 0029, payload 0.4",
)
@pytest.mark.parametrize("case", [c for c in CUTS if c != "a letter"])
def test_x2t_reads_every_row_of_a_large_csv(tmp_path, case):
    document = tmp_path / "list.csv"
    document.write_text(CUTS[case], encoding="utf-8")

    assert rows_x2t_changes(document, tmp_path / "s") == []
