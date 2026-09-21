"""Every AscDesktopEditor member the payload calls, against what we implement.

sdkjs feature-checks most of them and calls a handful outright. An outright
call to a method we do not have is a TypeError in the middle of whatever the
user was doing: `Show from the beginning` was one, and ending a slideshow was
another.

The classification is computed here, not written down. The first version of
this test carried a hand-written list of "checked, it is guarded" and eight of
its fourteen entries were wrong -- including endReporter, which every
slideshow calls on the way out. A list of judgements is only as good as the
judgements, and these were made by reading a heuristic instead of the source.

A call is guarded when the same member is named without being called somewhere
just before it -- `X && X()`, `if (X) { ... X() }`. That is what a feature
check looks like, and it is the same test in the minified and unminified
bundles.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from support import repo_root

if TYPE_CHECKING:
    from pathlib import Path

BRIDGE = repo_root() / "src/libera/host/server/bridge-desktop.js"

# How far back to look for the check. Long enough for `if (A && A["X"]) { let
# y = A["X"](...) }` in minified code, short enough not to reach the previous
# statement's mention of something else.
WINDOW = 200


def payload_scripts(root: Path) -> list[Path]:
    files: list[Path] = []
    for sub in (
        "sdkjs/word",
        "sdkjs/cell",
        "sdkjs/slide",
        "sdkjs/visio",
        "sdkjs/common",
    ):
        files += list((root / sub).rglob("*.js"))
    for app in (
        "documenteditor",
        "spreadsheeteditor",
        "presentationeditor",
        "visioeditor",
    ):
        files += list((root / "web-apps/apps" / app / "main").glob("*.js"))
    return files


def unguarded_calls(root: Path) -> dict[str, str]:
    """Members called with no feature check, and one call site for each."""
    found: dict[str, str] = {}
    for f in payload_scripts(root):
        text = f.read_text(errors="replace")
        for m in re.finditer(r'AscDesktopEditor"\]\["([A-Za-z_]\w*)"\]\(', text):
            name = m.group(1)
            if name in found:
                continue
            before = text[max(0, m.start() - WINDOW) : m.start()]
            # A bare mention of the same member -- not followed by "(" -- is
            # the editor asking whether we have it before using it.
            if re.search(rf'\["{re.escape(name)}"\](?!\s*\()', before):
                continue
            found[name] = f"{f.name}: ...{before[-90:]}{m.group(0)}"
    return found


@pytest.fixture(scope="module")
def implemented() -> set[str]:
    """What the bridge answers to, by its own object keys."""
    return set(re.findall(r"^    ([A-Za-z_]\w*):", BRIDGE.read_text(), re.MULTILINE))


def test_nothing_the_payload_calls_unguarded_is_missing(live_payload, implemented):
    """The whole test. Absence here is an exception, not a disabled feature."""
    missing = {
        name: where
        for name, where in unguarded_calls(live_payload).items()
        if name not in implemented
    }
    assert not missing, (
        "called with no feature check and not implemented:\n"
        + "\n".join(f"  {name}\n    {where}" for name, where in sorted(missing.items()))
    )


def test_the_ones_that_have_already_cost_us_are_still_there(implemented):
    """Each of these was a frozen editor, found by somebody using the app."""
    for name in ("SetFullscreen", "endReporter", "AddAudio", "AddVideo", "MediaStart"):
        assert name in implemented, f"{name} is called with no feature check"


def test_the_classification_recognises_a_feature_check(live_payload):
    """If the guard test stopped working, everything would look unguarded.

    These are checked in the payload with `A["X"] && A["X"](...)` right at the
    call, so finding them here would mean the rule had gone wrong.

    The rule is deliberately short-sighted the other way: a guard further from
    its call than WINDOW reads as unguarded, and we implement a no-op we did
    not strictly need. That is the cheap mistake -- onFileLockedClose is one --
    and the expensive one is a frozen editor.
    """
    unguarded = unguarded_calls(live_payload)
    for name in ("SetLocalRestrictions", "CallMediaPlayerCommand"):
        assert name not in unguarded, f"{name} is guarded in the payload"
