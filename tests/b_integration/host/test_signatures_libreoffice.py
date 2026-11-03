"""Digital signatures judged against LibreOffice's: a signature made here must
be one LibreOffice accepts, one LibreOffice made must be valid here, and on a
signed file from elsewhere our verdict must be LibreOffice's.

LibreOffice runs in a container (`support.libreoffice`), so these skip where
no container engine is running. Word is the program that matters most and is
not here; LibreOffice is the second implementation that is, and the first
check against it found a signature made here on every document Words writes
that LibreOffice refused (2026-11-03).
"""

from __future__ import annotations

import pathlib
import shutil

import pytest
from support import libreoffice
from support.keys import PASSPHRASE, SIGNER, make_pkcs12
from support.protected import make_protected, open_in

from libera.host import apps, signing

DATA = pathlib.Path(__file__).parent / "data" / "signed"
KINDS = [(apps.WORDS, "docx"), (apps.TABLES, "xlsx"), (apps.SLIDES, "pptx")]
KIND_IDS = ["docx", "xlsx", "pptx"]

# Files LibreOffice calls valid and our verifier, core's COOXMLVerifier, does
# not. Measured on 2026-11-03 with Debian's LibreOffice 25.2; Apache POI
# agrees with LibreOffice on all three. The causes are not known yet.
REFUSED_HERE = {
    "hello-world-office-2010-technical-preview.docx": "Office 2010's preview",
    "signed.docx": "SHA-512, and no relationship transform",
    "hello-world-signed.pptx": "Office 2007; our verifier answers 4",
}


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


# raises=AssertionError: a reference that fails raises LibreOfficeError, which
# must not pass for the known disagreement.
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="our verifier refuses every signature LibreOffice makes; it digests"
    " the package's _rels/.rels otherwise (measured 2026-11-03, cause not known)",
)
@pytest.mark.parametrize(("app", "ext"), KINDS, ids=KIND_IDS)
def test_a_signature_libreoffice_made_is_valid_here(app, ext, office, tmp_path):
    document = make_protected(app, ext, tmp_path / "made", password="")
    signed = tmp_path / f"signed.{ext}"
    office.sign(document, signed, make_pkcs12(tmp_path / "keys"), PASSPHRASE)

    listed = signing.list_signatures(opened(app, signed, tmp_path))

    assert [(s["valid"], s["name"]) for s in listed["data"]] == [(0, SIGNER)]


@pytest.fixture(scope="module")
def verdicts(office) -> dict[str, list[bool]]:
    """LibreOffice's verdict on each signature of each signed file, sorted."""
    files = sorted(DATA.iterdir())
    found = office.verify(files)
    return {
        path.name: sorted(s.valid for s in signatures)
        for path, signatures in zip(files, found, strict=True)
    }


def corpus():
    for path in sorted(DATA.iterdir()):
        marks = []
        if path.name in REFUSED_HERE:
            marks.append(
                pytest.mark.xfail(
                    strict=True, raises=AssertionError, reason=REFUSED_HERE[path.name]
                )
            )
        yield pytest.param(path, id=path.name, marks=marks)


@pytest.mark.parametrize("path", list(corpus()))
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
