"""The blank document with something in its settings or its body, and the
same typed in and saved.

Through the editor, because a save with no edit copies the file and converts
nothing.
"""

from __future__ import annotations

import re
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
DOCUMENT = "word/document.xml"


def _blank_with(path: pathlib.Path, part: str, change) -> pathlib.Path:
    source = payload_mod.resolve().root / "empty" / apps.WORDS.blank
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(path, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item)
            if item.filename == part:
                data = change(data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)
    return path


def blank(
    tmp_path: pathlib.Path, insert: str = "", before: str = "<w:defaultTabStop"
) -> pathlib.Path:
    """The payload's blank document, with `insert` in its settings before the
    first `before`."""

    def change(text: str) -> str:
        assert before in text
        return text.replace(before, insert + before, 1)

    return _blank_with(tmp_path / "settings.docx", SETTINGS, change)


def with_body(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    """The payload's blank document, its paragraphs replaced by `body`."""

    def change(text: str) -> str:
        changed, count = re.subn(
            r"<w:body>.*?(<w:sectPr)",
            lambda m: "<w:body>" + body + m[1],
            text,
            flags=re.DOTALL,
        )
        assert count == 1
        return changed

    return _blank_with(tmp_path / "body.docx", DOCUMENT, change)


def edited_and_saved(editor_with, document: pathlib.Path, part: str = SETTINGS) -> str:
    """`part` of the document once a letter is typed and the document saved."""
    editor = editor_with([], document)
    editor.press("x")
    session = SESSIONS["0"]
    log = session.change_log.path
    deadline = time.monotonic() + 30
    while not (log.exists() and log.stat().st_size) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert save_document(session, SaveRequest())["error"] == 0
    with zipfile.ZipFile(session.document) as saved:
        return saved.read(part).decode("utf-8")
