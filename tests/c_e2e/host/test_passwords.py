"""A protected document in the editor, in a real browser: the editor's own
dialog asks for its password, again after a wrong one, and the document
opens; saved, it is still protected (opening.ask_password)."""

from __future__ import annotations

import json
import logging

from support.protected import SECRET, SENTENCE, is_encrypted, make_protected, open_in

from libera.host import apps, convert, hooks, saving, session as sessions

MARK = "zqx-typed-4471"


def test_a_protected_document_asks_opens_and_saves_protected(
    editor_with, tmp_path, caplog
):
    caplog.set_level(logging.DEBUG)
    protected = make_protected(apps.WORDS, "docx", tmp_path / "made")

    editor = editor_with([], document=protected, password=("not it", SECRET))

    assert "documenteditor" in editor.frame.url
    assert editor.report()["errors"] == []
    editor.press("End")
    editor.page.keyboard.type(" " + MARK)
    with editor.answered("save") as saved:
        editor.press("ControlOrMeta+s")
    assert saved.value.json()["error"] == 0

    assert is_encrypted(protected)
    sessions.SESSIONS.clear()
    again = open_in(apps.WORDS, protected, tmp_path / "again")
    asked = again.password_asked
    assert asked is not None
    asked.answer(SECRET)
    text = again.editor_bin.read_bytes()
    assert SENTENCE.encode("utf-16-le") in text
    assert MARK.encode("utf-16-le") in text
    assert SECRET not in json.dumps(editor.reported())
    assert any("SetAdvancedOptions" in line for line in editor.console)
    assert not [line for line in editor.console if SECRET in line]
    assert SECRET not in caplog.text


NEW = "zqx-New-Pass-9"


def reopened_text(document, work, password: str | None) -> bytes:
    """`document` opened by the host, with `password` when it asks; None
    says it must not ask. In a session of its own, beside the window's,
    which stays registered for the saves that follow."""
    again = open_in(apps.WORDS, document, work)
    asked = again.password_asked
    if password is None:
        assert asked is None, "it asks for a password"
        return again.editor_bin.read_bytes()
    assert asked is not None, "it opens without a password"
    asked.answer("not it")
    asked = again.password_asked
    assert asked is not None
    assert asked.code == convert.WRONG_PASSWORD
    asked.answer(password)
    assert again.password_asked is None
    return again.editor_bin.read_bytes()


def test_file_protect_gives_a_document_a_password(editor_with, tmp_path):
    """File > Protect saves at once, with the password typed
    (asc_setCurrentPassword, what its dialog calls)."""
    plain = make_protected(apps.WORDS, "docx", tmp_path / "made", password="")
    editor = editor_with([], document=plain)
    assert editor.frame.evaluate("() => Asc.editor.asc_isProtectionSupport()")
    editor.press("End")
    editor.page.keyboard.type(" " + MARK)

    with editor.answered("save") as saved:
        editor.frame.evaluate("(p) => Asc.editor.asc_setCurrentPassword(p)", NEW)
    assert saved.value.json()["error"] == 0

    assert is_encrypted(plain)
    assert MARK.encode("utf-16-le") in reopened_text(plain, tmp_path / "again", NEW)
    assert not [line for line in editor.console if NEW in line]


def test_file_protect_changes_and_removes_a_password(editor_with, tmp_path):
    protected = make_protected(apps.WORDS, "docx", tmp_path / "made")
    editor = editor_with([], document=protected, password=SECRET)

    with editor.answered("save") as saved:
        editor.frame.evaluate("(p) => Asc.editor.asc_setCurrentPassword(p)", NEW)
    assert saved.value.json()["error"] == 0
    assert SENTENCE.encode("utf-16-le") in reopened_text(protected, tmp_path / "a", NEW)

    with editor.answered("save") as saved:
        editor.frame.evaluate("() => Asc.editor.asc_resetPassword()")
    assert saved.value.json()["error"] == 0
    assert not is_encrypted(protected)
    assert SENTENCE.encode("utf-16-le") in reopened_text(
        protected, tmp_path / "b", None
    )


