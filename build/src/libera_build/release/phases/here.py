"""`native` and `wheel`: the phases that run on this machine."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

from libera_build import repo, versions
from libera_build.process import run_here
from libera_build.report import RefusedError, problems, say, step
from libera_build.sources import pinned, source_problems

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.release.context import Context

# Under what payload.sh deletes as it starts, and written near its end, so it is
# there only after a build that got that far.
PAYLOAD_FINISHED = "out/payload/sdkjs/slide/themes/themes.js"


def native(ctx: Context) -> None:
    """The macOS core, on this machine, because there is nowhere else for it.

    `lb payload build dist` re-tars the core already built under $BUILD_ROOT and
    takes a minute. It does not build one: that is `make payload`, an
    afternoon, run by hand beforehand, and one older than its trees is
    refused. It runs every time all the same, because the payload half is
    never skippable: a release once shipped an editors.tar.gz older than the
    licence text inside it.
    """
    if not [b for b in ctx.builders if not b.remote]:
        say("    no local builder selected; nothing to do here")
        return
    step("the native core, here")
    if sys.platform != "darwin":
        # Skipping and going on would ship the previous macOS core.
        msg = f"the local builder makes the macOS core, and this is {sys.platform}"
        raise RefusedError(msg)
    problems(
        source_problems(ctx.root, repo.build_root() / "src"),
        "the manifest would name the pins and these trees are not at them.\n"
        "  make payload: it fetches, which applies the queue, and rebuilds.",
    )
    problems(
        stale_problems(ctx.root, repo.build_root()),
        "the tarballs would hold a build older than the trees it comes from.\n"
        "  make payload: it rebuilds.",
    )
    run_here(["uv", "run", "lb", "payload", "build", "dist"], "native", cwd=ctx.root)


def stale_problems(root: Path, build: Path) -> list[str]:
    """Which trees under `build` moved after its payload was built, one sentence
    a tree. Trees at their pins say nothing about what out/ was made from: every
    check passed on a Mac whose editors were a week older than its trees.

    The reflog says when a tree last moved, and a commit's date does not: a pin
    can be bumped to a commit older than the build.
    """
    finished = build / PAYLOAD_FINISHED
    if not finished.is_file():
        return [f"no finished payload build: {finished} is not there"]
    built = finished.stat().st_mtime
    found = []
    for name in pinned(root):
        moved = (build / "src" / name / ".git" / "logs" / "HEAD").stat().st_mtime
        if moved > built:
            found.append(f"{name}: moved {when(moved)}, payload built {when(built)}")
    return found


def when(seconds: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(seconds))


def wheel(ctx: Context) -> None:
    """The suite, then the wheel -- in that order, and the order is the point.

    The wheel carries the manifest, which `native`'s dist stamped. Building
    it before the suite has run means publishing a wheel nothing has
    exercised.
    """
    step("the suite, then the wheel")
    run_here(["make", "verify"], "wheel", cwd=ctx.root)
    run_here(["make", "build"], "wheel", cwd=ctx.root)
    app = versions.app_version(ctx.root)
    dist = ctx.root / "dist"
    wheels = sorted(dist.glob(f"libera-{app}-*.whl"))
    if not wheels:
        msg = (
            f"make build reported success and there is no libera-{app}-*.whl in {dist}."
        )
        raise RefusedError(msg)
    for found in wheels:
        say(f"    {found.name}  {found.stat().st_size // 1024} kB")
