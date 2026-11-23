"""The release's version, the same for `libera`, `libera-core` and `libera-web`.

They moved independently while the application downloaded its components, so
that a fix to the host did not cost a download. Since 0.7 pip installs them
together, and two numbers only made two ways to get a release wrong: 0.7.0
went out pinning components 0.7.1. So one number, written in six places by
`bump`, and a test holds them equal. `payload_version` and `app_version` both
stay, each read where it lives, for that test and for a deliberate exception
made by hand.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import tomllib

from libera.manifest import Manifest
from libera_build.repo import PAYLOAD_VERSION
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


# Where the version is written, and how, besides `version` in the root
# pyproject.toml: each pattern must match exactly once, or nothing is written.
PLACES = (
    ("src/libera/payload/payload.version", 'version = "{}"'),
    ("components/core/pyproject.toml", 'version = "{}"'),
    ("components/web/pyproject.toml", 'version = "{}"'),
    ("components/web/pyproject.toml", '"libera-core=={}"'),
    ("pyproject.toml", '"libera-core=={}"'),
    ("pyproject.toml", '"libera-web=={}"'),
)


def check_version(version: str) -> None:
    """Refused unless `version` is one a release can have: digits and dots,
    perhaps a pre-release; not a candidate's local label, which PyPI refuses."""
    if not re.fullmatch(r"\d+(\.\d+)*([a-z]+\d+)?", version):
        msg = f"not a version a release can have: {version}"
        raise RefusedError(msg)


def bump(root: Path, version: str) -> int:
    """Write `version` everywhere the release's version is, checking every
    place first: a bump that stopped half way would be a tree no test passes."""
    check_version(version)
    old_app, old_payload = app_version(root), payload_version(root)
    places = [("pyproject.toml", 'version = "{}"', old_app)]
    places += [(path, pattern, old_payload) for path, pattern in PLACES]
    texts = {path: (root / path).read_text(encoding="utf-8") for path, _, _ in places}
    for path, pattern, old in places:
        found = texts[path].count(pattern.format(old))
        # The root pyproject's `version = ` is the project's, the first line
        # that says it; nothing else there is written that way.
        if found != 1:
            msg = f"{path}: {pattern.format(old)} is there {found} times, not once"
            raise RefusedError(msg)
    for path, pattern, old in places:
        texts[path] = texts[path].replace(pattern.format(old), pattern.format(version))
    for path, text in texts.items():
        (root / path).write_text(text, encoding="utf-8")
    say(f"    {old_app} (payload {old_payload}) -> {version}, in {len(texts)} files")
    return 0


def is_prerelease(version: str) -> bool:
    """Anything but digits and dots: 0.4.0rc1, and a .post or a +local too.

    The rule is install.sh's, which refuses a pointer naming anything else, so
    a release that moved `latest` to one would stop every `curl | sh`. pip
    leaves such a version alone unless asked (`--pre`), and so the pointers
    and the install scripts do too: a pre-release is reached by its own name.
    """
    return not re.fullmatch(r"\d+(\.\d+)*", version)


def check_dist(root: Path, dist: Path) -> str:
    """The payload version of the artifacts in `dist`, refused unless it is
    the one this tree wants."""
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
    return found
