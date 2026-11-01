"""Each editor loads in each language the documentation has.

In French, Italian, Spanish and Portuguese, Words used to load with its toolbar
greyed out and never take an edit: a string Euro-Office added to en.json alone
was undefined, and the toolbar threw while building itself. The page still
reached "ready", so readiness says nothing here; the error it threw does.
"""

from __future__ import annotations

import shutil

import pytest

from libera import payload as payload_mod
from libera.host import language

LANGUAGES = ["fr-FR", "de-DE", "it-IT", "es-ES"]


@pytest.mark.parametrize("ext", ["docx", "xlsx", "pptx"])
@pytest.mark.parametrize("tag", LANGUAGES)
def test_the_editor_loads_in_the_language_without_an_error(
    editor_with, tmp_path, monkeypatch, tag, ext
):
    document = tmp_path / f"blank.{ext}"
    shutil.copyfile(payload_mod.resolve().root / "empty" / f"new.{ext}", document)
    monkeypatch.setattr(language, "get_language", lambda: tag)

    editor = editor_with([], document=document)

    # The editor's own reading of the tag, as locale.js makes it: fr-FR is fr.
    asked = f"/main/locale/{tag.split('-')[0]}.json"
    assert any(asked in url for url in editor.requested), f"never asked for {asked}"
    # The toolbar's error came 0.04 to 0.3 s after ready (measured on the
    # payload before the fix), so read the report only after the wait for
    # what must not come.
    editor.wait_for_nothing()
    assert editor.reported()["errors"] == []
