"""status: where a release has got to, measured, and the next command.

The runbook in docs/src/develop/release.md, answered instead of read. A release
spans days, several machines and hours of unattended building, so the question
actually asked is "where was I". Remembering is how 0.1.0 shipped against a
payload rebuilt underneath it. This measures instead: the tree, the artifacts
on this disk, the origin and PyPI. Read-only: no token, nothing written.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from libera.manifest import Manifest
from libera_build import repo, versions
from libera_build.origin.check import PYPI
from libera_build.report import say, step

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.origin.place import Origin

EXPECTED = (
    "core-macos-arm64",
    "core-linux-x86_64",
    "core-linux-arm64",
    "core-windows-x86_64",
    "editors",
    "fonts-core",
)


def next_steps(missing: list[str]) -> list[str]:
    """What to run next, one line per command rather than per artifact: the Mac
    core and the shared pair all come out of the same `payload dist`."""
    if not missing:
        return [
            "every core is here. The rest, in order:",
            "  lb release collect      # restamps the manifest over all six",
            "  make build              # the wheel, after the manifest",
            "  make verify",
            "  CDN_TOKEN=... lb release push && lb release check",
            "  make publish && lb release check --wheel pypi",
        ]
    lines = [f"not here yet: {' '.join(missing)}"]
    remote = {"core-linux-x86_64", "core-linux-arm64", "core-windows-x86_64"}
    if any(m not in remote for m in missing):
        lines.append("  here:              lb payload dist")
    if "core-linux-x86_64" in missing:
        lines.append("  on the x86_64 box: lb payload container")
    if "core-linux-arm64" in missing:
        lines.append("  on the arm64 box:  lb payload container --arch arm64")
    if "core-windows-x86_64" in missing:
        lines.append("  on Windows:        lb payload all")
    lines.append("then:                lb release collect")
    return lines


def reachable(url: str) -> bool:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, method="HEAD"), timeout=30
        ):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def status(root: Path, origin: Origin, dist: Path) -> None:
    step("versions")
    say(f"    application   {versions.app_version(root):<8} (pyproject.toml)")
    say(f"    payload       {origin.version:<8} (src/libera/payload/payload.version)")

    step("this tree")
    _, tag = repo.git(root, "tag", "--points-at", "HEAD")
    dirty = len(repo.dirty(root))
    say(f"    commit       {repo.head(root)[:7]}  ({dirty} file(s) modified)")
    say(f"    tag          {tag.splitlines()[0] if tag.strip() else 'none on HEAD'}")

    step(f"artifacts here, for payload {origin.version}")
    missing = []
    for name in EXPECTED:
        f = dist / f"{name}.tar.gz"
        if f.is_file():
            say(f"    {f.name:26} {f.stat().st_size / 1e6:6.1f} MB")
        else:
            say(f"    {f.name:26} MISSING")
            missing.append(name)

    step("the manifest in this tree")
    stamped = root / repo.MANIFEST
    if stamped.is_file():
        found = Manifest.read(stamped)
        known = repo.git(root, "cat-file", "-t", found.commit)[0] == 0
        say(f"    stamped for payload {found.payload_version}, built {found.built}")
        say(
            f"    names commit {found.commit[:9]}"
            + ("" if known else "  -- WHICH THIS REPOSITORY DOES NOT HAVE")
        )
        if found.dirty:
            say("    stamped from a dirty tree, so it names no source anyone can check")
        if found.payload_version != origin.version:
            say(f"    DISAGREES with this tree, which wants payload {origin.version}")
    else:
        say("    none stamped")

    step("the origin, and PyPI")
    serving = reachable(f"{origin.base}/manifest.json")
    say(f"    origin       {origin.base}/  {'serving' if serving else 'NOT THERE'}")
    say(f"    PyPI         {pypi_summary()}")

    step("next")
    for line in next_steps(missing):
        say(f"    {line}")


def pypi_summary() -> str:
    try:
        with urllib.request.urlopen(PYPI, timeout=30) as r:
            d = json.load(r)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return f"could not ask: {e}"
    yanked = sorted(
        v for v, fs in d["releases"].items() if fs and all(f["yanked"] for f in fs)
    )
    live = sorted(v for v in d["releases"] if v not in yanked)
    line = f"latest {d['info']['version']}; published {', '.join(live)}"
    return line + (f"; yanked {', '.join(yanked)}" if yanked else "")
