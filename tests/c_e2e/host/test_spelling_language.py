"""The document's language changed as soon as it opens.

The editor asks for every paragraph's words to be checked as soon as it has
laid them out. A change of language asks again, in the new one, but the
answer to the first request still arrived, and was applied: French text set
to French straight away stayed underlined as English (sdkjs 0019, after
ElixirOffice 0.9.1, who saw it with Markdown documents). Measured in the
picture, as a user sees it: the editor's own names are minified.
"""

from __future__ import annotations

import time

from support.render import red_pixels

FRENCH = "".join(
    f"Le chat dort sur la chaise près de la fenêtre, et nous avons mangé {i}.\n\n"
    for i in range(12)
)
FRENCH_LCID = 1036


def red_after(editor, tmp_path, settled) -> int:
    """The red in the window once `settled` holds, or after 15 seconds."""
    deadline = time.monotonic() + 15
    while True:
        path = tmp_path / f"{time.monotonic_ns()}.png"
        editor.page.screenshot(path=str(path))
        red = red_pixels(str(path))
        if settled(red) or time.monotonic() > deadline:
            return red
        time.sleep(0.5)


def opened(editor_with, tmp_path):
    document = tmp_path / "french.md"
    document.write_text(FRENCH, encoding="utf-8")
    return editor_with([], document)


def test_french_text_is_underlined_in_english(editor_with, tmp_path):
    """The control: the squiggles the test below looks for are there to see."""
    editor = opened(editor_with, tmp_path)

    assert red_after(editor, tmp_path, lambda red: red > 0) > 0


def test_a_language_set_on_opening_is_the_one_checked(editor_with, tmp_path):
    editor = opened(editor_with, tmp_path)

    editor.frame.evaluate(f"() => Asc.editor.asc_setDefaultLanguage({FRENCH_LCID})")

    time.sleep(2)  # the answers to the first requests come back meanwhile
    assert red_after(editor, tmp_path, lambda red: red == 0) == 0
