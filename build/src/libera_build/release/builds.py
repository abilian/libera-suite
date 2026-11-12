"""`lb` on several builders at once, each judged by what it printed.

The builds run in parallel: two builders of two hours each, one after the
other, is an afternoon that did not need to be. Each says a verdict line rather
than trusting an exit status (see hosts), and then a phase's own check looks
for the artifact. Each phase brings that check, because one that guessed the
artifact from the command got it wrong: `bundles` once reported a pass after
finding the core tarball a *payload* build had left behind.
"""

from __future__ import annotations

import concurrent.futures
import time
from typing import TYPE_CHECKING

from libera_build import detached
from libera_build.artifacts import size_problem
from libera_build.hosts import LB, MARK, facts_from, remote_path
from libera_build.release import plan
from libera_build.report import problems, say, step

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context

    # What a phase brings: the `lb` command for a builder, and the check that
    # says whether it produced anything.
    CommandFor = Callable[[Builder], str]
    Verify = Callable[[Builder, Host], str | None]

# Long enough that two builders do not fill the terminal, short enough that a
# two-hour stage never looks like a hang.
HEARTBEAT_SECONDS = 60
HEARTBEAT_WIDTH = 60


def run_builds(
    ctx: Context,
    remotes: list[Builder],
    command_for: CommandFor,
    verify: Verify,
    what: str,
) -> None:
    """Run one `lb` command per builder, in parallel; report every failure."""
    step(f"{what} on {len(remotes)} machine(s), in parallel")
    for b in remotes:
        say(
            f"    {b.platform:<14} {b.target}  lb {command_for(b)}"
            f"  ->  tmp/remote/{b.platform}.log"
        )
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(remotes)) as pool:
        results = list(
            pool.map(lambda b: build_one(ctx, b, command_for(b), verify), remotes)
        )
    failures = [r for r in results if r]
    problems(failures, f"{len(failures)} of {len(remotes)} builder(s) failed.")


def build_one(ctx: Context, b: Builder, command: str, verify: Verify) -> str | None:
    """Build on one machine. Returns a complaint, or None if it worked.

    The build runs detached on the builder and is polled from here (see
    `detached`): a dropped connection is a poll that missed, and the build
    goes on. A re-run of a phase whose job is still running watches that job
    rather than starting a second build on the same tree.
    """
    ctx.logs.mkdir(parents=True, exist_ok=True)
    log = ctx.logs / f"{b.platform}.log"
    host = ctx.host_for(b)
    name = f"{b.platform} {command}"
    # `lb` as a module: a builder runs it with its own python3, nothing
    # installed, so the console script is not there. No `set -e`, and the
    # verdict comes back as a printed line.
    script = f"""
cd {remote_path(b.repo)} || {{ echo "{MARK}=no such directory"; exit; }}
echo "== $(hostname) $(uname -m), at $(git rev-parse --short HEAD)"
if {LB} {command}
then echo "{MARK}=ok"
else echo "{MARK}=lb {command} failed ($?)"
fi
"""
    started = time.monotonic()
    begun = facts_from(host.capture(detached.start_script(name, script)))
    if "STARTED" not in begun and "ATTACHED" not in begun:
        return (
            f"{b.platform}: the build did not start: {begun.get('START', 'no answer')}"
        )
    if "ATTACHED" in begun:
        say(f"    {b.platform:<14} still running there from before: watching it")
    verdict = watch(ctx, b, name, log, started)
    elapsed = mmss(time.monotonic() - started)
    if problem := plan.build_problem(b.platform, verdict, elapsed):
        return f"{problem}\n       {log}\n{tail(log)}"
    if problem := verify(b, host):
        return f"{problem}\n       {log}"
    say(f"    {b.platform:<14} done in {elapsed}")
    return None


def watch(ctx: Context, b: Builder, name: str, log: Path, started: float) -> str:
    """Poll a detached job until it ends; its verdict line, "" for none.

    A heartbeat rather than the output itself: `lb container run payload` is
    tens of thousands of lines and two of them interleaved is noise; silence
    for two hours is worse. The log has everything. A builder that does not
    answer for `ctx.unreachable_seconds` ends the watch, saying the job may
    still be running there: the same phase, run again, picks it up.
    """
    host = ctx.host_for(b)
    offset, lines, verdict, said = 0, 0, "", ""
    last_beat = last_heard = time.monotonic()
    with log.open("w", encoding="utf-8") as fh:
        while True:
            poll = detached.parse_poll(host.capture(detached.poll_script(name, offset)))
            now = time.monotonic()
            if poll is None:
                silent = now - last_heard
                if silent >= ctx.unreachable_seconds:
                    return (
                        f"no answer from {b.target} for {mmss(silent)}; the job may "
                        "still be running there, and the same phase, run again, "
                        "watches it"
                    )
                if now - last_beat >= HEARTBEAT_SECONDS:
                    say(
                        f"    {b.platform:<14} {mmss(now - started)}"
                        f"  no answer for {mmss(silent)}"
                    )
                    last_beat = now
                time.sleep(ctx.poll_seconds)
                continue
            last_heard = now
            if poll.gone:
                return ""
            fh.write(poll.text)
            fh.flush()
            offset = poll.size
            for line in poll.text.splitlines():
                lines += 1
                if line.startswith(f"{MARK}="):
                    verdict = line.split("=", 1)[1].strip()
                # The last line that said something: a heartbeat that lands on
                # a blank line otherwise reports "115 lines" and nothing else.
                said = line if line.strip() else said
            if poll.done or not poll.alive:
                return verdict
            if now - last_beat >= HEARTBEAT_SECONDS:
                say(
                    f"    {b.platform:<14} {mmss(now - started)}"
                    f"  {lines} lines  {shorten(said)}"
                )
                last_beat = now
            time.sleep(ctx.poll_seconds)


def check_remote_file(b: Builder, host: Host, path: str, minimum: int) -> str | None:
    """One remote stat, asserted on the size it printed."""
    out = host.capture(
        f"""
        f={path}
        if [ -f "$f" ]; then echo "BYTES=$(wc -c < "$f" | tr -d ' ')"
        else echo "MISSING=$f"; fi
        """
    )
    facts = facts_from(out)
    name = path.rsplit("/", 1)[-1]
    if "BYTES" not in facts:
        return (
            f"{b.platform}: the build said it worked and {name} is not there.\n"
            f"       {out}"
        )
    size = int(facts["BYTES"])
    if problem := size_problem(b.platform, name, size, minimum):
        return problem
    say(f"    {b.platform:<14} {name}, {size // 1048576} MB")
    return None


def mmss(seconds: float) -> str:
    return f"{int(seconds) // 60:d}m{int(seconds) % 60:02d}s"


def shorten(line: str) -> str:
    text = line.strip()
    return text if len(text) <= HEARTBEAT_WIDTH else text[:HEARTBEAT_WIDTH] + "..."


def tail(log: Path, lines: int = 25) -> str:
    text = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(f"       | {line}" for line in text[-lines:])
