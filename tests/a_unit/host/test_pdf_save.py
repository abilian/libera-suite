"""A PDF saved with changes that comes back as the original is a failed save.

x2t saves a PDF by replaying the change log onto the original, and when the
replay fails it writes the original and exits 0: measured with its script
missing, with the changes not yet in the log, and on two PDFs certified
against changes (notes/plans/release-0.7.md, item B). Every edit was lost and
the save said nothing. x2t is stood in for here, so this runs without a
payload.
"""

from __future__ import annotations

import re

import pytest

from libera.host import apps, convert
from libera.host.session import Session, configure

ORIGINAL = b"%PDF-1.4\n% the original\n%%EOF\n"


@pytest.fixture
def opened(tmp_path) -> Session:
    """A PDF open in the PDF editor, nothing edited."""
    document = tmp_path / "report.pdf"
    document.write_bytes(ORIGINAL)
    found = Session(
        payload=tmp_path / "payload",
        work=tmp_path / "sessions" / "0",
        fonts=tmp_path / "fonts",
        document=document,
        app=apps.PDFS,
    )
    configure(found)
    convert.convert_to_editor_bin(found, document)
    return found


@pytest.fixture
def annotated(opened) -> Session:
    """The same, with one edit in its log."""
    opened.change_log.record("a comment", None, 1)
    return opened


def make_x2t_write(monkeypatch, content: bytes) -> None:
    """x2t's job-file form: m_sFileTo is what it writes."""

    def run(_session, job):
        text = convert.pathlib.Path(job).read_text(encoding="utf-8")
        target = re.search(r"<m_sFileTo>(.*?)</m_sFileTo>", text)
        assert target is not None
        convert.pathlib.Path(target.group(1)).write_bytes(content)
        return convert.subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(convert, "run_x2t", run)


def test_a_pdf_opens_as_itself(opened):
    """The PDF editor reads the PDF: no conversion, the bytes as they were."""
    assert opened.editor_bin.read_bytes() == ORIGINAL


def test_a_save_that_writes_the_original_fails(annotated, tmp_path, monkeypatch):
    make_x2t_write(monkeypatch, ORIGINAL)

    with pytest.raises(convert.ConversionError, match="saved none of the changes"):
        convert.export(annotated, tmp_path / "saved.pdf", 513, None)


def test_a_certified_pdf_says_so(opened, tmp_path, monkeypatch):
    """Two of LibreOffice's test PDFs are certified (/DocMDP), and x2t saved
    neither one's comment. "Saved none of the changes" alone does not say
    why; the signature is the likely reason, so the message names it."""
    certified = b"%PDF-1.7\n<< /Perms << /DocMDP 5 0 R >> >>\n%%EOF\n"
    opened.editor_bin.write_bytes(certified)
    opened.change_log.record("a comment", None, 1)
    make_x2t_write(monkeypatch, certified)

    with pytest.raises(convert.ConversionError, match="certification signature"):
        convert.export(opened, tmp_path / "saved.pdf", 513, None)


def test_a_save_that_rewrites_the_original_fails(annotated, tmp_path, monkeypatch):
    """Every save measured appended to the original's bytes, page operations
    included; one that did not may have lost what it rewrote. ElixirOffice
    refuses it too."""
    make_x2t_write(monkeypatch, b"%PDF-1.4\n% another file, the comment in it\n%%EOF\n")

    with pytest.raises(convert.ConversionError, match="rewrote"):
        convert.export(annotated, tmp_path / "saved.pdf", 513, None)


def test_a_save_with_the_changes_appended_succeeds(annotated, tmp_path, monkeypatch):
    saved = ORIGINAL + b"% an incremental update\n%%EOF\n"
    make_x2t_write(monkeypatch, saved)

    convert.export(annotated, tmp_path / "saved.pdf", 513, None)

    assert (tmp_path / "saved.pdf").read_bytes() == saved


def test_a_pdf_saved_unchanged_may_be_the_original(opened, tmp_path, monkeypatch):
    """Nothing edited, nothing to lose: the original is the right answer."""
    make_x2t_write(monkeypatch, ORIGINAL)

    convert.export(opened, tmp_path / "saved.pdf", 513, None)

    assert (tmp_path / "saved.pdf").read_bytes() == ORIGINAL
