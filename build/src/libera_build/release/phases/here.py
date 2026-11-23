"""`wheel`: the suite, then libera's own wheel and sdist, on this machine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from libera_build import versions
from libera_build.process import run_here
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from libera_build.release.context import Context


def wheel(ctx: Context) -> None:
    """The suite, then the wheel -- in that order, and the order is the point:
    building it before the suite has run means publishing a wheel nothing
    has exercised. With --fast, the wheel alone: a check between releases,
    which the release's own check does not skip.
    """
    dist = ctx.run / "pypi"
    if ctx.fast:
        step("the wheel (--fast: not the suite)")
    else:
        step("the suite, then the wheel")
        run_here(["make", "verify"], "wheel", cwd=ctx.root)
    run_here(["uv", "build", "--out-dir", str(dist)], "wheel", cwd=ctx.root)
    app = versions.app_version(ctx.root)
    wheels = sorted(dist.glob(f"libera-{app}-*.whl"))
    if not wheels:
        msg = f"uv build reported success and there is no libera-{app}-*.whl in {dist}."
        raise RefusedError(msg)
    for found in wheels:
        say(f"    {found.name}  {found.stat().st_size // 1024} kB")
