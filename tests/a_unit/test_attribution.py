"""The attribution says the same thing everywhere it is said.

Four surfaces carry it and three of them are outside Python: the editor's About
panel reads the theme's `attribution` token, the Flatpak's AppStream metadata
is read by software centres, and `build/macos-app.sh` writes a copyright line
into `Info.plist`. `host/about.py` holds the text the host itself shows.

They drifted once already in the other direction: the theme said the right
thing and nothing displayed it, because upstream switches the About panel off
in a desktop build. A copy nobody compares is a copy that goes stale, and this
is the one string in the application that has to be correct rather than merely
present -- it names somebody else's work, says the build is modified, and names
the licence that requires both.

So: compare them, and check each says the three things it has to.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest
from support import repo_root

from libera.host import about

ROOT = repo_root()
THEME = ROOT / "build" / "theme" / "libera" / "meta" / "config.json"
METAINFO = ROOT / "build" / "flatpak" / "eu.liberasuite.Libera.metainfo.xml"
MACOS_APP = ROOT / "build" / "macos-app.sh"


def test_the_theme_and_the_host_say_the_same_thing() -> None:
    """The editor's About panel and Help > About are one sentence, not two."""
    theme = json.loads(THEME.read_text(encoding="utf-8"))
    assert theme["attribution"] == about.ATTRIBUTION


@pytest.mark.parametrize(
    "required",
    ["ONLYOFFICE", "Ascensio System SIA", "Euro-Office", "AGPL"],
)
def test_the_attribution_names_who_and_under_what(required: str) -> None:
    """The original developer, the upstream project, and the licence."""
    assert required in about.ATTRIBUTION


def test_the_attribution_says_the_components_are_modified() -> None:
    """AGPLv3 section 5(a) wants a modified work to say that it is one."""
    assert "modified" in about.ATTRIBUTION


def test_the_attribution_includes_rather_than_is_based_on() -> None:
    """The host is ours; what comes from upstream is the payload.

    "Based on" reads as though the whole application were a derivative of
    theirs, which overstates their claim and understates ours.
    """
    assert "includes components from" in about.ATTRIBUTION
    assert "based on" not in about.ATTRIBUTION.lower()


def test_the_macos_bundle_carries_the_copyright_line() -> None:
    """`Info.plist`'s NSHumanReadableCopyright is what AppKit's About shows."""
    plist = MACOS_APP.read_text(encoding="utf-8")
    assert "NSHumanReadableCopyright" in plist
    for phrase in ("Euro-Office", "ONLYOFFICE", "AGPL"):
        assert phrase in plist, phrase


def test_the_appstream_metadata_attributes_and_licenses() -> None:
    """A software centre shows this before anything is installed."""
    root = ET.parse(METAINFO).getroot()
    assert root.findtext("project_license") == "AGPL-3.0-or-later"
    assert root.findtext("developer/name") == "Abilian SAS"

    described = " ".join(re.sub(r"\s+", " ", (p.text or "")) for p in root.iter("p"))
    for phrase in ("ONLYOFFICE", "Ascensio System SIA", "AGPL", "modified"):
        assert phrase in described, phrase


def test_the_desktop_about_gate_is_patched_out() -> None:
    """Without patch 0007 the panel that shows all of this is display:none.

    Upstream sets `customization.about = false` whenever `isDesktopApp`, on the
    assumption that a native shell provides About instead. Measured on the
    running editor before the patch: `#left-btn-about` and `#about-menu-panel`
    both display:none, and the attribution nowhere in visible text.
    """
    patch = ROOT / "build" / "patches" / "web-apps"
    about_patches = list(patch.glob("*keep-About-reachable*.patch"))
    assert about_patches, f"no About patch in {patch}"

    body = about_patches[0].read_text(encoding="utf-8")
    # Five editors carry the identical gate, so the patch has to touch all five.
    touched = re.findall(
        r"^\+\+\+ b/apps/(\w+)/main/app/controller/Main\.js$", body, re.MULTILINE
    )
    assert sorted(touched) == [
        "documenteditor",
        "pdfeditor",
        "presentationeditor",
        "spreadsheeteditor",
        "visioeditor",
    ]
    assert (
        "-                            this.appOptions.customization.about = false;"
        in body
    )
