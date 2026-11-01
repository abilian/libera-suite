"""A protected document in the editor, in a real browser: the editor's own
dialog asks for its password, again after a wrong one, and the document
opens; saved, it is still protected (opening.ask_password)."""

from __future__ import annotations

import json
import logging

from support.protected import SECRET, SENTENCE, is_encrypted, make_protected, open_in

from libera.host import apps, session as sessions

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
