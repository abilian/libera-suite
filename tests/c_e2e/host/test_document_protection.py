"""A document's editing protection, through an edit and a save.

The editor sends the document's protection back with every save, an empty
record when there is none, and x2t wrote that as `<w:documentProtection />`:
every document edited here came back with an element Word never writes. Seen
in ElixirOffice's 0.7.3, whose fix is the same guard in core.

Through the editor, because a save with no edit copies the file and converts
nothing.
"""

from __future__ import annotations

import re
import shutil
import time
import zipfile
from typing import TYPE_CHECKING

from libera import payload as payload_mod
from libera.host import apps
from libera.host.saving import SaveRequest, save_document
from libera.host.session import SESSIONS

if TYPE_CHECKING:
    import pathlib

SETTINGS = "word/settings.xml"
PROTECTION = re.compile(r"<w:documentProtection\b[^>]*>")
READ_ONLY = '<w:documentProtection w:edit="readOnly" w:enforcement="0"/>'


def blank(tmp_path: pathlib.Path, protection: str = "") -> pathlib.Path:
    """The payload's blank document, with `protection` in its settings."""
    source = payload_mod.resolve().root / "empty" / apps.WORDS.blank
    document = tmp_path / "protected.docx"
    if not protection:
        shutil.copyfile(source, document)
        return document
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(document, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item)
            if item.filename == SETTINGS:
                text = data.decode("utf-8")
                assert "<w:defaultTabStop" in text
                text = text.replace(
                    "<w:defaultTabStop", protection + "<w:defaultTabStop", 1
                )
                data = text.encode("utf-8")
            zout.writestr(item, data)
    return document


def edited_and_saved(editor_with, document: pathlib.Path) -> str:
    """The settings part once a letter is typed and the document saved."""
    editor = editor_with([], document)
    editor.press("x")
    session = SESSIONS["0"]
    log = session.change_log.path
    deadline = time.monotonic() + 30
    while not (log.exists() and log.stat().st_size) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert save_document(session, SaveRequest())["error"] == 0
    with zipfile.ZipFile(session.document) as saved:
        return saved.read(SETTINGS).decode("utf-8")


def test_a_document_without_protection_is_saved_without_one(editor_with, tmp_path):
    settings = edited_and_saved(editor_with, blank(tmp_path))

    assert PROTECTION.findall(settings) == []


def test_a_documents_protection_is_kept(editor_with, tmp_path):
    settings = edited_and_saved(editor_with, blank(tmp_path, READ_ONLY))

    (found,) = PROTECTION.findall(settings)
    assert 'w:edit="readOnly"' in found
