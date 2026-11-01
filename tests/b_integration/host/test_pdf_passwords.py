"""File > Protect on a PDF, with x2t run out of the payload: its password set,
changed and removed. Editor.bin is the PDF as it was opened, under the
password it had, and x2t rewrites the whole file under the new one.

A change of password padded every stream with 0xFF until core 0185 (an AES
stream decrypts to fewer bytes than its Length), and left the old encryption
dictionary in the file until 0187. The check that a password opens the file
is the reader's (support.protected.pdf_opens_with).
"""

from __future__ import annotations

import shutil

from support.paths import repo_root
from support.protected import pdf_opens_with, pdf_streams

from libera import payload as payload_mod
from libera.host import apps, convert, session as sessions, window
from libera.host.session import Session

SMOKE_PDF = repo_root() / "build" / "engine" / "smoke-pdf"
NEW = "zqx-New-Pass-9"


def pdf_session(pdf, work, opened_with: str, password: str) -> Session:
    """The PDF open in the PDF editor, the smoke test's comment in its log."""
    session = Session(
        payload=payload_mod.resolve().root, work=work, document=pdf, app=apps.PDFS
    )
    sessions.configure(session)
    convert.convert_to_editor_bin(session, pdf)
    (session.doc / "changes").mkdir()
    shutil.copy(SMOKE_PDF / "changes0.txt", session.doc / "changes" / "changes0.json")
    session.opened_with, session.password = opened_with, password
    return session


def save(session: Session, target):
    convert.export(session, target, 513, None)
    return target


def test_file_protect_changes_a_pdfs_password(tmp_path):
    session = pdf_session(SMOKE_PDF / "protected.pdf", tmp_path / "w", "secret", NEW)

    saved = save(session, tmp_path / "changed.pdf")

    assert pdf_opens_with(saved, NEW)
    assert not pdf_opens_with(saved, "secret")
    # The old encryption dictionary is not copied over with the rest.
    assert saved.read_bytes().count(b"/Filter /Standard") == 1


def test_a_changed_then_removed_password_leaves_no_padding(tmp_path):
    """Removed, the streams are in clear: a change that padded them with
    0xFF passes its padding on, and the removal adds its own."""
    changed = save(
        pdf_session(SMOKE_PDF / "protected.pdf", tmp_path / "a", "secret", NEW),
        tmp_path / "changed.pdf",
    )
    session = pdf_session(changed, tmp_path / "b", NEW, "")

    removed = save(session, tmp_path / "removed.pdf")

    data = removed.read_bytes()
    assert b"/Encrypt" not in data
    assert b"/Subtype /Text" in data
    streams = pdf_streams(removed)
    assert streams
    assert not [s for s in streams if s.endswith(b"\xff\xff\xff\xff")]


def test_file_protect_gives_a_pdf_a_password(tmp_path):
    session = pdf_session(SMOKE_PDF / "sample.pdf", tmp_path / "w", "", NEW)

    saved = save(session, tmp_path / "added.pdf")

    assert pdf_opens_with(saved, NEW)
    # Names are never encrypted: the comment's annotation is there.
    assert b"/Subtype /Text" in saved.read_bytes()


def test_protect_is_offered_for_the_pdfs_pypdf_and_x2t_encrypt(tmp_path):
    """pypdf's RC4 and AES-256 with every permission, as x2t's own."""
    added = save(
        pdf_session(SMOKE_PDF / "sample.pdf", tmp_path / "w", "", NEW),
        tmp_path / "added.pdf",
    )
    for pdf in (SMOKE_PDF / "encrypted.pdf", SMOKE_PDF / "protected.pdf", added):
        assert convert.may_change_password(pdf), pdf.name


def test_a_reload_after_a_change_of_password_opens_with_the_new_one(tmp_path):
    """Editor.bin was the PDF under its old password, edits or none, and the
    reloaded editor asked for that one."""
    session = pdf_session(SMOKE_PDF / "protected.pdf", tmp_path / "w", "secret", NEW)
    shutil.rmtree(session.doc / "changes")

    window.fold_changes_in(session)

    assert pdf_opens_with(session.editor_bin, NEW)
    assert session.opened_with == NEW
