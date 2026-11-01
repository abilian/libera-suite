"""The two versions, which move independently on purpose.

The application is the `libera` package; the payload is the editor build it
fetches. A host fix should not force a 120 MB re-download, so the wheel and the
Flatpak bundles are named for the first and the origin's directory for the
second.
"""

from __future__ import annotations

import re
import shutil
from typing import TYPE_CHECKING

import tomllib

from libera.manifest import Manifest
from libera_build.repo import MANIFEST, PAYLOAD_VERSION
from libera_build.report import RefusedError, say

if TYPE_CHECKING:
    from pathlib import Path


def payload_version(root: Path) -> str:
    """The payload version, as the host reads it: with tomllib.

    payload.version is a commented TOML file, not a bare number, and reading
    it whole once printed the file's comment block as the version. A reader
    of its own, splitting lines on `=`, read a trailing comment into it.
    """
    doc = tomllib.loads((root / PAYLOAD_VERSION).read_text(encoding="utf-8"))
    if "version" not in doc:
        msg = f"no version in {root / PAYLOAD_VERSION}"
        raise RefusedError(msg)
    return str(doc["version"])


def app_version(root: Path) -> str:
    doc = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(doc["project"]["version"])


def is_prerelease(version: str) -> bool:
    """Anything but digits and dots: 0.4.0rc1, and a .post or a +local too.

    The rule is install.sh's, which refuses a pointer naming anything else, so
    a release that moved `latest` to one would stop every `curl | sh`. pip
    leaves such a version alone unless asked (`--pre`), and so the pointers
    and the install scripts do too: a pre-release is reached by its own name.
    """
    return not re.fullmatch(r"\d+(\.\d+)*", version)


def stamp_bundled_manifest(root: Path, dist: Path) -> None:
    """The wheel's manifest, from the artifacts about to be installed or bundled.

    The installer prefers the manifest baked into the wheel over the one
    beside the artifacts, deliberately, and src/libera/manifest.json is
    gitignored: on a builder it is whatever an earlier run left there. The
    two builders had drifted in opposite directions, one refusing in the
    sandbox ("manifest is for payload 0.1"), one shipping a wheel with no
    provenance in it; and `lb linux test` on a builder installed against the
    last release's ("manifest is for payload 0.4.1"). Each builder makes its
    own editors.tar.gz, so the one collected here will not do either.
    """
    src = dist / "manifest.json"
    if not src.is_file():
        msg = f"no manifest.json in {dist}"
        raise RefusedError(msg)
    found = Manifest.read(src).payload_version
    want = payload_version(root)
    if found != want:
        msg = (
            f"{src} is for payload {found} and this tree wants {want}.\n"
            "  The application would refuse to load those editors."
        )
        raise RefusedError(msg)
    shutil.copyfile(src, root / MANIFEST)
    say(f"    manifest  payload {found}, from {dist}")
