"""A protected document: x2t is given its password in a job, never on the
command line; exits 90 and 91 leave the editor the question; every save
passes the password on, since x2t given none writes the document
unprotected (notes/plans/release-0.8.md, measured 2026-10-30).

x2t is stood in for here; tests/b_integration/host/test_passwords.py runs it.
"""

from __future__ import annotations

import pathlib
import re
import zipfile

import pytest
from support import ScriptedShell

from libera.host import convert, hooks, opening, saving
from libera.host.session import Session

SECRET = "s<cr&t"


@pytest.fixture
def session(tmp_path) -> Session:
    document = tmp_path / "Report.docx"
    document.write_bytes(b"\xd0\xcf\x11\xe0 an encrypted package")
    work = tmp_path / "work"
    work.mkdir()
    return Session(payload=tmp_path, work=work, fonts=tmp_path, document=document)


def x2t_that(monkeypatch, password: str, jobs: list[str]) -> None:
    """x2t, as far as passwords go: 90 given none, 91 given another, and with
    this one a DOCY Editor.bin. Each job it is given is kept, as text."""

    def run(_session, *args):
        job = pathlib.Path(args[0])
        text = job.read_text(encoding="utf-8") if job.suffix == ".xml" else ""
        jobs.append(text or " ".join(args))
        given = re.search(r"<m_sPassword>(.*?)</m_sPassword>", text)
        if given is None:
            return convert.subprocess.CompletedProcess(
                args, convert.NO_PASSWORD, "", ""
            )
        if given.group(1) != convert.escape(password):
            return convert.subprocess.CompletedProcess(
                args, convert.WRONG_PASSWORD, "", ""
            )
        target = re.search(r"<m_sFileTo>(.*?)</m_sFileTo>", text)
        assert target is not None
        pathlib.Path(target.group(1)).write_bytes(b"DOCY;v5;")
        return convert.subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(convert, "run_x2t", run)


def test_no_password_is_a_question_not_a_failure(session, monkeypatch):
    jobs: list[str] = []
    x2t_that(monkeypatch, SECRET, jobs)

    with pytest.raises(convert.PasswordNeededError) as raised:
        convert.convert_to_editor_bin(session, session.document)

    assert raised.value.code == convert.NO_PASSWORD
    assert not session.editor_bin.exists()


def test_the_password_goes_in_a_job_deleted_after(session, monkeypatch):
    """Never on the command line, where any process listing shows it."""
    jobs: list[str] = []
    x2t_that(monkeypatch, SECRET, jobs)
    session.password = SECRET

    convert.convert_to_editor_bin(session, session.document)

    (job,) = jobs
    assert "<m_sPassword>s&lt;cr&amp;t</m_sPassword>" in job
    assert not (session.work / "open.xml").exists()
    assert session.editor_bin.read_bytes().startswith(b"DOCY")


def test_the_editor_is_asked_until_the_password_is_right(session, monkeypatch):
    x2t_that(monkeypatch, SECRET, [])
    done = []

    opening.convert_behind(
        session, session.document, pytest.fail, lambda: done.append(1)
    )
    assert session.converting is not None
    session.converting.join()

    asked = session.password_asked
    assert asked is not None
    assert asked.code == convert.NO_PASSWORD
    asked.answer("wrong")
    asked = session.password_asked
    assert asked is not None
    assert asked.code == convert.WRONG_PASSWORD
    assert not session.password
    asked.answer(SECRET)
    assert session.password_asked is None
    assert session.password == SECRET
    assert session.editor_bin.is_file()
    assert done == [1]


def test_an_answer_that_cannot_open_it_fails_and_says_so(session, monkeypatch):
    x2t_that(monkeypatch, SECRET, [])
    failures = []
    opening.ask_password(
        session, session.document, convert.NO_PASSWORD, failures.append, pytest.fail
    )
    asked = session.password_asked
    assert asked is not None

    def broken(_session, *args):
        return convert.subprocess.CompletedProcess(args, 0, "", "")  # and no Editor.bin

    monkeypatch.setattr(convert, "run_x2t", broken)
    with pytest.raises(convert.ConversionError):
        asked.answer(SECRET)

    assert len(failures) == 1
    assert session.password_asked is None
    assert not session.password


