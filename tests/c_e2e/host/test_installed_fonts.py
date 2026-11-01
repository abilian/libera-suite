"""A window opened with an index of the machine's fonts loads the editor from
it: its font list, its pictures, and each font by number.

The index here is built from the payload's own fonts, without allfontsgen, so
the editor lays out as it always does and the test takes no longer; what is
checked is where each request went. Each window has its own list, so each of
those requests has to name its window's session: RequireJS loads AllFonts.js
from a path in the page's config, which names none, and the bridge adds it.
"""

from __future__ import annotations

import re
import shutil
import urllib.parse
from typing import TYPE_CHECKING

from libera import payload as payload_mod
from libera.payload import fonts

if TYPE_CHECKING:
    import pathlib


def make_index_of_the_payloads_fonts(into: pathlib.Path) -> pathlib.Path:
    """What fonts.build writes, made from what generate wrote."""
    layout = payload_mod.resolve()
    into.mkdir()
    shutil.copy(layout.all_fonts, into / "AllFonts.js")
    shutil.copy(layout.sdkjs_common / "font_selection.bin", into)
    shutil.copytree(layout.font_thumbnails, into / fonts.THUMBNAILS)
    fonts.write_web_all_fonts(into / "AllFonts.js", into / fonts.WEB_ALL_FONTS)
    return into


def sessions_asked_with(requested: list[str], pattern: str) -> set[str]:
    """The session each matching request named, "" for none."""
    return {
        urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("session", [""])[0]
        for url in requested
        if re.search(pattern, url)
    }


def test_the_editor_loads_its_windows_own_font_list(editor_with, tmp_path):
    index = make_index_of_the_payloads_fonts(tmp_path / "index")
    editor = editor_with([], fonts=index)
    session = "0"  # the work folder's name, as editor_with makes it

    assert sessions_asked_with(editor.requested, r"/sdkjs/common/AllFonts\.js") == {
        session
    }
    assert sessions_asked_with(
        editor.requested, r"/sdkjs/common/Images/fonts_thumbnail"
    ) == {session}
    # By number, as the index's list names them: the payload's names them
    # 000, 001...
    numbers = [
        url.split("/__host__/fonts/")[1].split("?")[0]
        for url in editor.requested
        if "/__host__/fonts/" in url
    ]
    assert numbers
    assert all(str(int(n)) == n for n in numbers)
    # The page gives up on other requests: the help's Contents.json, at times.
    assert [f for f in editor.failed if re.search(r"fonts|AllFonts", f)] == []
