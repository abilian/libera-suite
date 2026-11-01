"""Each editor loads in every language it has a locale for.

In French, Italian, Spanish and Portuguese, Words used to load with its toolbar
greyed out and never take an edit: a string Euro-Office added to en.json alone
was undefined, and the toolbar threw while building itself. The page still
reached "ready", so readiness says nothing here; the error it threw does.
Euro-Office adds strings without translating them, so every locale it ships
is loaded, not only the ones our own catalogues cover.
"""

from __future__ import annotations

import os
import shutil

import pytest

from libera import payload as payload_mod
from libera.host import language

# Every locale file the editors ship but English, named as the files are: the
# editor asks for `fr.json`, and for the four-letter `pt-pt`, `zh-tw` and
# `sr-cyrl` by their full name. Collection comes before the payload is
# found, so the list is written out, and the test below holds it to the
# payload's.
LOCALES = [
    "ar", "az", "be", "bg", "ca", "cs", "da", "de", "el", "es", "eu", "fi",
    "fr", "gl", "he", "hu", "hy", "id", "it", "ja", "ko", "lo", "lv", "ms",
    "nl", "no", "pl", "pt", "pt-pt", "ro", "ru", "si", "sk", "sl", "sq", "sr",
    "sr-cyrl", "sv", "tr", "uk", "ur", "vi", "zh", "zh-tw",
]  # fmt: skip
# What `make test` loads: the languages with a catalogue of ours, Dutch, which
# is next, one right to left and two of the four-letter names. `make verify`
# loads them all, which takes about 9 minutes more.
SAMPLE = ["ar", "de", "es", "fr", "it", "nl", "pt-pt", "zh-tw"]
LOADED = LOCALES if os.environ.get("LIBERA_ALL_LOCALES") else SAMPLE
EDITORS = ["documenteditor", "spreadsheeteditor", "presentationeditor"]


@pytest.mark.parametrize("editor", EDITORS)
def test_the_list_is_the_locales_the_payload_ships(editor):
    folder = payload_mod.resolve().root / "web-apps/apps" / editor / "main/locale"
    assert sorted(f.stem for f in folder.glob("*.json") if f.stem != "en") == LOCALES


def test_every_language_the_editors_speak_has_a_catalogue_of_ours():
    """Our menus, start window and dialogs in each of the editors' languages."""
    assert set(LOCALES) <= set(language.TRANSLATED)


@pytest.mark.parametrize("ext", ["docx", "xlsx", "pptx"])
@pytest.mark.parametrize("tag", LOADED)
def test_the_editor_loads_in_the_language_without_an_error(
    editor_with, tmp_path, monkeypatch, tag, ext
):
    document = tmp_path / f"blank.{ext}"
    shutil.copyfile(payload_mod.resolve().root / "empty" / f"new.{ext}", document)
    monkeypatch.setattr(language, "get_language", lambda: tag)

    editor = editor_with([], document=document)

    # The tag is the file's own name, which the editor asks for as it is.
    asked = f"/main/locale/{tag}.json"
    assert any(asked in url for url in editor.requested), f"never asked for {asked}"
    # The toolbar's error came 0.04 to 0.3 s after ready (measured on the
    # payload before the fix), so read the report only after the wait for
    # what must not come.
    editor.wait_for_nothing()
    assert editor.reported()["errors"] == []
