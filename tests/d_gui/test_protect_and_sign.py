"""File > Protect and signing, in real windows, in the engine that ships.

Headless Chromium has the editor and the bridge but not the window, and WebKit has
already differed from it where a user noticed. Each window here is a process of its
own, reopening what the last one saved.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from support.keys import SIGNER
from support.paths import repo_root
from support.protected import is_encrypted, make_protected, pdf_opens_with

from libera.host import apps, saving

from .conftest import signed_document

if TYPE_CHECKING:
    from .driver import Run

NEW = "zqx-New-Pass-9"
CHANGED = "zqx-Changed-Pass-3"


def test_file_protect_adds_changes_and_removes_a_docx_password(run: Run) -> None:
    plain = make_protected(apps.WORDS, "docx", run.work / "document", password="")
    run.window(plain, steps=(("protect", NEW),))
    assert is_encrypted(plain), "File > Protect left it in the clear"
    run.window(plain, passwords=("not it", NEW))
    run.window(plain, passwords=(NEW,), steps=(("protect", CHANGED),))
    run.window(plain, passwords=(NEW, CHANGED))
    run.window(plain, passwords=(CHANGED,), steps=(("unprotect", ""),))
    assert not is_encrypted(plain), "the password stayed"
    run.window(plain)


def test_file_protect_changes_removes_and_adds_a_pdf_password(run: Run) -> None:
    pdf = run.work / "Protected.pdf"
    shutil.copyfile(repo_root() / "build/engine/smoke-pdf/protected.pdf", pdf)
    run.window(pdf, passwords=("not it", "secret"), steps=(("protect", NEW),))
    assert pdf_opens_with(pdf, NEW), "the new password does not open it"
    assert not pdf_opens_with(pdf, "secret"), "the old one still does"
    run.window(pdf, passwords=("secret", NEW))
    run.window(pdf, passwords=(NEW,), steps=(("unprotect", ""),))
    assert b"/Encrypt" not in pdf.read_bytes(), "the password stayed"
    run.window(pdf)
    run.window(pdf, steps=(("protect", NEW),))
    assert pdf_opens_with(pdf, NEW), "a password added does not open it"


def test_a_signature_is_made_shown_and_removed(run: Run) -> None:
    signed = signed_document(run, "signature")
    run.window(signed, steps=(("shows-signature", SIGNER),))
    run.window(signed, steps=(("remove-signature", ""),))
    assert not saving.is_signed(signed), "the signature stayed in the file"
