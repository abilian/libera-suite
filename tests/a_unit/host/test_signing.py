"""Signatures without the program: how the host runs libera-sign, and what it
lets the page name. libera-sign is stood in for here;
tests/b_integration/host/test_signatures.py runs it."""

from __future__ import annotations

import json
import zipfile

import pytest

from libera.host import convert, saving, signing
from libera.host.server import signatures
from libera.host.server.api import Refused, Request
from libera.host.session import Session

PASSPHRASE = "zqx <pass> & 4471"


@pytest.fixture
def session(tmp_path) -> Session:
    document = tmp_path / "Report.docx"
    with zipfile.ZipFile(document, "w") as package:
        package.writestr("word/document.xml", "<w:document/>")
    work = tmp_path / "work"
    work.mkdir()
    found = Session(payload=tmp_path, work=work, fonts=tmp_path, document=document)
    found.write_current_document(document)
    found.layout.sign.parent.mkdir(parents=True, exist_ok=True)
    found.layout.sign.write_text("stood in for")
    return found


def libera_sign_that(monkeypatch, answer: dict, calls: list, status: int = 0) -> None:
    """libera-sign as far as the host can tell: `answer` on standard output,
    each call kept as (argv, standard input)."""

    def run(argv, _env, stdin=None):
        calls.append((argv, stdin))
        return convert.subprocess.CompletedProcess(argv, status, json.dumps(answer), "")

    monkeypatch.setattr(signing.convert, "run_watched", run)


def test_the_passphrase_goes_on_standard_input(session, tmp_path, monkeypatch):
    """On the command line, any process listing shows it."""
    calls: list = []
    libera_sign_that(monkeypatch, {"name": "Zoé", "date": "1/1/2026 - 1/1/2027"}, calls)
    key = tmp_path / "signer.p12"

    chosen = signing.choose_certificate(session, key, None, PASSPHRASE)

    ((argv, given),) = calls
    assert argv[1:] == ["info", str(key), ""]
    assert given == PASSPHRASE + "\n"
    assert PASSPHRASE not in repr(chosen)
    assert PASSPHRASE not in repr(session)
    assert chosen.for_editor() == {"id": chosen.id, "name": "Zoé", "date": chosen.date}


def test_a_refused_key_is_said_so(session, tmp_path, monkeypatch):
    libera_sign_that(monkeypatch, {}, [], status=signing.NO_KEY)

    with pytest.raises(signing.KeyRefusedError):
        signing.choose_certificate(session, tmp_path / "k.p12", None, "wrong")


@pytest.mark.parametrize("field", ["key", "cert"])
def test_the_page_names_only_files_the_user_chose(session, tmp_path, field):
    """Else a page could have the host read any file as a key."""
    chosen = tmp_path / "signer.p12"
    session.offered.add(chosen)
    body = {"key": str(chosen), "cert": "", "passphrase": ""}
    body[field] = "/etc/passwd"

    with pytest.raises(Refused) as refused:
        signatures.choose_certificate(
            Request(session, json.dumps(body).encode(), {"session": [session.id]})
        )

    assert refused.value.status == 403


def test_a_picture_for_the_sign_dialog_is_one_the_user_chose(session, tmp_path):
    picture = tmp_path / "me.png"
    picture.write_bytes(b"\x89PNG not really")

    asked = {"path": [str(picture)], "session": [session.id]}
    with pytest.raises(Refused):
        signatures.serve_image(Request(session, query=asked))

    session.offered.add(picture)
    served = signatures.serve_image(Request(session, query=asked))
    assert served.body.startswith(b"data:image/png;base64,")


def test_a_signature_picture_must_be_a_png_data_url(session, monkeypatch):
    calls: list = []
    libera_sign_that(monkeypatch, {"name": "Zoé", "date": ""}, calls)
    chosen = signing.choose_certificate(session, session.work / "k.p12", None, "")

    with pytest.raises(signing.SigningError, match="PNG"):
        signing.sign(session, chosen.id, "", ("file:///etc/passwd", ""))


def test_a_signed_file_is_recognised_without_the_program(tmp_path):
    signed = tmp_path / "signed.docx"
    with zipfile.ZipFile(signed, "w") as package:
        package.writestr("_xmlsignatures/sig1.xml", "<Signature/>")
    plain = tmp_path / "plain.docx"
    with zipfile.ZipFile(plain, "w") as package:
        package.writestr("_xmlsignatures/origin.sigs", "")

    assert saving.is_signed(signed)
    assert not saving.is_signed(plain)
    assert not saving.is_signed(tmp_path / "missing.docx")


def test_a_document_with_a_password_offers_no_signing(session):
    assert signing.is_signable(session)
    session.password = "s3cret"
    assert not signing.is_signable(session)


@pytest.mark.parametrize(
    "endpoint",
    [signatures.serve_certificate, signatures.sign, signatures.remove_signature],
)
def test_a_request_that_names_no_window_is_refused(session, endpoint):
    """It would go to the first window, whose certificate another window's
    page could then sign with."""
    with pytest.raises(Refused) as refused:
        endpoint(Request(session, b"{}"))

    assert refused.value.status == 400


def test_neither_a_new_document_nor_one_open_elsewhere_is_signable(session):
    """File > New's copy of a blank is in the state folder, and x2t saves it
    where the user chooses, with no signature; a locked file is someone
    else's."""
    assert signing.is_signable(session)
    session.locked_by = {"name": "Someone", "since": "today"}
    assert not signing.is_signable(session)
    session.locked_by = None
    untitled = session.scratch / "Untitled.docx"
    untitled.parent.mkdir(parents=True, exist_ok=True)
    untitled.write_bytes((session.read_current_document() or untitled).read_bytes())
    session.write_current_document(untitled)
    assert not signing.is_signable(session)


def test_an_encrypted_file_is_not_signable_before_its_password(session):
    """The editor asks whether to offer signatures as it loads, before the
    password is typed: the file itself says, an encrypted OOXML being no zip."""
    document = session.read_current_document()
    assert document is not None
    document.write_bytes(b"\xd0\xcf\x11\xe0 an encrypted package")

    assert not signing.is_signable(session)


def test_removing_from_a_file_with_no_signature_answers_none(session, monkeypatch):
    """After a Save As the editor may show the old file's signatures, and its
    Edit anyway removes them all."""
    monkeypatch.setattr(signing, "_run", lambda *_a, **_k: pytest.fail("ran"))

    assert signing.remove_signature(session, "") == signing.NO_SIGNATURES
