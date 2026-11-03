"""Digital signatures judged against LibreOffice's: a signature made here must
be one LibreOffice accepts, one LibreOffice made must be valid here, and on a
signed file from elsewhere our verdict must be LibreOffice's.

LibreOffice runs in a container (`support.libreoffice`), so these skip where
no container engine is running. Word is the program that matters most and is
not here; LibreOffice is the second implementation that is. The first run
against it, on 2026-11-03, found LibreOffice refusing every signature made
here on a document Words or Slides writes, and our verifier refusing every
signature LibreOffice makes and four of Office's (core 0191 to 0193).

LibreOffice is not right everywhere. Its libxmlsec 1.2 digests the text
between the entries of a .rels part, which the standard leaves out: it
refuses a signature over such a part made to the standard, and signs its own
in a form only it reproduces. The one file of the corpus that this affects,
office2007prettyPrintedRels.docx, is refused here too, for another reason:
its signer wrote the SHA-1 DigestInfo without its NULL parameter, which
OpenSSL refuses. So the two agree there, each for its own reason.
"""

from __future__ import annotations

import pathlib
import shutil
import zipfile

import pytest
from support import libreoffice
from support.keys import PASSPHRASE, SIGNER, make_pkcs12
from support.protected import SENTENCE, make_protected, open_in

from libera.host import apps, signing

DATA = pathlib.Path(__file__).parent / "data" / "signed"
KINDS = [(apps.WORDS, "docx"), (apps.TABLES, "xlsx"), (apps.SLIDES, "pptx")]
KIND_IDS = ["docx", "xlsx", "pptx"]


@pytest.fixture(scope="module")
def office(tmp_path_factory) -> libreoffice.LibreOffice:
    return libreoffice.reference(tmp_path_factory.mktemp("libreoffice"))


def opened(app: apps.App, document: pathlib.Path, tmp_path: pathlib.Path):
    session = open_in(app, document, tmp_path / "work")
    if not session.layout.sign.is_file():
        pytest.skip("this payload has no libera-sign (core 0190)")
    return session


@pytest.mark.parametrize(("app", "ext"), KINDS, ids=KIND_IDS)
def test_libreoffice_accepts_a_signature_made_here(app, ext, office, tmp_path):
    document = make_protected(app, ext, tmp_path / "made", password="")
    session = opened(app, document, tmp_path)
    key = make_pkcs12(tmp_path / "keys")
    chosen = signing.choose_certificate(session, key, None, PASSPHRASE)

    signing.sign(session, chosen.id, "", ("", ""))

    (found,) = office.verify([document])
    assert found == [libreoffice.Signature(valid=True, signer=f"CN={SIGNER}")]


@pytest.mark.parametrize(("app", "ext"), KINDS, ids=KIND_IDS)
def test_a_signature_libreoffice_made_is_valid_here(app, ext, office, tmp_path):
    document = make_protected(app, ext, tmp_path / "made", password="")
    signed = tmp_path / f"signed.{ext}"
    office.sign(document, signed, make_pkcs12(tmp_path / "keys"), PASSPHRASE)

    listed = signing.list_signatures(opened(app, signed, tmp_path))

    assert [(s["valid"], s["name"]) for s in listed["data"]] == [(0, SIGNER)]


def changed(path: pathlib.Path, part: str, old: bytes, new: bytes) -> None:
    """`path` with `old` replaced by `new` in its `part`, the rest as it was."""
    with zipfile.ZipFile(path) as package:
        parts = [(info, package.read(info)) for info in package.infolist()]
    with zipfile.ZipFile(path, "w") as package:
        for info, data in parts:
            if info.filename == part:
                assert old in data, f"{old!r} is not in {part}"
            package.writestr(
                info, data.replace(old, new) if info.filename == part else data
            )


# What a signature covers, changed after LibreOffice signed it: the second
# form of a relationships digest accepted here must not let either through.
TAMPERING = {
    "text": ("word/document.xml", SENTENCE.encode(), SENTENCE.upper().encode()),
    "relationship": (
        "_rels/.rels",
        b'Target="word/document.xml"',
        b'Target="word/x.xml"',
    ),
}


@pytest.mark.parametrize("what", TAMPERING)
def test_a_signature_libreoffice_made_breaks_when_the_document_changes(
    what, office, tmp_path
):
    document = make_protected(apps.WORDS, "docx", tmp_path / "made", password="")
    signed = tmp_path / "signed.docx"
    office.sign(document, signed, make_pkcs12(tmp_path / "keys"), PASSPHRASE)

    changed(signed, *TAMPERING[what])

    (theirs,) = office.verify([signed])
    listed = signing.list_signatures(opened(apps.WORDS, signed, tmp_path))
    assert [s.valid for s in theirs] == [False]
    assert [s["valid"] for s in listed["data"]] == [1]


@pytest.fixture(scope="module")
def verdicts(office) -> dict[str, list[bool]]:
    """LibreOffice's verdict on each signature of each signed file, sorted."""
    files = sorted(DATA.iterdir())
    found = office.verify(files)
    return {
        path.name: sorted(s.valid for s in signatures)
        for path, signatures in zip(files, found, strict=True)
    }


@pytest.mark.parametrize("path", sorted(DATA.iterdir()), ids=lambda p: p.name)
def test_our_verdict_on_a_signed_file_is_libreoffices(path, verdicts, tmp_path):
    expected = verdicts[path.name]
    assert expected, f"LibreOffice finds no signature in {path.name}"
    # A copy: opening a document leaves a lock file beside it.
    document = tmp_path / path.name
    shutil.copyfile(path, document)

    listed = signing.list_signatures(
        opened(apps.choose_for(document), document, tmp_path)
    )

    assert sorted(s["valid"] == 0 for s in listed["data"]) == expected
