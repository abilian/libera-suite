"""A PDF saved with changes that comes back as the original is a failed save.

x2t saves a PDF by replaying the change log onto the original, and when the
replay fails it writes the original and exits 0: measured with its script
missing, with the changes not yet in the log, and on two PDFs certified
against changes (notes/plans/release-0.7.md, item B). Every edit was lost and
the save said nothing. x2t is stood in for here, so this runs without a
payload.
"""

from __future__ import annotations

import json
import re
import threading

import pytest
from support import ScriptedShell

from libera.host import apps, convert, hooks, saving
from libera.host.server import document
from libera.host.server.api import Request
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


def job_of_save(session, tmp_path, monkeypatch) -> str:
    """The job x2t was given for a save."""
    jobs = []

    def run(_session, job):
        text = convert.pathlib.Path(job).read_text(encoding="utf-8")
        jobs.append(text)
        target = re.search(r"<m_sFileTo>(.*?)</m_sFileTo>", text)
        assert target is not None
        convert.pathlib.Path(target.group(1)).write_bytes(ORIGINAL + b"% update\n")
        return convert.subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(convert, "run_x2t", run)
    convert.export(session, tmp_path / "saved.pdf", 513, None)
    (job,) = jobs
    return job


def test_a_pdf_with_a_password_is_saved_under_the_same(
    annotated, tmp_path, monkeypatch
):
    """Given the password to open with alone, x2t took the empty one to save
    under for a change, and rewrote the PDF without its encryption."""
    annotated.opened_with = annotated.password = "s<cret"

    job = job_of_save(annotated, tmp_path, monkeypatch)

    assert "<m_sPassword>s&lt;cret</m_sPassword>" in job
    assert "<m_sSavePassword>s&lt;cret</m_sSavePassword>" in job


def x2t_for_protect(monkeypatch, *, appends: bytes, rewrites: bytes) -> list[str]:
    """x2t for a change of password: the run with the change log writes
    `appends`, the one without `rewrites`. The jobs it was given, as text."""
    jobs: list[str] = []

    def run(_session, job):
        text = convert.pathlib.Path(job).read_text(encoding="utf-8")
        jobs.append(text)
        target = re.search(r"<m_sFileTo>(.*?)</m_sFileTo>", text)
        assert target is not None
        written = appends if "<m_bFromChanges>true" in text else rewrites
        convert.pathlib.Path(target.group(1)).write_bytes(written)
        return convert.subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(convert, "run_x2t", run)
    return jobs


APPENDED = ORIGINAL + b"% the comment, appended\n%%EOF\n"


@pytest.mark.parametrize(
    "case",
    [
        ("old", "new", ["<m_sPassword>old<", "<m_sSavePassword>new<"]),
        ("old", "", ["<m_sPassword>old<"]),
        ("", "new", ["<m_sSavePassword>new<"]),
    ],
    ids=["changed", "removed", "added"],
)
def test_file_protect_appends_the_changes_then_changes_the_password(
    annotated, tmp_path, monkeypatch, case
):
    """Editor.bin is the PDF as it was opened, under the password it had.
    The changes are appended under that one, where a failed replay shows;
    then x2t rewrites the whole file under the new one."""
    annotated.opened_with, annotated.password, given = case
    jobs = x2t_for_protect(monkeypatch, appends=APPENDED, rewrites=b"%PDF rewritten")

    convert.export(annotated, tmp_path / "saved.pdf", 513, None)

    appending, rewriting = jobs
    kept = annotated.opened_with
    if kept:
        assert f"<m_sPassword>{kept}<" in appending
        assert f"<m_sSavePassword>{kept}<" in appending
    else:
        assert "Password>" not in appending
    assert "<m_bFromChanges>false" in rewriting
    assert [g for g in given if g in rewriting] == given
    assert rewriting.count("Password>") == 2 * len(given)
    assert (tmp_path / "saved.pdf").read_bytes() == b"%PDF rewritten"


