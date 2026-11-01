"""A window opened with an index of the machine's fonts loads the editor from
it: its font list, its pictures, and each font by number.

The index here is the payload's own fonts', so the editor lays out as it
always does and the test takes no longer; what is checked is where each
request went. Each window has its own list, so each of
those requests has to name its window's session: RequireJS loads AllFonts.js
from a path in the page's config, which names none, and the bridge adds it.
"""

from __future__ import annotations

import re
import urllib.parse

from libera import payload as payload_mod
from libera.payload import fonts


def sessions_asked_with(requested: list[str], pattern: str) -> set[str]:
    """The session each matching request named, "" for none."""
    return {
        urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("session", [""])[0]
        for url in requested
        if re.search(pattern, url)
    }


def test_the_editor_loads_its_windows_own_font_list(editor_with):
    index = fonts.get_shipped(payload_mod.resolve())
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
