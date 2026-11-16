"""The blank document with something in its settings, typed in and saved.

Through the editor, because a save with no edit copies the file and converts
nothing.
"""

from __future__ import annotations

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


def blank(
    tmp_path: pathlib.Path, insert: str = "", before: str = "<w:defaultTabStop"
) -> pathlib.Path:
    """The payload's blank document, with `insert` in its settings before the
    first `before`."""
    source = payload_mod.resolve().root / "empty" / apps.WORDS.blank
    document = tmp_path / "settings.docx"
    if not insert:
        shutil.copyfile(source, document)
        return document
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(document, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item)
            if item.filename == SETTINGS:
                text = data.decode("utf-8")
                assert before in text
                data = text.replace(before, insert + before, 1).encode("utf-8")
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