def make_odt(path: pathlib.Path, manifest: str) -> pathlib.Path:
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        package.writestr("META-INF/manifest.xml", manifest)
        package.writestr("content.xml", "encrypted bytes")
    return path


LIBREOFFICE_26 = (
    "<manifest:encryption-data><manifest:algorithm manifest:algorithm-name="
    '"http://www.w3.org/2009/xmlenc11#aes256-gcm"/><manifest:key-derivation'
    ' manifest:key-derivation-name="urn:org:documentfoundation:names:'
    'experimental:office:manifest:argon2id"/></manifest:encryption-data>'
)
LIBREOFFICE_7 = (
    "<manifest:encryption-data><manifest:algorithm manifest:algorithm-name="
    '"http://www.w3.org/2001/04/xmlenc#aes256-cbc"/><manifest:key-derivation'
    ' manifest:key-derivation-name="PBKDF2"/></manifest:encryption-data>'
)


def test_libreoffice_26s_encryption_is_refused_before_x2t(tmp_path):
    """x2t asks for its password, then exits 0 having written nothing."""
    with pytest.raises(convert.UnsupportedEncryptionError):
        convert.check_package(make_odt(tmp_path / "new.odt", LIBREOFFICE_26))


def test_the_encryption_x2t_reads_goes_to_x2t(tmp_path):
    convert.check_package(make_odt(tmp_path / "old.odt", LIBREOFFICE_7))


def job_of_save(session: Session, tmp_path, monkeypatch, target: str) -> str:
    jobs = []

    def run(_session, job):
        text = pathlib.Path(job).read_text(encoding="utf-8")
        jobs.append(text)
        out = re.search(r"<m_sFileTo>(.*?)</m_sFileTo>", text)
        assert out is not None
        pathlib.Path(out.group(1)).write_bytes(b"saved")
        return convert.subprocess.CompletedProcess([], 0, "", "")

    session.doc.mkdir(parents=True)
    session.editor_bin.write_bytes(b"DOCY;v5;")
    monkeypatch.setattr(convert, "run_x2t", run)
    convert.export(session, tmp_path / target, 65, None)
    (job,) = jobs
    return job


def test_a_protected_document_is_saved_under_its_password(
    session, tmp_path, monkeypatch
):
    """x2t given no password writes it unprotected, exit 0."""
    session.password = SECRET

    job = job_of_save(session, tmp_path, monkeypatch, "saved.docx")

    assert "<m_sSavePassword>s&lt;cr&amp;t</m_sSavePassword>" in job
    # Editor.bin is decrypted: nothing to open it with.
    assert "<m_sPassword>" not in job


def test_a_document_without_one_is_saved_without(session, tmp_path, monkeypatch):
    assert "Password" not in job_of_save(session, tmp_path, monkeypatch, "saved.docx")


def test_a_save_that_does_not_take_keeps_the_files_password(
    session, tmp_path, monkeypatch
):
    """File > Protect saves at once. Cancelled or failed, the password it
    carried never reached the file, and the next save, a print or the one on
    close would have written the document under it."""
    session.password = SECRET
    monkeypatch.setattr(saving, "_export", lambda *_: None)

    outcome = saving.save_document(session, saving.SaveRequest(password="new"))

    assert outcome["error"] == saving.SaveOutcome.FAILED
    assert session.password == SECRET


def test_a_save_that_takes_gives_the_file_its_new_password(
    session, tmp_path, monkeypatch
):
    session.password = SECRET
    monkeypatch.setattr(saving, "_export", lambda *_: tmp_path / "saved.docx")
    monkeypatch.setattr(session, "mark_modified", lambda _m: None)

    outcome = saving.save_document(session, saving.SaveRequest(password=""))

    assert outcome["error"] == saving.SaveOutcome.SAVED
    assert not session.password


