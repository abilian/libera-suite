"""`libera --convert`, through x2t, on the payload's own blanks.

Each result is checked by its bytes: x2t exits 0 having written the wrong
thing often enough here.
"""

from __future__ import annotations

import shutil
import zipfile

import pytest

from libera import cli
from libera.host import apps, convert


@pytest.fixture
def docs(tmp_path, monkeypatch, live_payload):
    """A Words document twice, and a presentation, in the current directory."""
    monkeypatch.chdir(tmp_path)
    for name, app in (("a", apps.WORDS), ("b", apps.WORDS), ("deck", apps.SLIDES)):
        shutil.copyfile(
            live_payload / "empty" / app.blank, tmp_path / f"{name}.{app.ext}"
        )
    return tmp_path


def test_each_document_is_written_beside_it_over_what_was_there(docs):
    (docs / "a.pdf").write_bytes(b"old")
    assert cli.main(["--convert", "a.docx", "b.docx", "-t", "pdf"]) == 0
    for name in ("a.pdf", "b.pdf"):
        assert (docs / name).read_bytes().startswith(b"%PDF-")


def test_the_format_comes_from_the_output_name(docs):
    assert cli.main(["--convert", "deck.pptx", "-o", "talk.odp"]) == 0
    with zipfile.ZipFile(docs / "talk.odp") as odp:
        mimetype = odp.read("mimetype")
    assert mimetype == b"application/vnd.oasis.opendocument.presentation"


def test_outdir_is_made_and_written_into(docs):
    assert cli.main(["--convert", "a.docx", "-t", "odt", "--outdir", "o/x"]) == 0
    assert zipfile.is_zipfile(docs / "o" / "x" / "a.odt")
    assert not (docs / "a.odt").exists()


def test_dash_writes_to_standard_output(docs, capsysbinary):
    assert cli.main(["--convert", "a.docx", "-o", "-", "-t", "pdf"]) == 0
    assert capsysbinary.readouterr().out.startswith(b"%PDF-")
    assert not list(docs.glob("*.pdf"))


def test_a_document_that_fails_does_not_stop_the_others(docs, capsys, monkeypatch):
    """x2t reads anything it cannot recognise as plain text, so a broken file
    converts; the failure is made here instead."""
    real = convert.convert_to_editor_bin

    def fail_on_a(session, src):
        if src.name == "a.docx":
            msg = "x2t could not convert a.docx (exit status 89)"
            raise convert.ConversionError(msg)
        real(session, src)

    monkeypatch.setattr(convert, "convert_to_editor_bin", fail_on_a)
    assert cli.main(["--convert", "a.docx", "b.docx", "-t", "pdf"]) == 1
    assert "a.docx: x2t could not convert" in capsys.readouterr().err
    assert not (docs / "a.pdf").exists()
    assert (docs / "b.pdf").read_bytes().startswith(b"%PDF-")
