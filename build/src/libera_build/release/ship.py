"""`lb release ship`: the phases, in the one order they work in.

Hours, most of it unattended. Every phase asserts on what a machine printed
rather than on an exit status, and checks for its own artifact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libera_build import inventory, repo, versions
from libera_build.hosts import ssh_host
from libera_build.release import plan, precheck
from libera_build.release.builds import mmss
from libera_build.release.context import Context
from libera_build.release.phases import builders, here, publishing, update
from libera_build.report import say, step

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder


@dataclass(frozen=True)
class ShipOptions:
    phases: tuple[str, ...] = ()
    only: tuple[str, ...] = ()
    yes: bool = False
    dry_run: bool = False
    root: Path = repo.REPO
    host_for: Callable[[Builder], Host] = field(default=ssh_host)


ACTIONS: dict[str, Callable[[Context], None]] = {
    "update": update.run,
    "native": here.native,
    "build": builders.build,
    "collect": lambda ctx: publishing.origin(ctx, "collect"),
    "push": lambda ctx: publishing.origin(ctx, "push"),
    "check": lambda ctx: publishing.origin(ctx, "check"),
    "bundles": builders.bundles,
    "wheel": here.wheel,
    "publish": publishing.publish,
    "verify": publishing.verify,
}


def ship(options: ShipOptions) -> int:
    builders_ = inventory.read(options.root / repo.BUILDERS)
    # One platform at a time, because the reasons to build them differ: an
    # arm64 flatpak can only be built on an arm64 machine, and a machine short
    # of disk should not be handed a build just because its neighbour is free.
    chosen = inventory.narrow(builders_, list(options.only))
    phases = plan.choose_phases(options.phases, narrowed=bool(options.only))
    ctx = Context(
        root=options.root,
        builders=chosen,
        phases=phases,
        yes=options.yes,
        host_for=options.host_for,
    )
    if options.dry_run:
        show_plan(ctx)
        return 0
    precheck.run(ctx)
    started = time.monotonic()
    for phase in ctx.phases:
        ACTIONS[phase](ctx)
    step(f"done in {mmss(time.monotonic() - started)}")
    app = versions.app_version(options.root)
    if "publish" in phases and versions.is_prerelease(app):
        say(f"    {app} is a pre-release: pip, the install scripts and the")
        say("    Homebrew tap stay on the last release. Testers name it:")
        say(f"        pipx install --pip-args=--pre libera=={app}")
    elif "publish" in phases:
        # A separate repository, so nothing here can keep it in step. Naming
        # the command is the difference between a tap that lags one release
        # and a tap that lags five.
        say("    the Homebrew tap is a separate repository and does not follow:")
        say("        cd ~/projects/homebrew-tap && make update FORMULA=libera")
        say("")
    if any(p in phases for p in ("publish", "check", "verify")):
        say("    the last word belongs to a machine that never built it:")
        say("        libera --payload-install")
    return 0


def show_plan(ctx: Context) -> None:
    step("the plan")
    say(f"    phases   {', '.join(ctx.phases)}")
    say(f"    libera   {versions.app_version(ctx.root)}")
    say(f"    payload  {versions.payload_version(ctx.root)}")
    say(f"    here     {repo.branch(ctx.root)} at {repo.head(ctx.root)[:9]}")
    for b in ctx.builders:
        where = f"{b.target}:{b.repo}" if b.remote else "local"
        say(f"    {b.platform:<14} {where}{'  neutral' if b.neutral else ''}")
    if irreversible := [p for p in plan.IRREVERSIBLE if p in ctx.phases]:
        say(f"    note     {', '.join(irreversible)} cannot be undone")
