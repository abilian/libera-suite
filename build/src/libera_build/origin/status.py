"""status: where a release has got to, measured, and the next command.

A release spans days, several machines and hours of unattended building, so
the question actually asked is "where was I". Remembering is how 0.1.0
shipped against a payload rebuilt underneath it. This measures instead: the
tree, the release's files on this disk, and PyPI. Read-only: no token,
nothing written.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from libera_build import repo, versions
from libera_build.artifacts import bundle_name, installer_name, run_bundles, run_pypi
from libera_build.report import say, step

if TYPE_CHECKING:
    from pathlib import Path

PYPI = "https://pypi.org/pypi/libera/json"


def status(root: Path) -> int:
    """`lb release status`: read-only, so it always succeeds."""
    version = versions.app_version(root)
    step("version")
    say(f"    {version}  (pyproject.toml; payload {versions.payload_version(root)})")

    step("this tree")
    tag = repo.git(root, "tag", "--points-at", "HEAD")
    dirty = len(repo.dirty(root))
    say(f"    commit       {repo.head(root)[:7]}  ({dirty} file(s) modified)")
    say(f"    tag          {tag.splitlines()[0] if tag.strip() else 'none on HEAD'}")

    step(f"the release's files here, for {version}")
    wheels = run_pypi(root)
    bundles = run_bundles(root)
    files = sorted(wheels.glob("*")) if wheels.is_dir() else []
    files += [
        f
        for f in (
            bundles / bundle_name(version, "amd64"),
            bundles / installer_name(version),
        )
        if f.is_file()
    ]
    for f in files:
        say(f"    {f.name:56} {f.stat().st_size / 1e6:6.1f} MB")
    if not files:
        say("    none yet: lb release check")

    step("PyPI")
    say(f"    {pypi_summary()}")
    return 0


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