def test_a_reloaded_protected_document_is_saved_protected(editor_with, tmp_path):
    """A reload makes a new page, and the editor's password goes with the
    old one; each save carries the editor's, so the host gives it back."""
    protected = make_protected(apps.WORDS, "docx", tmp_path / "made")
    editor = editor_with([], document=protected, password=SECRET)

    editor.page.reload()
    editor.wait_until_ready()
    assert editor.frame.evaluate("() => Asc.editor.currentPassword") == SECRET
    editor.press("End")
    editor.page.keyboard.type(" " + MARK)
    with editor.answered("save") as saved:
        editor.press("ControlOrMeta+s")
    assert saved.value.json()["error"] == 0

    assert is_encrypted(protected)
    assert MARK.encode("utf-16-le") in reopened_text(protected, tmp_path / "a", SECRET)


def test_a_protected_spreadsheet_saves_protected(editor_with, tmp_path):
    """Tables keeps a state of its own for the question it asked, and its
    save returns early while that is set (cell/Local/api.js)."""
    protected = make_protected(apps.TABLES, "xlsx", tmp_path / "made")
    editor = editor_with([], document=protected, password=SECRET)
    assert editor.frame.evaluate("() => Asc.editor.asc_isProtectionSupport()")
    editor.page.keyboard.type(MARK)
    editor.page.keyboard.press("Enter")

    with editor.answered("save") as saved:
        editor.press("ControlOrMeta+s")
    assert saved.value.json()["error"] == 0

    assert is_encrypted(protected)
    sessions.SESSIONS.clear()
    again = open_in(apps.TABLES, protected, tmp_path / "again")
    asked = again.password_asked
    assert asked is not None
    asked.answer(SECRET)
    assert MARK.encode("utf-16-le") in again.editor_bin.read_bytes()


def test_a_protect_that_fails_leaves_the_password_as_it_was(
    editor_with, tmp_path, monkeypatch
):
    """The editor keeps the password it sent whatever the save's outcome, and
    its panel still says the old one: so the bridge gives it back the one the
    file has, and the host keeps it too."""
    protected = make_protected(apps.WORDS, "docx", tmp_path / "made")
    original = protected.read_bytes()
    editor = editor_with([], document=protected, password=SECRET)
    monkeypatch.setattr(saving, "_export", lambda *_: None)

    with editor.answered("save") as saved:
        editor.frame.evaluate("(p) => Asc.editor.asc_setCurrentPassword(p)", NEW)
    assert saved.value.json()["error"] == saving.SaveOutcome.FAILED

    editor.frame.wait_for_function(
        "(p) => Asc.editor.currentPassword === p", arg=SECRET
    )
    assert protected.read_bytes() == original
    assert next(iter(sessions.SESSIONS.values())).password == SECRET


def test_protect_is_offered_only_where_a_password_is_kept(editor_with, tmp_path):
    """x2t writes a .txt in clear whatever the password, and the editor would
    then show it as protected."""
    text = tmp_path / "notes.txt"
    text.write_text(SENTENCE + "\n", encoding="utf-8")

    editor = editor_with([], document=text)

    assert not editor.frame.evaluate("() => Asc.editor.asc_isProtectionSupport()")


def test_saved_as_text_the_document_and_the_editor_drop_the_password(
    editor_with, tmp_path, monkeypatch
):
    """Asked first, since x2t writes a .txt in clear and says nothing. The
    window then has the .txt open, and the editor's password would have gone
    to the next Save As. The editor still offers Protect, which it reads as it
    loads: a password set there asks too, and declined, is not kept."""
    from support import ScriptedShell

    protected = make_protected(apps.WORDS, "docx", tmp_path / "made")
    editor = editor_with([], document=protected, password=SECRET)
    text = tmp_path / "notes.txt"
    asked = []
    answers = iter([True, False])
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            choose_save_path=lambda *_: str(text),
            confirm_unprotected=lambda d: asked.append(d) or next(answers),
        ),
    )

    with editor.answered("save") as saved:
        editor.press("Control+Shift+s")
    reply = saved.value.json()

    assert reply["error"] == 0
    assert not reply["protected"]
    assert SENTENCE in text.read_text(encoding="utf-8")
    editor.frame.wait_for_function("() => Asc.editor.currentPassword === ''")
    session = next(iter(sessions.SESSIONS.values()))
    assert not session.password

    with editor.answered("save") as saved:
        editor.frame.evaluate("(p) => Asc.editor.asc_setCurrentPassword(p)", NEW)
    assert saved.value.json()["error"] == saving.SaveOutcome.DECLINED

    assert asked == [text, text]
    editor.frame.wait_for_function("() => Asc.editor.currentPassword === ''")
    assert not session.password
