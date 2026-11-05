"""Digital signatures judged by Microsoft's own code: `System.IO.Packaging`, in the
.NET Framework every Windows has, which reads a signed Office file as the standard
says.

Not Word, which may ask for more, and whose verdict no script on a Mac can read
(notes/plans/owner-todo.md). It is the nearest thing that runs by itself. The
LibreOffice verdicts are in test_signatures_libreoffice.py.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import zipfile

import pytest
from support.keys import PASSPHRASE, make_pkcs12
from support.protected import SENTENCE, make_protected, open_in

from libera.host import apps, signing

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="System.IO.Packaging is the .NET Framework's"
)

DATA = pathlib.Path(__file__).parent / "data" / "signed"
VERDICT = """
Add-Type -AssemblyName WindowsBase
$package = [System.IO.Packaging.Package]::Open(
    $env:SIGNED_FILE, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
try {
    $manager = New-Object System.IO.Packaging.PackageDigitalSignatureManager($package)
    $manager.VerifySignatures($false)
} finally {
    $package.Close()
}
"""


def microsoft_says(document: pathlib.Path) -> str:
    """Success, InvalidSignature, NotSigned: `VerifyResult`. About the signature
    alone: a test certificate is no more trusted here than anywhere."""
    done = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", VERDICT],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "SIGNED_FILE": str(document)},
        timeout=60,
    )
    return done.stdout.strip()


def signed_here(app: apps.App, ext: str, tmp_path: pathlib.Path) -> pathlib.Path:
    document = make_protected(app, ext, tmp_path / "made", password="")
    session = open_in(app, document, tmp_path / "work")
    if not session.layout.sign.is_file():
        pytest.skip("this payload has no libera-sign (core 0190)")
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    signing.sign(session, chosen.id, "", ("", ""))
    return document


@pytest.mark.parametrize(
    ("app", "ext"),
    [(apps.WORDS, "docx"), (apps.TABLES, "xlsx"), (apps.SLIDES, "pptx")],
    ids=["docx", "xlsx", "pptx"],
)
def test_a_signature_made_here_verifies(app: apps.App, ext: str, tmp_path):
    assert microsoft_says(signed_here(app, ext, tmp_path)) == "Success"


def test_a_word_changed_after_signing_does_not(tmp_path):
    """What makes the others mean something."""
    signed = signed_here(apps.WORDS, "docx", tmp_path)
    changed = tmp_path / "changed.docx"
    with zipfile.ZipFile(signed) as source, zipfile.ZipFile(changed, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "word/document.xml":
                assert SENTENCE.encode() in data
                data = data.replace(SENTENCE.encode(), b"Something else was signed")
            target.writestr(item, data)

    assert microsoft_says(changed) == "InvalidSignature"


def test_a_signature_over_relationships_of_no_part_verifies(tmp_path):
    """A file from before core 0196: the signer leaves them out (core 0197)."""
    document = make_protected(apps.SLIDES, "pptx", tmp_path / "made", password="")
    with zipfile.ZipFile(document, "a") as package:
        package.writestr(
            "ppt/handoutMasters/_rels/handoutMaster1.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.openxml'
            'formats.org/officeDocument/2006/relationships/theme"'
            ' Target="../theme/theme1.xml"/></Relationships>',
        )
    session = open_in(apps.SLIDES, document, tmp_path / "work")
    if not session.layout.sign.is_file():
        pytest.skip("this payload has no libera-sign (core 0190)")
    chosen = signing.choose_certificate(
        session, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    signing.sign(session, chosen.id, "", ("", ""))

    assert microsoft_says(document) == "Success"


def test_a_signature_office_made_verifies(tmp_path):
    """And what the verdict is worth: one that came from Office."""
    copy = tmp_path / "office.docx"
    shutil.copyfile(DATA / "ms-office-2010-signed.docx", copy)

    assert microsoft_says(copy) == "Success"