def test_a_change_of_password_whose_replay_failed_fails(
    annotated, tmp_path, monkeypatch
):
    """In one run, x2t rewrote the original under the new password, exit 0,
    and nothing could tell its changes were not in it."""
    annotated.opened_with, annotated.password = "old", "new"
    x2t_for_protect(monkeypatch, appends=ORIGINAL, rewrites=b"%PDF rewritten")

    with pytest.raises(convert.ConversionError, match="saved none of the changes"):
        convert.export(annotated, tmp_path / "saved.pdf", 513, None)


def test_a_change_of_password_x2t_did_not_make_fails(annotated, tmp_path, monkeypatch):
    """Given a password that does not open the PDF, x2t writes it as it was."""
    annotated.opened_with, annotated.password = "old", "new"
    x2t_for_protect(monkeypatch, appends=APPENDED, rewrites=APPENDED)

    with pytest.raises(convert.ConversionError, match="did not change the password"):
        convert.export(annotated, tmp_path / "saved.pdf", 513, None)


def test_a_pdf_without_one_names_none(annotated, tmp_path, monkeypatch):
    assert "Password" not in job_of_save(annotated, tmp_path, monkeypatch)


def test_the_password_is_in_no_repr(annotated):
    request = saving.SaveRequest.from_body({"fileType": 513, "password": "s<cret"})

    assert request.password == "s<cret"
    annotated.password = "s<cret"
    assert "s<cret" not in repr(request)
    assert "s<cret" not in repr(annotated)


ENCRYPTED = (
    b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"11 0 obj\n<< /Filter /Standard /V 5 /R 6 /O <00> /U <00> /P {p} >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R /Encrypt 11 0 R >>\n%%EOF\n"
)


@pytest.mark.parametrize(
    ("pdf", "may"),
    [
        (ORIGINAL, True),
        (ENCRYPTED.replace(b"{p}", b"-4"), True),
        (ENCRYPTED.replace(b"{p}", b"-3904"), False),
        (ENCRYPTED.replace(b"{p}", b"19"), False),
        (ORIGINAL + b"<< /Type /Sig /ByteRange [0 10 20 30] >>", False),
        (b"%PDF-1.7\ntrailer\n<< /Encrypt << /P -4 >> >>\n%%EOF\n", False),
        (ENCRYPTED.replace(b"/P {p} ", b""), False),
        (ENCRYPTED.replace(b"/P {p}", b"/P -4 /EncryptMetadata false"), False),
        (ENCRYPTED.replace(b"/P {p}", b"/P -4 /StmF /Identity"), False),
        (ENCRYPTED.replace(b"{p}", b"-4") + b"<< /Filter [/Crypt] >>", False),
        (ENCRYPTED.replace(b"{p}", b"-4") + b"<< /Encoding /Identity-H >>", True),
    ],
    ids=[
        *("plain", "all-permitted", "no-print", "pypdfs", "signed", "direct", "no-p"),
        *("clear-metadata", "identity", "crypt-filter", "identity-h-font"),
    ],
)
def test_protect_leaves_a_signature_and_an_authors_restrictions_alone(
    tmp_path, pdf, may
):
    """x2t's rewrite breaks a signature, gives the new password the owner's
    rights, every restriction lifted (measured 2026-10-31), and turns what the
    PDF left in clear into garbage."""
    path = tmp_path / "Editor.bin"
    path.write_bytes(pdf)

    assert convert.may_change_password(path) is may


def test_a_save_that_changed_the_password_reloads_the_window(annotated, monkeypatch):
    """Editor.bin is still the PDF under its old password, and edits a crash
    leaves would reopen on it and be saved under that one, or under none."""
    reloaded = threading.Event()
    monkeypatch.setattr(
        hooks, "shell", ScriptedShell(reload=lambda _session: reloaded.set())
    )
    monkeypatch.setattr(
        saving, "save_document", lambda *_: {"error": saving.SaveOutcome.SAVED}
    )
    annotated.opened_with, annotated.password = "old", "new"

    document.save(Request(annotated, json.dumps({"fileType": 513}).encode()))

    assert reloaded.wait(5)

    reloaded.clear()
    annotated.opened_with = "new"
    document.save(Request(annotated, json.dumps({"fileType": 513}).encode()))
    assert not reloaded.wait(0.5)
