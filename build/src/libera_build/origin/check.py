"""Reading the origin back as a stranger: no token, no configuration, the URL
the wheel will build, every artifact sized and hashed against a manifest.

Hashing is streamed, so this verifies a quarter of a gigabyte and writes
nothing to disk.
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING

from libera.manifest import Manifest
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from pathlib import Path

# The project, whose "version" is its newest release; and one version of it.
PYPI = "https://pypi.org/pypi/libera/json"
PYPI_VERSION = "https://pypi.org/pypi/libera/{version}/json"


@dataclass(frozen=True)
class Wanted:
    name: str
    size: (
        int | None
    )  # None for manifest.json, which is what the others are checked against
    sha256: str | None


def wanted(manifest: Manifest) -> list[Wanted]:
    """Every artifact, then manifest.json itself: not one of its own artifacts,
    and only --trust-manifest reads it from the origin, but a mirror needs it,
    so its absence is worth knowing."""
    found = [Wanted(a.name, a.size, a.sha256) for a in manifest.artifacts]
    return [*found, Wanted("manifest.json", None, None)]


def verdict(want: Wanted, length: int, digest: str | None) -> tuple[bool, str]:
    """Whether what the origin served is what the manifest names, and the note.

    Says what was compared, not what the run was capable of comparing:
    manifest.json carries no size or hash of its own, so it is only "present",
    and printing "size and sha256 ok" beside it once claimed two checks that had
    not happened -- the exact shape this exists to catch.
    """
    problems = []
    if want.size is not None and length != want.size:
        problems.append(f"{length} bytes, the manifest says {want.size}")
    if digest is not None and want.sha256 is not None and digest != want.sha256:
        problems.append(f"sha256 {digest[:12]}…, the manifest says {want.sha256[:12]}…")
    if problems:
        return False, "; ".join(problems)
    if want.sha256 is None:
        return True, "present"
    return True, "size ok" if digest is None else "size and sha256 ok"


def read_back(url: str, *, quick: bool) -> tuple[int, str | None]:
    """The length a URL serves, and its streamed SHA-256 unless only sizes
    were asked for (a HEAD, then)."""
    request = urllib.request.Request(url, method="HEAD" if quick else "GET")
    with urllib.request.urlopen(request, timeout=120) as r:
        if quick:
            return int(r.headers.get("Content-Length") or 0), None
        h = hashlib.sha256()
        read = 0
        for chunk in iter(lambda: r.read(1 << 20), b""):
            h.update(chunk)
            read += len(chunk)
        return read, h.hexdigest()


def check(base: str, manifest: Manifest, *, quick: bool) -> None:
    """Every artifact of `manifest` under `base`, as a stranger reads it.

    The directory comes out of the manifest being checked rather than out of
    the tree: a wheel naming payload 0.1 is checked against 0.1/ even when this
    checkout has moved on. A check that named the tree's directory and read
    another once passed against a 404.
    """
    step(f"reading {base}/ as a stranger")
    wants = wanted(manifest)
    bad = 0
    for want in wants:
        try:
            length, digest = read_back(f"{base}/{want.name}", quick=quick)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            say(f"    MISSING  {want.name:28} {getattr(e, 'reason', e)}")
            bad += 1
            continue
        ok, note = verdict(want, length, digest)
        say(f"    {'ok' if ok else 'WRONG':8} {want.name:28} {note}")
        bad += not ok
    if bad:
        msg = f"{bad} of {len(wants)} are not what the wheel will ask for."
        raise RefusedError(msg)
    hashed = sum(1 for w in wants if w.sha256 is not None)
    say(f"\n    all {hashed} artifacts match the manifest the wheel ships,")
    say("    and manifest.json is there beside them.")
    if quick:
        say("    sizes only -- drop --quick to hash the bytes.")
    else:
        say("\n    The last word belongs to the application: on a machine with no")
        say("    payload, libera --payload-install")


def wheel_manifest(source: str | Path, version: str) -> Manifest:
    """The manifest a *published wheel* carries, which is what decides what
    somebody else's install accepts. `pypi` for `version`'s unyanked wheel
    there: not PyPI's newest, which is its newest *release*, so that after a
    pre-release went up it named the release before.

    `libera` 0.1.0 went to PyPI naming a payload that was rebuilt two days
    later, and no command compared the two: the check read the manifest in this
    tree, which was correct, about a wheel that was not.
    """
    wheel: str | Path | io.BytesIO = source
    if str(source) == "pypi":
        url = PYPI_VERSION.format(version=version)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != HTTPStatus.NOT_FOUND:
                raise
            msg = f"libera {version} is not on PyPI"
            raise RefusedError(msg) from e
        wheels = [
            f
            for f in data["urls"]
            if f["filename"].endswith(".whl") and not f["yanked"]
        ]
        if not wheels:
            msg = f"libera {data['info']['version']} has no unyanked wheel on PyPI"
            raise RefusedError(msg)
        say(f"    {wheels[0]['filename']}, as PyPI serves it")
        with urllib.request.urlopen(wheels[0]["url"], timeout=120) as r:
            wheel = io.BytesIO(r.read())
    with zipfile.ZipFile(wheel) as z:
        found = [n for n in z.namelist() if n.endswith("libera/manifest.json")]
        if not found:
            # The other half of the same failure: a wheel with no manifest
            # verifies nothing and refuses every download.
            msg = "that wheel ships no libera/manifest.json, so it can verify nothing"
            raise RefusedError(msg)
        return Manifest.from_dict(json.loads(z.read(found[0])))
