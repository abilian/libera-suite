"""`native` and `wheel`: the phases that run on this machine."""

from __future__ import annotations

import subprocess
import sys
import time
from typing import TYPE_CHECKING

import tomllib

from libera_build import repo, versions
from libera_build.process import run_here
from libera_build.report import RefusedError, problems, say, step

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

    from libera_build.release.context import Context

# Under what payload.sh deletes as it starts, and written near its end, so it is
# there only after a build that got that far.
PAYLOAD_FINISHED = "out/payload/sdkjs/slide/themes/themes.js"


def native(ctx: Context) -> None:
    """The macOS core, on this machine, because there is nowhere else for it.

    `lb payload dist` re-tars the core already built under $BUILD_ROOT and
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
    run_here(["uv", "run", "lb", "payload", "dist"], "native", cwd=ctx.root)


def pinned(root: Path) -> dict[str, str]:
    return tomllib.loads((root / repo.PINS).read_text(encoding="utf-8"))["repos"]


def source_problems(
    root: Path, src: Path, only: Collection[str] | None = None
) -> list[str]:
    """Why the trees under `src` are not the pins plus the patch queue in
    `root`, one sentence a tree; of every pinned tree, or of `only`.

    The manifest stamps the pins from pins.toml, not from what was compiled,
    and nothing in re-tarring a core fetches: a patch added since the trees
    were last fetched would ship as a release that claims it. Patches are
    compared by `git patch-id`, which reads the change rather than the subject
    line, so a patch refreshed in place counts as a different one. Not their
    order: a tree fetched before a patch was renumbered holds the same changes
    in another order, as this Mac's core did when this was written.
    """
    found = []
    for name, pin in pinned(root).items():
        if only is not None and name not in only:
            continue
        tree = src / name
        if not (tree / ".git").exists():
            found.append(f"{name}: no source tree at {tree}")
            continue
        on_pin = subprocess.run(
            ["git", "-C", str(tree), "merge-base", "--is-ancestor", pin, "HEAD"],
            capture_output=True,
            check=False,
        )
        if on_pin.returncode != 0:
            found.append(f"{name}: {tree} is not on its pin, {pin[:9]}")
            continue
        queue = sorted((root / repo.PATCHES / name).glob("*.patch"))
        want = patch_ids(b"".join(p.read_bytes() for p in queue), tree)
        applied = git_out(tree, "format-patch", "--stdout", f"{pin}..HEAD")
        if sorted(have := patch_ids(applied, tree)) != sorted(want):
            found.append(
                f"{name}: {tree} carries {len(have)} commit(s) on its pin, and "
                f"they are not the {len(want)} patch(es) in the queue"
            )
    return found


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


def patch_ids(patches: bytes, tree: Path) -> list[str]:
    """The `git patch-id` of each patch in a series, in order."""
    out = git_out(tree, "patch-id", "--stable", stdin=patches)
    return [line.split()[0] for line in out.decode().splitlines()]


def git_out(tree: Path, *args: str, stdin: bytes = b"") -> bytes:
    """What git printed, as bytes, since a patch need not be UTF-8; or a
    refusal carrying what git said instead."""
    done = subprocess.run(
        ["git", "-C", str(tree), *args], input=stdin, capture_output=True, check=False
    )
    if done.returncode != 0:
        said = done.stderr.decode(errors="replace").strip()
        msg = f"git {args[0]} in {tree} failed ({done.returncode}): {said}"
        raise RefusedError(msg)
    return done.stdout


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
