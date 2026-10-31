"""Protected documents, with x2t run out of the payload.

Each is made the way a save makes one: a document opened, then exported with
its password, which x2t encrypts with (OLE for OOXML, AES-CBC for
OpenDocument). Files saved by LibreOffice, and OOXML files encrypted the way
Word does by msoffcrypto-tool, were measured on 2026-10-30
(notes/plans/release-0.8.md): they behave as these do, but for LibreOffice
26's own ODF encryption, which is refused before x2t. No file saved by Word
itself has been tried.
"""

from __future__ import annotations

import logging

import pytest
from support import ScriptedShell
from support.protected import (
    SECRET,
    SENTENCE,
    is_encrypted,
    make_protected,
    open_in,
    tamper,
)

from libera.host import apps, convert, hooks, opening, session as sessions

KINDS = [
    (apps.WORDS, "docx"),
    (apps.WORDS, "odt"),
    (apps.TABLES, "xlsx"),
    (apps.TABLES, "ods"),
    (apps.SLIDES, "pptx"),
    (apps.SLIDES, "odp"),
]


@pytest.mark.parametrize(("app", "ext"), KINDS, ids=[ext for _, ext in KINDS])
def test_a_protected_document_asks_until_its_password_opens_it(
    tmp_path, caplog, app: apps.App, ext: str
):
    caplog.set_level(logging.DEBUG)
    protected = make_protected(app, ext, tmp_path)
    assert is_encrypted(protected)

    session = open_in(app, protected, tmp_path / "work")
    asked = session.password_asked
    assert asked is not None
    assert asked.code == convert.NO_PASSWORD
    assert not session.editor_bin.exists()

    asked.answer("not it")
    asked = session.password_asked
    assert asked is not None
    assert asked.code == convert.WRONG_PASSWORD

    asked.answer(SECRET)
    assert session.password_asked is None
    with session.editor_bin.open("rb") as stream:
        assert stream.read(4) == convert.SIGNATURES[app.doctype]
    if app is not apps.SLIDES:
        assert SENTENCE.encode("utf-16-le") in session.editor_bin.read_bytes()
    # In memory only: in no file the session holds, and in no log line.
    for path in (tmp_path / "work").rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes(), path
    assert SECRET not in caplog.text


@pytest.mark.parametrize(("app", "ext"), KINDS, ids=[ext for _, ext in KINDS])
def test_a_protected_document_is_saved_protected(tmp_path, app: apps.App, ext: str):
    """x2t given no password writes the document unprotected, exit 0."""
    protected = make_protected(app, ext, tmp_path)
    session = open_in(app, protected, tmp_path / "work")
    asked = session.password_asked
    assert asked is not None
    asked.answer(SECRET)

    saved = tmp_path / f"Saved.{ext}"
    convert.export(session, saved, app.ids_by_ext[ext], None)

    assert is_encrypted(saved)
    sessions.SESSIONS.clear()
    again = open_in(app, saved, tmp_path / "again")
    asked = again.password_asked
    assert asked is not None
    asked.answer(SECRET)
    assert again.password_asked is None
    assert again.editor_bin.is_file()


def test_recovered_edits_ask_for_the_password_their_saves_need(tmp_path, monkeypatch):
    """Recovered, the edits open from their Editor.bin, decrypted already,
    and would be saved unprotected. The password typed is checked against the
    document on disk: a mistyped one would become the document's."""
    protected = make_protected(apps.WORDS, "docx", tmp_path)
    crashed = open_in(apps.WORDS, protected, tmp_path / "crashed")
    asked = crashed.password_asked
    assert asked is not None
    asked.answer(SECRET)
    crashed.change_log.record("an edit", None, 1)
    crashed.mark_modified(True)
    sessions.SESSIONS.clear()  # the crash: its window is gone
    monkeypatch.setattr(hooks, "shell", ScriptedShell(ask_to_recover=lambda _d: True))

    recovered = open_in(apps.WORDS, protected, tmp_path / "recovered")

    assert recovered.change_log, "these are the crashed session's edits"
    asked = recovered.password_asked
    assert asked is not None
    assert asked.code == convert.NO_PASSWORD
    asked.answer("not it")
    asked = recovered.password_asked
    assert asked is not None
    assert asked.code == convert.WRONG_PASSWORD
    assert not recovered.password
    asked.answer(SECRET)
    assert recovered.password_asked is None
    assert recovered.password == SECRET
    assert not (recovered.work / "password-check").exists()


@pytest.mark.parametrize(
    "app", [apps.WORDS, apps.TABLES, apps.SLIDES], ids=["docx", "xlsx", "pptx"]
)
def test_a_tampered_protected_document_is_refused(tmp_path, app: apps.App):
    """Its HMAC fails, and x2t opened it all the same (core 0183, from
    ElixirOffice). The right password, and still no document. A changed
    byte of the package was measured too, on files Word's way encrypts
    (notes/plans/release-0.8.md)."""
    protected = make_protected(app, app.ext, tmp_path)
    tamper(protected)
    session = open_in(app, protected, tmp_path / "work")
    asked = session.password_asked
    assert asked is not None

    with pytest.raises(convert.ConversionError) as refused:
        asked.answer(SECRET)

    assert not isinstance(refused.value, convert.PasswordNeededError)
    assert not session.editor_bin.exists()


def test_the_next_document_in_a_session_is_not_saved_with_the_last_password(
    tmp_path,
):
    """`libera --serve` opens every document into its one session. Kept, the
    password of the last encrypted every save of the next, unasked."""
    protected = make_protected(apps.WORDS, "docx", tmp_path)
    session = open_in(apps.WORDS, protected, tmp_path / "work")
    asked = session.password_asked
    assert asked is not None
    asked.answer(SECRET)
    plain = tmp_path / "plain.txt"
    plain.write_text(SENTENCE + "\n", encoding="utf-8")

    opening.open_document(session, plain)
    saved = tmp_path / "Saved.docx"
    convert.export(session, saved, apps.WORDS.ids_by_ext["docx"], None)

    assert not session.password
    assert not is_encrypted(saved)
