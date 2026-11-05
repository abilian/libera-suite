"""Digital signatures through the host, with `libera-sign` run out of the
payload: listed, made, removed and described on the file on disk
(host/signing.py, core 0188 to 0190).

The keys are made here, a certificate issued by a test authority, so that the
signer and the issuer differ: the signer used to be shown as the issuer.
"""

from __future__ import annotations

import base64
import struct
import zipfile
import zlib

import pytest
from support import ScriptedShell
from support.keys import ISSUER, PASSPHRASE, SIGNER, make_pem, make_pkcs12
from support.protected import SECRET, make_protected, open_in

from libera.host import apps, hooks, saving, signing

GUID = "{5A1C0F4E-0000-4000-8000-0123456789AB}"


def png(rgb: tuple[int, int, int]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    rows = b"".join(b"\0" + bytes(rgb) * 40 for _ in range(20))
    header = struct.pack(">IIBBBBB", 40, 20, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def unpadded(b64: str) -> bytes:
    """The verifier hands a picture back without its base64 padding, which a
    data: URL does not need."""
    return base64.b64decode(b64 + "=" * (-len(b64) % 4))


def data_url(picture: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(picture).decode()


def with_relationships_of_no_part(document) -> None:
    """As every presentation saved here before core 0196 was: see test_convert."""
    with zipfile.ZipFile(document, "a") as package:
        package.writestr(
            "word/_rels/gone.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.openxml'
            'formats.org/officeDocument/2006/relationships/theme"'
            ' Target="theme/theme1.xml"/></Relationships>',
        )


@pytest.fixture
def session(tmp_path):
    document = make_protected(apps.WORDS, "docx", tmp_path / "made", password="")
    opened = open_in(apps.WORDS, document, tmp_path / "work")
    if not opened.layout.sign.is_file():
        pytest.skip("this payload has no libera-sign (core 0190)")
    return opened


def test_a_document_signed_here_is_listed_valid(session, tmp_path):
    key = make_pkcs12(tmp_path / "keys")

    chosen = signing.choose_certificate(session, key, None, PASSPHRASE)
    listed = signing.sign(session, chosen.id, "", ("", ""))

    assert (chosen.name, chosen.date) == (SIGNER, "5/3/2026 - 20/11/2036")
    (one,) = listed["data"]
    assert listed["count"] == 1
    assert (one["valid"], one["name"]) == (0, SIGNER)
    assert one["guid"] == "/_xmlsignatures/sig1.xml"
    assert one["certificate"]["issuer"] == ISSUER
    document = session.read_current_document()
    assert document is not None
    assert saving.is_signed(document)
    assert signing.list_signatures(session) == listed


def test_a_signature_line_keeps_its_pictures(session, tmp_path):
    key, cert = make_pem(tmp_path / "keys")
    valid, invalid = png((0, 0, 200)), png((200, 0, 0))

    chosen = signing.choose_certificate(session, key, cert, PASSPHRASE)
    listed = signing.sign(
        session, chosen.id, GUID, (data_url(valid), data_url(invalid))
    )

    (one,) = listed["data"]
    assert (one["guid"], one["valid"]) == (GUID, 0)
    assert unpadded(one["image_valid"]) == valid
    assert unpadded(one["image_invalid"]) == invalid


def test_a_wrong_passphrase_is_refused(session, tmp_path):
    key = make_pkcs12(tmp_path / "keys")

    with pytest.raises(signing.KeyRefusedError):
        signing.choose_certificate(session, key, None, "not it")

    assert session.certificate is None


def test_a_signature_is_removed_then_all(session, tmp_path):
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    signing.sign(session, chosen.id, GUID, ("", ""))
    signing.sign(session, chosen.id, "", ("", ""))

    left = signing.remove_signature(session, GUID)
    assert [s["guid"] for s in left["data"]] == ["/_xmlsignatures/sig2.xml"]

    assert signing.remove_signature(session, "") == signing.NO_SIGNATURES
    document = session.read_current_document()
    assert document is not None
    assert not saving.is_signed(document)


def test_a_signers_certificate_is_described(session, tmp_path):
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    signing.sign(session, chosen.id, "", ("", ""))

    found = signing.describe_signer(session, 0)

    assert found["certificate"]["name"] == SIGNER
    assert "Certificate:" in found["text"]
    assert ISSUER in found["text"]


def test_a_certificate_of_another_window_does_not_sign(session, tmp_path):
    signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )

    with pytest.raises(signing.SigningError, match="no such certificate"):
        signing.sign(session, "another-window", "", ("", ""))


def test_a_signed_document_is_not_saved_over_unsigned(session, tmp_path):
    """x2t's save rebuilds the package and writes no signature."""
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    signing.sign(session, chosen.id, "", ("", ""))
    document = session.read_current_document()
    assert document is not None
    signed = document.read_bytes()

    outcome = saving.save_document(session, saving.PLAIN_SAVE)

    assert outcome["error"] == saving.SaveOutcome.DECLINED
    assert document.read_bytes() == signed


@pytest.mark.parametrize("ext", ["odt"])
def test_an_opendocument_file_is_not_signable(tmp_path, ext):
    document = make_protected(apps.WORDS, ext, tmp_path / "made", password="")
    opened = open_in(apps.WORDS, document, tmp_path / "work")

    assert not signing.is_signable(opened)


def test_a_protected_document_is_not_signable(tmp_path):
    """The signer works on a zip, and an encrypted OOXML file is not one."""
    document = make_protected(apps.WORDS, "docx", tmp_path / "made")
    opened = open_in(apps.WORDS, document, tmp_path / "work")
    asked = opened.password_asked
    assert asked is not None
    asked.answer(SECRET)

    assert not signing.is_signable(opened)


@pytest.mark.parametrize("agree", [True, False])
def test_edits_not_in_the_file_are_saved_before_it_is_signed(
    session, tmp_path, monkeypatch, agree
):
    """After a reload or a crash recovery the editor shows edits the file
    does not have, and starts unmodified, so it asks nothing: signed as it
    was, the file's signature would cover what the user never saw."""
    asked = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(confirm_save_before_signing=lambda d: asked.append(d) or agree),
    )
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    session.mark_modified(True)
    document = session.read_current_document()
    assert document is not None

    if agree:
        signing.sign(session, chosen.id, "", ("", ""))
        assert saving.is_signed(document)
        assert not session.unsaved_marker.is_file()
    else:
        with pytest.raises(signing.SigningError, match="not saved"):
            signing.sign(session, chosen.id, "", ("", ""))
        assert not saving.is_signed(document)
    assert asked == [document]


def test_relationships_of_no_part_are_not_signed(session, tmp_path):
    """A signature over them is one Microsoft's code refuses, so one that goes on
    a file from before core 0196 has to leave them out (core 0197)."""
    document = session.read_current_document()
    with_relationships_of_no_part(document)
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )

    signing.sign(session, chosen.id, "", ("", ""))

    signature = zipfile.ZipFile(document).read("_xmlsignatures/sig1.xml")
    assert b"gone.xml" not in signature
    assert [s["valid"] for s in signing.list_signatures(session)["data"]] == [0]
