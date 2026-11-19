"""Nothing in the editors names Nextcloud.

Euro-Office is Nextcloud's fork, and its `main` brought a Smart Picker toolbar
button, a picker that "/" opens, and "Ask Nextcloud Assistant" in the
paragraph and cell menus. Each shows once the page hosting the editor says
Nextcloud is there (`setSmartPickerAvailable`, `setAssistantAvailable`), which
ours never does. Nextcloud is a competitor, so these fail the day upstream
shows any of it without being asked: the interface's text is read where a
user would see it, after each thing that could bring one of them up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from support.documents import blank_of

from libera.host import apps

if TYPE_CHECKING:
    from pathlib import Path

    from c_e2e.conftest import Editor

NAMES = ("Nextcloud", "Smart Picker")


def shown(editor: Editor) -> list[str]:
    # A big toolbar button wraps its caption: "Smart\nPicker".
    text = " ".join(editor.frame.evaluate("() => document.body.innerText").split())
    return [name for name in NAMES if name in text]


@pytest.mark.parametrize(
    "app", [apps.WORDS, apps.TABLES, apps.SLIDES], ids=lambda a: a.name
)
def test_no_editor_shows_nextcloud(
    editor_with, sample_document: Path, tmp_path: Path, app
):
    document = (
        sample_document
        if app is apps.WORDS
        else blank_of(app, tmp_path / f"blank.{app.ext}")
    )
    editor = editor_with([], document)
    assert shown(editor) == [], "on opening"

    editor.frame.click('li.ribtab a[data-tab="ins"]')
    editor.frame.wait_for_timeout(300)
    assert shown(editor) == [], "on the Insert tab"

    # The Assistant's item is offered for a selection.
    editor.frame.click("#editor_sdk")
    editor.page.keyboard.press("ControlOrMeta+A")
    editor.frame.click("#editor_sdk", button="right")
    editor.frame.wait_for_timeout(500)
    assert shown(editor) == [], "in the right-click menu"
    editor.page.keyboard.press("Escape")

    editor.frame.click("#editor_sdk")
    editor.page.keyboard.type("/")
    editor.frame.wait_for_timeout(500)
    assert shown(editor) == [], "after typing /"
