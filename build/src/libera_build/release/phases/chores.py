"""tap and docs: what a release moves outside this repository, once PyPI has it.

Both were steps of the runbook done by hand after `publish`, and both lagged:
the Homebrew formula is in a repository of its own (abilian/homebrew-tap),
whose generator reads the release from PyPI, and users get nothing until it is
pushed; the documentation site is its own deployment (docs/hop3.toml), which
carries the release's news and its install page. Neither runs for a
pre-release, which moves no pointer.

Each checks what it did by what users get, not by an exit status: the formula
names the version, and the site serves the stamp of this checkout's docs/.
"""

from __future__ import annotations

import json
import shutil
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

import tomllib

from libera_build import versions
from libera_build.process import capture, run_here
from libera_build.report import problems, say, step

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.release.context import Context

FORMULA = "libera"
# What `make publish` in docs/ deploys, and docs/scripts/build_stamp.py writes
# into it: the last commit that touched docs/.
DOCS_STAMP = "https://docs.liberasuite.eu/build.json"
DEPLOYED_SECONDS = 120


def tap(ctx: Context) -> None:
    """The formula moved to this release by the tap's own generator, which
    reads it from PyPI (`make update`, with brew's style check and audit),
    then committed and pushed to the branch brew reads."""
    app = versions.app_version(ctx.root)
    if versions.is_prerelease(app):
        say(f"    {app} is a pre-release: the tap stays on the last release")
        return
    step(f"the Homebrew formula, to libera {app}")
    run_here(["make", "update", f"FORMULA={FORMULA}"], "tap", cwd=ctx.tap)
    problems(formula_problems(ctx.tap, app), "nothing was committed to the tap.")
    run_here(["git", "commit", "-q", "-am", f"libera {app}"], "tap", cwd=ctx.tap)
    run_here(["git", "push", "-q"], "tap", cwd=ctx.tap)
    say(f"    brew upgrade {FORMULA} now installs {app}")


def formula_problems(tap_dir: Path, app: str) -> list[str]:
    """Why the formula in `tap_dir` is not libera `app`, if it is not: the
    generator's record of the version, and the sdist the formula fetches."""
    with (tap_dir / "formulae.toml").open("rb") as f:
        recorded = tomllib.load(f).get(FORMULA, {}).get("version")
    found = []
    if recorded != app:
        found.append(f"formulae.toml says {FORMULA} {recorded}, not {app}")
    rb = (tap_dir / "Formula" / f"{FORMULA}.rb").read_text(encoding="utf-8")
    if f"/{FORMULA}-{app}.tar.gz" not in rb:
        found.append(f"Formula/{FORMULA}.rb does not fetch {FORMULA}-{app}.tar.gz")
    return found


def tap_problems(tap_dir: Path) -> list[str]:
    """Why the tap cannot be updated, asked before anything is published: a
    change of someone's in it would be committed with the formula."""
    if not (tap_dir / "formulae.toml").is_file():
        return [f"no Homebrew tap at {tap_dir}: clone abilian/homebrew-tap, or --tap"]
    status, out = capture(["git", "status", "--porcelain"], cwd=tap_dir)
    if status != 0 or out.strip():
        return [f"the tap at {tap_dir} has uncommitted changes: commit or stash them"]
    status, _ = capture(["git", "rev-parse", "@{upstream}"], cwd=tap_dir)
    if status != 0:
        return [f"the tap's branch at {tap_dir} has no upstream to push to"]
    return []


def docs(ctx: Context) -> None:
    """The documentation site built and deployed (docs/Makefile's publish,
    through hop3), then read back: the site must serve the stamp of this
    checkout's docs/, which takes a moment to go live."""
    app = versions.app_version(ctx.root)
    if versions.is_prerelease(app):
        say(f"    {app} is a pre-release: the site stays on the last release")
        return
    step("the documentation site, with this release's news")
    run_here(["make", "-C", "docs", "publish"], "docs", cwd=ctx.root)
    _, want = capture(["git", "log", "-1", "--format=%H", "--", "docs"], cwd=ctx.root)
    deadline = time.monotonic() + DEPLOYED_SECONDS
    while (served := deployed_commit()) != want.strip():
        if time.monotonic() >= deadline:
            break
        time.sleep(10)
    else:
        say(f"    {DOCS_STAMP} names {want.strip()[:9]}, this checkout's docs")
        return
    problems(
        [f"{DOCS_STAMP} names {served}, not {want.strip()[:9]}"],
        "the site did not go live.",
    )


def deployed_commit() -> str | None:
    """The commit the live site says it was built from, or None."""
    try:
        with urllib.request.urlopen(DOCS_STAMP, timeout=30) as r:
            return json.load(r).get("commit")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def docs_problems() -> list[str]:
    """Why the site cannot be deployed from here, asked before anything is
    published."""
    if shutil.which("hop3") is None:
        return ["no hop3 here, which deploys the documentation site"]
    return []
