"""The scroll wheel scrolls a spreadsheet.

On a Mac sdkjs listens for the legacy `mousewheel` event and web-apps for
`wheel`, on the same element in the spreadsheet, and a browser fires an
element's `mousewheel` listeners only when it has no `wheel` listener. Words
and Slides scrolled; Tables did not move. The bridge registers `mousewheel` as
`wheel` there. Chromium on a Mac reports a Mac user agent, so this sees the
bug where it lives; elsewhere sdkjs asks for `wheel` itself and it passes
either way.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from libera import payload as payload_mod
from libera.host import apps

if TYPE_CHECKING:
    import pathlib

FIRST_ROW = "() => Asc.editor.wb.getWorksheet().visibleRange.r1"


def test_the_wheel_scrolls_a_spreadsheet(editor_with, tmp_path: pathlib.Path):
    sheet = tmp_path / "blank.xlsx"
    shutil.copyfile(payload_mod.resolve().root / "empty" / apps.TABLES.blank, sheet)
    editor = editor_with([], sheet)
    editor.page.wait_for_function(
        "() => document.querySelector('iframe').contentWindow.Asc.editor.wb"
    )
    box = editor.page.locator("iframe").first.bounding_box()
    assert box is not None
    editor.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert editor.frame.evaluate(FIRST_ROW) == 0

    for _ in range(3):
        editor.page.mouse.wheel(0, 100)
        editor.page.wait_for_timeout(300)

    assert editor.frame.evaluate(FIRST_ROW) > 0
