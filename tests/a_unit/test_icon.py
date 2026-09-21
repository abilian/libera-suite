"""The application icon, which three toolchains read and one of them is strict.

`src/libera/icon.svg` is the only copy of the mark in the repository.
`build/macos-icon.py` rasterises it into `Libera.icns`, `build/flatpak.sh`
copies it beside the Flatpak manifest to be exported as the desktop icon, and
the host loads it at startup to set the Dock icon over the interpreter's.

Sharing a file between three readers means satisfying the strictest, and the
strictest is not the one you hear from first. A comment written in house style,
with `--` in it, is not well-formed XML: librsvg does not care and built a
perfectly good Flatpak, while `NSImage` returned nil and the `.icns` step died
saying only that it could not read the file. Neither `check-xml` in
`.pre-commit-config.yaml` nor any linter sees it -- pre-commit's `identify`
types `.svg` as `svg`, not `xml`.

So parse it here, where every platform runs.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from importlib import resources

ICON = resources.files("libera") / "icon.svg"


def test_the_icon_ships_with_the_package():
    """Not just in the repository: the Dock icon is read from the install.

    `libera` run from a virtualenv wears the interpreter's identity, so the
    host sets the icon itself at startup -- which it can only do if the wheel
    carried the file. build/flatpak.sh installs that wheel into the sandbox.
    """
    assert ICON.is_file(), f"no icon at {ICON}"


def test_the_icon_is_well_formed_xml():
    """Strict enough for NSImage, which is the one that refuses without saying."""
    ET.fromstring(ICON.read_text(encoding="utf-8"))


def test_the_icon_declares_itself_on_the_first_line():
    """flatpak-builder validates every exported icon through gdk-pixbuf.

    With anything ahead of the declaration -- a comment, a blank line -- it
    refuses the file with "not a valid icon: Format not recognized", at the
    very end of an otherwise clean build and naming nothing useful.
    """
    first = ICON.read_text(encoding="utf-8").split("\n", 1)[0]
    assert first.startswith("<?xml "), f"first line is {first!r}"
