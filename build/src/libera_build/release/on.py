"""`lb on PLATFORM COMMAND...`: any `lb` command, run on a builder.

The way `ship` runs its builds there: in the builder's checkout, as `python3 -m
libera_build`, since nothing is installed there and the `lb` script is not.
And as a release phase runs one, detached there and polled from here (see
`detached`): a connection reset two hours into a build once ended the watch
and lost the output while the build carried on. A dropped connection is now a
missed poll; the same `lb on` command, run again while the job runs, follows
it rather than starting a second. The output streams as the polls bring it,
and is kept in tmp/remote/on-<platform>.log. The status is read from the
verdict line the script prints, not from ssh's exit status.

The builder runs whatever commit its checkout is at. This says which, warns
when it is not this checkout's, and with --update sends this one first.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libera_build import artifacts, detached, inventory, repo
from libera_build.hosts import LB, MARK, facts_from, remote_path, ssh_host
from libera_build.release import builds
from libera_build.release.context import Context
from libera_build.release.phases import labels, update
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder


@dataclass(frozen=True)
class OnOptions:
    platform: str
    command: tuple[str, ...]
    update: bool = False
    root: Path = REPO
    host_for: Callable[[Builder], Host] = field(default=ssh_host)
    poll_seconds: float = 2


def script_for(b: Builder, command: tuple[str, ...]) -> str:
    """What the builder runs: its HEAD said first, then the command, then the
    verdict line the caller believes."""
    line = shlex.join(command)
    return f"""
cd {remote_path(b.repo)} || {{ echo "{MARK}=no checkout at {b.repo}"; exit; }}
echo "HEAD=$(git rev-parse HEAD)"
{LB} {line}
echo "{MARK}=$?"
"""


def status_of(platform: str, verdict: str) -> int:
    """The command's exit status, from the verdict line. Anything else there
    is why the command never ran ("no checkout at ~/x"), and nothing at all
    means the connection dropped: either is a refusal that says so."""
    if verdict.isdigit():
        return int(verdict)
    msg = f"{platform}: {verdict or 'the command stopped without saying how'}"
    raise RefusedError(msg)


def on(options: OnOptions) -> int:
    builders = inventory.read(options.root / repo.BUILDERS)
    (b,) = inventory.narrow(builders, [options.platform])
    if not b.remote:
        msg = (
            f"{b.platform} is this machine: run `lb {shlex.join(options.command)}` here"
        )
        raise RefusedError(msg)
    # `lb on` makes no release files; the context names this commit's
    # candidate and run directory only because every Context carries them.
    here = repo.head(options.root)
    ctx = Context(
        root=options.root,
        builders=[b],
        phases=[],
        version=labels.candidate_version(options.root, here),
        run=options.root / artifacts.RELEASE_DIR / here,
        host_for=options.host_for,
        poll_seconds=options.poll_seconds,
    )
    if options.update:
        update.run(ctx)
    step(f"lb {shlex.join(options.command)}, on {b.platform} ({b.target})")
    name = f"on {shlex.join(options.command)}"
    host = options.host_for(b)
    begun = facts_from(
        host.capture(detached.start_script(name, script_for(b, options.command)))
    )
    if "STARTED" not in begun and "ATTACHED" not in begun:
        why = begun.get("START", "no answer")
        msg = f"{b.platform}: the command did not start: {why}"
        raise RefusedError(msg)
    if "ATTACHED" in begun:
        say("    still running there from an earlier `lb on`: following it")
    seen_head = False

    def echo(line: str) -> None:
        # The first line is the builder's HEAD, which the script prints first.
        nonlocal seen_head
        if not seen_head and line.startswith("HEAD="):
            seen_head = True
            if (there := line.split("=", 1)[1].strip()) != here:
                say(f"    note: {b.platform} is at {there[:9]}, here at {here[:9]};")
                say("    --update sends this commit first")
            return
        print(line, flush=True)

    ctx.logs.mkdir(parents=True, exist_ok=True)
    log = ctx.logs / f"on-{b.platform}.log"
    verdict = builds.watch(ctx, b, name, log, echo=echo)
    return status_of(b.platform, verdict)
