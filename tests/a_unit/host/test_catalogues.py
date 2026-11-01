"""Our own strings, in every language we translate them into.

Each catalogue is keyed by the English, which is what a missing entry shows:
nothing fails at run time, so this is where a string added in English and
nowhere else is caught, and one left behind after its English changed.
"""

from __future__ import annotations

import ast
import json
import re

import pytest
from support import repo_root
from webview.localization import original_localization

from libera.host import apps, language, saving

HOST = repo_root() / "src/libera/host"
# Our pages: `{{English}}` in the start window's markup, `tr("English")` in
# its script and in the bridge's.
PAGES = ("server/start-window.html", "server/bridge-desktop.js")
MARKED = re.compile(r"\{\{(.+?)\}\}")
TR = re.compile(r'\btr\(\s*("(?:[^"\\]|\\.)*")')
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def find_literal_keys() -> set[str]:
    """Every `language.translate("...")` the host makes with a literal."""
    found = set()
    for path in HOST.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "translate"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                found.add(node.args[0].value)
    return found


def find_page_keys() -> set[str]:
    found = set()
    for name in PAGES:
        text = (HOST / name).read_text(encoding="utf-8")
        found |= set(MARKED.findall(text))
        found |= {json.loads(literal) for literal in TR.findall(text)}
    return found


def find_data_keys() -> set[str]:
    """What is translated where it is shown rather than where it is written:
    the kinds of document, the save panel's formats, and pywebview's own."""
    formats = [label for app in apps.ALL for label, _ in app.save_formats]
    formats += [label for label, _ in saving.PRINT_FORMATS]
    return (
        {app.noun for app in apps.ALL}
        | set(formats)
        | set(original_localization.values())
    )


def test_the_keys_are_found() -> None:
    """A scan that finds nothing passes every catalogue."""
    assert "Save As…" in find_literal_keys()
    assert "Open a document…" in find_page_keys()
    assert "Create New" in find_page_keys()
    assert "Spreadsheet" in find_data_keys()


@pytest.mark.parametrize("lang", language.TRANSLATED)
def test_each_catalogue_has_every_string_and_no_other(lang: str) -> None:
    catalogue = language.read_catalogue(lang)
    used = find_literal_keys() | find_page_keys() | find_data_keys()
    assert sorted(used - catalogue.keys()) == [], "missing"
    assert sorted(catalogue.keys() - used) == [], "no longer used"


@pytest.mark.parametrize("lang", language.TRANSLATED)
def test_a_translation_fills_in_what_its_english_does(lang: str) -> None:
    for english, text in language.read_catalogue(lang).items():
        assert text.strip(), english
        assert set(PLACEHOLDER.findall(text)) == set(PLACEHOLDER.findall(english)), (
            english
        )


def test_english_needs_no_catalogue(monkeypatch) -> None:
    monkeypatch.setattr(language, "get_language", lambda: "en-FR")
    assert language.translate("Save changes to “{name}” before closing?", name="a") == (
        "Save changes to “a” before closing?"
    )


def test_a_translated_language_is_looked_up(monkeypatch) -> None:
    monkeypatch.setattr(language, "get_language", lambda: "fr-CA")
    assert language.get_interface_language() == "fr"
    assert language.translate("Save") == language.read_catalogue("fr")["Save"]
