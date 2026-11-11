"""Everything that can stop a release, found before any of the long work.

Gathers the facts -- the environment, this checkout, the manifest, each
builder -- and hands them to the rules in `plan`, which decide.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from libera.manifest import Manifest
from libera_build import repo, versions
from libera_build.hosts import facts_from, remote_path
from libera_build.origin import publish
from libera_build.release import plan
from libera_build.release.phases import staging
from libera_build.report import problems, say, step

if TYPE_CHECKING:
    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context


def run(ctx: Context) -> None:
    step("before anything long")
    found: list[str] = []
    found += plan.token_problems(
        ctx.phases, have_token=bool(os.environ.get("CDN_TOKEN"))
    )
    found += plan.signing_problems(ctx.phases, have_key=publish.signing_key_here())

    head = repo.head(ctx.root)
    say(
        f"    libera {versions.app_version(ctx.root)},"
        f" payload {versions.payload_version(ctx.root)}"
    )
    say(f"    here at {head[:9]} on {repo.branch(ctx.root)}")
    dirty = len(repo.dirty(ctx.root))
    refused = plan.dirty_problems(
        ctx.phases, dirty=dirty, allow_dirty=os.environ.get("ALLOW_DIRTY") == "1"
    )
    if dirty and not refused:
        say(f"    note: {dirty} uncommitted file(s) here, which no builder sees")
    found += refused

    stamped = ctx.root / repo.MANIFEST
    manifest = Manifest.read(stamped) if stamped.is_file() else None
    found += plan.publish_problems(
        ctx.phases,
        manifest=manifest,
        payload_version=versions.payload_version(ctx.root),
        head=head,
    )
    # A publish without a stage in the same run uploads the last one's, which
    # must still hold: found now, not after hours of building.
    if "publish" in ctx.phases and "stage" not in ctx.phases:
        found += staging.stamp_problems(ctx.root)
    if any(p in ctx.phases for p in plan.UPLOADING):
        found += plan.unpushed_problems(
            ctx.phases, on_a_remote=repo.on_a_remote(ctx.root), head=head
        )

    for b in ctx.builders:
        if b.remote:
            found += check_builder(ctx, b)
        else:
            say(f"    {b.platform:<14} local, left alone")
    problems(found, "nothing was started.")


ANSWER_TRIES = 4


def check_builder(ctx: Context, b: Builder) -> list[str]:
    """Ask one builder about itself.

    A missing checkout is a problem only when nothing in this run will make
    one: `update` does, since a builder's checkout holds nothing but the
    commit it is sent.
    """
    host = ctx.host_for(b)
    script = f"""
        echo "ARCH=$(uname -m)"
        if cd {remote_path(b.repo)} 2>/dev/null; then
            echo "DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
            echo "HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
        else
            echo "NOREPO=1"
        fi
        """
    # A few tries, a poll apart: builder-windows answered one minute and not
    # the next on 2026-11-01, and one unanswered question refused a whole run.
    out = host.capture(script)
    facts = facts_from(out)
    for _ in range(ANSWER_TRIES - 1):
        if "ARCH" in facts:
            break
        time.sleep(ctx.poll_seconds)
        out = host.capture(script)
        facts = facts_from(out)
    if "ARCH" not in facts:
        problem = f"{b.platform}: no answer from {b.target} in {ANSWER_TRIES} tries"
        return [f"{problem}\n       {out}"]
    if "NOREPO" in facts and "update" not in ctx.phases:
        return [missing_repo(host, b, out)]
    where = "none yet, update makes it" if "NOREPO" in facts else facts.get("HEAD", "?")
    say(f"    {b.platform:<14} {b.target} ({facts['ARCH']}, {b.repo} at {where})")
    return plan.builder_problems(b, facts)


def missing_repo(host: Host, b: Builder, out: str) -> str:
    """Name the checkouts that are there, since the configured one is not."""
    found = host.capture(
        'for d in "$HOME"/*/; do '
        f'[ -f "$d/{repo.PAYLOAD_VERSION.as_posix()}" ] && echo "         $d"; done'
    )
    detail = (
        f"\n       checkouts on that machine:\n{found}" if found else f"\n       {out}"
    )
    return f"{b.platform}: no checkout at {b.repo} on {b.target}{detail}"
