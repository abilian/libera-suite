"""`components`: what goes to PyPI beside `libera`, made on each builder.

From 0.7 `libera` installs the editors and the converter as two packages of
their own, which pip must find on PyPI: `libera-core`, a wheel per platform,
since it carries the native converter, and its source, which pip builds where
no wheel fits; and `libera-web`, the same on every platform. 0.7.0b1 went up
without them, `libera` alone, and nothing could install it: `make publish`
uploaded the wheel `make build` made, and no phase knew of the others.

So each builder runs `lb components wheels`, which builds its core wheel from
the core's source, reusing the build tree `build` has just brought to the pin,
and the editors' wheel. Every platform's wheel, the Mac's source and the Mac's
editors' wheel are then brought to one folder here, `build/out/pypi/<payload
version>/`, where `publish` uploads them from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from libera_build import versions
from libera_build.artifacts import (
    MIN_CORE_BYTES,
    PYPI_DIR,
    core_sdist_name,
    core_wheel_name,
    web_wheel_name,
)
from libera_build.components import TAGS
from libera_build.hosts import remote_path
from libera_build.process import run_here
from libera_build.release.builds import check_remote_file, run_builds
from libera_build.report import problems, say, step

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context


def folder(ctx: Context) -> Path:
    """Here, where every platform's files are gathered for `publish`."""
    return ctx.root / PYPI_DIR / versions.payload_version(ctx.root)


def run(ctx: Context) -> None:
    """Every selected builder's core wheel; the Mac's source and editors."""
    payload = versions.payload_version(ctx.root)
    out = f"{PYPI_DIR}/{payload}"
    if ctx.remotes:

        def verify(b: Builder, host: Host) -> str | None:
            name = core_wheel_name(payload, TAGS[b.platform])
            path = f"{remote_path(b.repo)}/{out}/{name}"
            return check_remote_file(b, host, path, MIN_CORE_BYTES)

        run_builds(
            ctx,
            ctx.remotes,
            lambda _b: f"components wheels --out {out}",
            verify,
            "building the components",
        )
        fetch(ctx, payload, out)
    if [b for b in ctx.builders if not b.remote]:
        step("the components, here")
        dest = folder(ctx)
        run_here(
            [
                "uv",
                "run",
                "--no-sync",
                "lb",
                "components",
                "wheels",
                "--out",
                str(dest),
            ],
            "components",
            cwd=ctx.root,
        )
    problems(missing(ctx, payload), "the components are not all here.")
    for name in sorted(p.name for p in folder(ctx).glob("libera_*")):
        size = (folder(ctx) / name).stat().st_size // 1048576
        say(f"    {name}  {size} MB")


def fetch(ctx: Context, payload: str, out: str) -> None:
    """Each remote builder's core wheel, here. Not its source or editors'
    wheel: one of each goes up, the Mac's."""
    step("collecting the components")
    dest = folder(ctx)
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


def missing(ctx: Context, payload: str) -> list[str]:
    """What the selected builders should have left here and did not."""
    dest = folder(ctx)
    wanted = [core_wheel_name(payload, TAGS[b.platform]) for b in ctx.builders]
    if [b for b in ctx.builders if not b.remote]:
        wanted += [core_sdist_name(payload), web_wheel_name(payload)]
    return [
        f"{name} is not in {dest}" for name in wanted if not (dest / name).is_file()
    ]
