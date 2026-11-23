"""`components`: what goes to PyPI beside `libera`, made on each builder.

From 0.7 `libera` installs the editors and the converter as two packages of
their own, which pip must find on PyPI: `libera-core`, a wheel per platform,
since it carries the native converter, and its source, which pip builds where
no wheel fits; and `libera-web`, the same on every platform. 0.7.0b1 went up
without them, `libera` alone, and nothing could install it: `make publish`
uploaded the wheel `make build` made, and no phase knew of the others.

So each builder runs `lb components build`, which builds its core wheel from
the core's source at the pins, its build tree kept as a compile cache (hours
the first time), and the editors' wheel, or takes both from a build of the
same inputs (components.cache_key). Every platform's core wheel and the Mac's
editors' wheel are then brought to one folder here, the run's `pypi/`, which
`label` labels.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from libera_build import repo, versions
from libera_build.artifacts import (
    MIN_CORE_BYTES,
    PYPI_DIR,
    core_wheel_name,
    web_wheel_name,
)
from libera_build.components import TAGS
from libera_build.hosts import remote_path
from libera_build.process import run_here
from libera_build.release.builds import check_remote_file, run_builds
from libera_build.report import problems, say, step

# Under $BUILD_ROOT, beside src/ and out/: see release_env.
RELEASE_ROOT = "release"
# What each machine runs, on a builder and here alike. One spelling: here it
# said `components wheels` for weeks after the command was renamed, and no
# test ran it.
COMMAND = "components build"

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context


def run(ctx: Context) -> None:
    """Every selected builder's core wheel; the Mac's editors."""
    payload = versions.payload_version(ctx.root)
    out = f"{PYPI_DIR}/{payload}"
    dest = ctx.run / "pypi"
    if ctx.remotes:

        def verify(b: Builder, host: Host) -> str | None:
            name = core_wheel_name(payload, TAGS[b.platform])
            path = f"{remote_path(b.repo)}/{out}/{name}"
            return check_remote_file(b, host, path, MIN_CORE_BYTES)

        run_builds(
            ctx,
            ctx.remotes,
            lambda _b: f"{COMMAND} --out {out}",
            verify,
            "building the components",
        )
        fetch(ctx, payload, out, dest)
    if [b for b in ctx.builders if not b.remote]:
        step("the components, here")
        argv = ["uv", "run", "--no-sync", "lb", *COMMAND.split(), "--out", str(dest)]
        run_here(argv, "components", cwd=ctx.root, env=release_env())
    problems(missing(ctx, payload, dest), "the components are not all here.")
    for name in sorted(p.name for p in dest.glob("libera_*")):
        size = (dest / name).stat().st_size // 1048576
        say(f"    {name}  {size} MB")


def release_env() -> dict[str, str]:
    """This machine's build, in a build root of its own, $BUILD_ROOT/release.

    The working trees under $BUILD_ROOT/src are where upstream fixes are made
    and committed before they are exported to the queue, and the components'
    hooks fetch a tree that is not its pin plus the queue, which resets it and
    removes what is not committed. In a root of their own, the release's trees
    hold nothing but what fetch put there, and the working trees are never
    touched. They are its MIRROR, unless one is set, so a pin they already
    have is not downloaded again. Its out/ is kept between runs, as a compile
    cache.
    """
    working = repo.build_root()
    return {
        "MIRROR": str(working / "src"),
        **os.environ,
        "BUILD_ROOT": str(working / RELEASE_ROOT),
    }


def fetch(ctx: Context, payload: str, out: str, dest: Path) -> None:
    """Each remote builder's core wheel, here. Not its editors' wheel: one
    goes up, the Mac's."""
    step("collecting the components")
    dest.mkdir(parents=True, exist_ok=True)
    found = []
    for b in ctx.remotes:
        name = core_wheel_name(payload, TAGS[b.platform])
        landed = dest / name
        status, said = ctx.host_for(b).fetch(f"{b.repo}/{out}/{name}", landed)
        # scp reports success for a transfer that wrote nothing often enough
        # that the size is the thing to believe.
        if (
            status != 0
            or not landed.is_file()
            or landed.stat().st_size < MIN_CORE_BYTES
        ):
            found.append(f"{b.platform}: {name} did not arrive\n       {said.strip()}")
    problems(found, "the components are not all here.")


def missing(ctx: Context, payload: str, dest: Path) -> list[str]:
    """What the selected builders should have left in `dest` and did not."""
    wanted = [core_wheel_name(payload, TAGS[b.platform]) for b in ctx.builders]
    if [b for b in ctx.builders if not b.remote]:
        wanted.append(web_wheel_name(payload))
    return [
        f"{name} is not in {dest}" for name in wanted if not (dest / name).is_file()
    ]
