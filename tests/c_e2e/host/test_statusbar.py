"""The status bar's page indicator and zoom work, read where a user reads them.

No other test looked at the status bar: when the second wave of experiments
replaced the word processor's zoom group with a component (E6), the whole
browser tier passed twice with it broken, once drawing nothing at all. These
read the bar by its elements' ids, web-apps' own; a part that replaces them
keeps those ids, or changes these tests with it. Broken on purpose (a click on
zoom in stopped before its handler), the zoom test fails.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import expect
from support.blank import with_body
from support.documents import blank_of

from libera.host import apps

if TYPE_CHECKING:
    from pathlib import Path

    from c_e2e.conftest import Editor

TWO_PAGES = (
    "<w:p><w:r><w:t>One</w:t></w:r></w:p>"
    '<w:p><w:r><w:br w:type="page"/><w:t>Two</w:t></w:r></w:p>'
)


def percent(editor: Editor, label: str) -> int:
    """The zoom the bar shows, as a number: "Zoom 110%" is 110."""
    text = editor.frame.locator(label).inner_text()
    found = re.search(r"(\d+)\s*%", text)
    assert found, f"no percentage in {text!r}"
    return int(found[1])


def zoomed(editor: Editor, button: str, label: str) -> tuple[int, int]:
    """The percentage before and after a click on `button`."""
    before = percent(editor, label)
    editor.frame.click(button)
    expect(editor.frame.locator(label)).not_to_have_text(re.compile(rf"\b{before}%"))
    return before, percent(editor, label)


def test_the_word_processor_counts_its_pages(editor_with, tmp_path: Path):
    editor = editor_with([], with_body(tmp_path, TWO_PAGES))
    expect(editor.frame.locator("#label-pages")).to_have_text(
        re.compile(r"^\s*Page 1 of 2\s*$")
    )


def test_zoom_in_and_out_move_the_percentage(editor_with):
    editor = editor_with([])
    before, after = zoomed(editor, "#btn-zoom-up", "#label-zoom")
    assert after > before
    _, back = zoomed(editor, "#btn-zoom-down", "#label-zoom")
    assert back < after


def test_fit_to_page_is_pressed_and_a_second_click_releases_it(editor_with):
    editor = editor_with([])
    fit = editor.frame.locator("#btn-zoom-topage")
    fit.click()
    expect(fit).to_have_class(re.compile(r"\bactive\b"))
    fit.click()
    expect(fit).not_to_have_class(re.compile(r"\bactive\b"))


def test_the_presentation_editor_counts_its_slides_and_zooms(
    editor_with, tmp_path: Path
):
    editor = editor_with([], blank_of(apps.SLIDES, tmp_path / "blank.pptx"))
    expect(editor.frame.locator("#status-label-pages")).to_have_text(
        re.compile(r"^\s*Slide 1 of 1\s*$")
    )
    before, after = zoomed(editor, "#btn-zoom-up", "#status-label-zoom")
    assert after > before
