"""Digital signatures judged by Office itself: Word, Excel and PowerPoint, through
COM, in the desktop session it needs. It takes no account to answer this.

Only for the signature over the content. About a certificate Office says what it
says of one it has no way to trust: 0, its "error", for the test certificate here,
and 5, "expired", for those in the test data. Each is said in `IsValid` too, which
is therefore False for all of them, a tampered file included, and tells nothing.

Asking Office to sign puts up a dialog, which no script can answer: a signature
Office made is the test data's.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import zipfile

import pytest
from support.keys import PASSPHRASE, make_pkcs12
from support.paths import repo_root
from support.protected import SENTENCE, make_protected, open_in

from libera.host import apps, signing

pytestmark = pytest.mark.skipif(
    not pathlib.Path(
        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"
    ).is_file(),
    reason="Office is on the Windows builder (notes/15-builders.md)",
)

DATA = repo_root() / "tests/b_integration/host/data/signed"
# MsoContentVerificationResults.
VALID, INVALID = 3, 4
OPENS = {
    ".docx": (
        "$app = New-Object -ComObject Word.Application; $app.DisplayAlerts = 0;"
        "$doc = $app.Documents.Open($env:SIGNED_FILE, $false, $true, $false);"
        "$doc.Signatures.Item(1).Details.ContentVerificationResults;"
        "$doc.Close(0); $app.Quit()"
    ),
    ".xlsx": (
        "$app = New-Object -ComObject Excel.Application; $app.DisplayAlerts = $false;"
        "$doc = $app.Workbooks.Open($env:SIGNED_FILE, 0, $true);"
        "$doc.Signatures.Item(1).Details.ContentVerificationResults;"
        "$doc.Close($false); $app.Quit()"
    ),
    ".pptx": (
        "$app = New-Object -ComObject PowerPoint.Application;"
        "$doc = $app.Presentations.Open($env:SIGNED_FILE, -1, 0, 0);"
        "$doc.Signatures.Item(1).Details.ContentVerificationResults;"
        "$doc.Close(); $app.Quit()"
    ),
}
PROGRAMS = {".docx": "WINWORD.EXE", ".xlsx": "EXCEL.EXE", ".pptx": "POWERPNT.EXE"}


def office_says(document: pathlib.Path) -> int:
    """What the program of this kind makes of the signature over the content. Not
    with that program already open, whose windows may be someone's work: it is
    stopped afterwards, however the answer went."""
    program = PROGRAMS[document.suffix]
    running = subprocess.run(
        ["tasklist", "/fi", f"imagename eq {program}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if program in running:
        pytest.skip(f"{program} is open")
    try:
        done = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                OPENS[document.suffix],
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "SIGNED_FILE": str(document)},
            timeout=90,
        )
    finally:
        subprocess.run(
            ["taskkill", "/f", "/im", program],
            check=False,
            capture_output=True,
        )
    return int(done.stdout.strip())


def signed_here(app: apps.App, ext: str, tmp_path: pathlib.Path) -> pathlib.Path:
    document = make_protected(app, ext, tmp_path / "made", password="")
    session = open_in(app, document, tmp_path / "work")
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
def test_office_accepts_a_signature_made_here(app: apps.App, ext: str, tmp_path):
    assert office_says(signed_here(app, ext, tmp_path)) == VALID


def test_office_refuses_one_when_a_word_has_changed(tmp_path):
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

    assert office_says(changed) == INVALID


@pytest.mark.parametrize("ext", ["docx", "xlsx", "pptx"])
def test_office_accepts_one_it_made(ext: str, tmp_path):
    """And what the verdict is worth."""
    copy = tmp_path / f"office.{ext}"
    shutil.copyfile(DATA / f"ms-office-2010-signed.{ext}", copy)

    assert office_says(copy) == VALID