def save_as(
    session, monkeypatch, target: pathlib.Path, *, confirm: bool, password=SECRET
) -> tuple:
    """A Save As to `target`, carrying the editor's `password` and answering the
    question of the password with `confirm`: the outcome, the questions asked
    and the files exported."""
    asked: list[pathlib.Path] = []
    exported: list[pathlib.Path] = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            choose_save_path=lambda *_: str(target),
            confirm_unprotected=lambda document: asked.append(document) or confirm,
        ),
    )

    def export(_session, plan, _open_file):
        exported.append(plan.target)
        session.write_current_document(plan.target)
        return plan.target

    monkeypatch.setattr(saving, "_export", export)
    monkeypatch.setattr(session, "mark_modified", lambda _m: None)
    outcome = saving.save_document(
        session, saving.SaveRequest(save_as=True, password=password)
    )
    return outcome, asked, exported


def test_a_save_as_that_drops_the_password_asks_first(session, monkeypatch, tmp_path):
    """x2t writes a .txt in clear, exit 0, and says nothing."""
    session.password = SECRET

    outcome, asked, exported = save_as(
        session, monkeypatch, tmp_path / "Report.txt", confirm=False
    )

    assert asked == [tmp_path / "Report.txt"]
    assert outcome["error"] == saving.SaveOutcome.DECLINED
    assert exported == []
    assert session.password == SECRET


def test_saved_without_its_password_the_document_has_none(
    session, monkeypatch, tmp_path
):
    """The window now has the .txt open. Kept, the password went to the next
    Save As, and a .docx got one the user had been told was dropped."""
    session.password = SECRET

    outcome, asked, exported = save_as(
        session, monkeypatch, tmp_path / "Report.txt", confirm=True
    )

    assert outcome["error"] == saving.SaveOutcome.SAVED
    assert asked
    assert exported == [tmp_path / "Report.txt"]
    assert not session.password


@pytest.mark.parametrize("name", ["Copy.docx", "Copy.odt", "Copy.pdf"])
def test_a_save_as_that_keeps_the_password_does_not_ask(
    session, monkeypatch, tmp_path, name
):
    session.password = SECRET

    outcome, asked, _ = save_as(session, monkeypatch, tmp_path / name, confirm=False)

    assert outcome["error"] == saving.SaveOutcome.SAVED
    assert asked == []
    assert session.password == SECRET


def test_a_document_without_a_password_is_saved_as_text_unasked(
    session, monkeypatch, tmp_path
):
    outcome, asked, _ = save_as(
        session, monkeypatch, tmp_path / "Report.txt", confirm=False, password=""
    )

    assert outcome["error"] == saving.SaveOutcome.SAVED
    assert asked == []


def test_a_name_without_a_suffix_is_judged_by_the_format_written(
    session, monkeypatch, tmp_path
):
    """Where the toolkit takes no format list (GTK, Windows), the name typed
    decides, and one it does not know is written in the format asked for:
    an encrypted .docx, with no question."""
    session.password = SECRET

    outcome, asked, _ = save_as(
        session, monkeypatch, tmp_path / "Report 2026.10.31", confirm=False
    )

    assert outcome["error"] == saving.SaveOutcome.SAVED
    assert asked == []
    assert session.password == SECRET


def test_a_password_set_on_a_text_file_asks_before_it_is_lost(
    session, monkeypatch, tmp_path
):
    """The editor reads whether to offer File > Protect once, as it loads: a
    document saved as text still offers it, and its save is a plain one."""
    notes = tmp_path / "notes.txt"
    session.write_current_document(notes)
    asked: list[pathlib.Path] = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(confirm_unprotected=lambda d: asked.append(d) or False),
    )
    monkeypatch.setattr(saving, "_export", lambda *_: pytest.fail("exported"))

    outcome = saving.save_document(session, saving.SaveRequest(password=SECRET))

    assert asked == [notes]
    assert outcome["error"] == saving.SaveOutcome.DECLINED
    assert not session.password


def test_with_no_one_to_ask_a_protected_document_is_not_saved_as_text(
    session, monkeypatch
):
    session.password = SECRET
    monkeypatch.setattr(saving, "_export", lambda *_: pytest.fail("exported"))
    txt = next(i for i, (ext, _) in saving.apps.WORDS.formats.items() if ext == "txt")

    outcome = saving.save_document(
        session, saving.SaveRequest(file_type=txt, save_as=True)
    )

    assert outcome["error"] == saving.SaveOutcome.DECLINED
    assert session.password == SECRET
