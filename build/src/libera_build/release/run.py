"""`lb release check` and `lb release publish`: their phases, in the one order
they work in.

Hours, most of it unattended. Every phase asserts on what a machine printed
rather than on an exit status, and checks for its own artifact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libera_build import artifacts, inventory, repo, versions
from libera_build.hosts import ssh_host
from libera_build.release import plan, precheck
from libera_build.release.builds import mmss
from libera_build.release.context import DEFAULT_TAP, Context
from libera_build.release.phases import (
    builders,
    chores,
    components,
    here,
    labels,
    publishing,
    staging,
    update,
)
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder


@dataclass(frozen=True)
class RunOptions:
    verb: str  # check or publish
    phases: tuple[str, ...] = ()
    only: tuple[str, ...] = ()
    version: str = ""  # publish's: the release's
    yes: bool = False
    fast: bool = False
    dry_run: bool = False
    tap: Path = DEFAULT_TAP
    root: Path = repo.REPO
    host_for: Callable[[Builder], Host] = field(default=ssh_host)


ACTIONS: dict[str, Callable[[Context], None]] = {
    "update": update.run,
    "components": components.run,
    "bundles": builders.bundles,
    "wheel": here.wheel,
    "label": labels.label,
    "release": labels.release,
    "stage": staging.run,
    "distros": staging.distros,
    "publish": staging.publish,
    "verify": publishing.verify,
    "downloads": publishing.downloads,
    "tap": chores.tap,
    "docs": chores.docs,
}


def run(options: RunOptions) -> int:
    builders_ = inventory.read(options.root / repo.BUILDERS)
    # One platform at a time, because the reasons to build them differ: an
    # arm64 flatpak can only be built on an arm64 machine, and a machine short
    # of disk should not be handed a build just because its neighbour is free.
    chosen = inventory.narrow(builders_, list(options.only))
    phases = plan.choose_phases(
        options.verb, options.phases, narrowed=bool(options.only), fast=options.fast
    )
    # What this run is about: for a check, this commit, under its candidate's
    # label; for a publish, the commit that was checked, under the release's.
    if options.verb == "publish":
        versions.check_version(options.version)
        checked = labels.checked_commit(options.root, options.version)
        version = options.version
    else:
        checked = repo.head(options.root)
        version = labels.candidate_version(options.root, checked)
    ctx = Context(
        root=options.root,
        builders=chosen,
        phases=phases,
        version=version,
        run=options.root / artifacts.RELEASE_DIR / checked,
        yes=options.yes,
        fast=options.fast,
        host_for=options.host_for,
        tap=options.tap,
    )
    if options.dry_run:
        show_plan(ctx)
        return 0
    precheck.run(ctx)
    started = time.monotonic()
    head = repo.head(options.root)
    took = []
    for phase in ctx.phases:
        begun = time.monotonic()
        ACTIONS[phase](ctx)
        took.append(f"{phase} {mmss(time.monotonic() - begun)}")
        if phase == "release":  # the one phase that commits, on purpose
            head = repo.head(options.root)
        moved_problem(options.root, head, phase)
    step(f"done in {mmss(time.monotonic() - started)}")
    say(f"    {', '.join(took)}")
    app = ctx.version
    if "stage" in phases and options.verb == "check":
        if options.fast:
            say("    checked with --fast, which no release starts from")
        else:
            say(f"    {app} checked; to release it: lb release publish X.Y.Z")
        return 0
    prerelease = versions.is_prerelease(app)
    if "publish" in phases and prerelease:
        say(f"    {app} is a pre-release: pip, the install scripts and the")
        say("    Homebrew tap stay on the last release.")
    elif "publish" in phases and "tap" not in phases:
        # A separate repository, so nothing here keeps it in step but the
        # tap phase. Naming the command is the difference between a tap
        # that lags one release and a tap that lags five.
        say("    the Homebrew tap does not follow without its phase:")
        say("        lb release publish tap")
        say("")
    if "publish" in phases or "verify" in phases:
        # verify installs from PyPI and converts; nothing here opens a window.
        pre = "--pip-args=--pre " if prerelease else ""
        say("    the last word is a window, on a machine that never built it:")
        say(f"        pipx install {pre}libera=={app} && libera")
    return 0


def moved_problem(root: Path, head: str, phase: str) -> None:
    """Refused, if a commit was made here while `phase` ran. The run directory
    is named by the commit, read again by each phase: a commit made during a
    Mac's hours-long components build once sent its final check to another
    commit's directory, which reported every wheel missing."""
    if (now := repo.head(root)) != head:
        msg = (
            f"this checkout moved from {head[:9]} to {now[:9]} during {phase}.\n"
            f"  What the run made so far is in {artifacts.RELEASE_DIR}/{head[:9]}…, and"
            " the next phase would\n  look for it under the new commit. Start"
            " again at this one: lb release check"
        )
        raise RefusedError(msg)


def show_plan(ctx: Context) -> None:
    step("the plan")
    say(f"    phases   {', '.join(ctx.phases)}")
    say(f"    version  {ctx.version}")
    say(f"    checked  {ctx.run.name[:9]}")
    say(f"    here     {repo.branch(ctx.root)} at {repo.head(ctx.root)[:9]}")
    for b in ctx.builders:
        where = f"{b.target}:{b.repo}" if b.remote else "local"
        say(f"    {b.platform:<14} {where}")
    if "publish" in ctx.phases:
        say("    note     publish cannot be undone")
