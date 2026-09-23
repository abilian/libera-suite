#!/usr/bin/env python3
"""Build the payload on the remote builders, then publish it.

    python3 build/remote.py                  update, build, collect, push, check
    python3 build/remote.py build            just the remote builds
    python3 build/remote.py collect push     skip the building
    python3 build/remote.py --dry-run        print the plan, run nothing

The builders come from build/builders.toml. `origin.sh` reads the same file
through `--print-builders` below, so there is one inventory of machines and one
parser for it rather than two of each.

Why a script at all. A payload release is several commands on three machines,
two of which take hours, and the failure that costs the most is the quiet one:
a builder that built the wrong commit, or wrote an artifact that is there and
empty. So each stage asserts on what the machine printed, and says which
machine it is talking about.

The builds run in parallel. Two builders of two hours each, one after the
other, is an afternoon that did not need to be.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import tomllib

REPO = Path(__file__).resolve().parent.parent
BUILDERS = REPO / "build" / "builders.toml"
LOGS = REPO / "tmp" / "remote"

# Non-interactive, and it should say so quickly rather than sit at a password
# prompt inside a thread whose output nobody is watching.
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]

PHASES = ("update", "build", "collect", "push", "check")

# What the remote scripts print instead of relying on an exit status. A login
# bash returns 1 from `set -eu; exit 0`, because ~/.bash_logout runs with -u
# still in force; see notes/lessons-learned.md.
MARK = "__LIBERA__"

# Long enough that two builders do not fill the terminal, short enough that a
# two-hour stage never looks like a hang.
HEARTBEAT_SECONDS = 60
HEARTBEAT_WIDTH = 60

# A core tarball is tens of megabytes. Anything under this is a build that
# produced a file rather than a payload, which is the failure this project
# keeps meeting: the artifact exists, so every check that only stats it passes.
MIN_CORE_BYTES = 10 * 1024 * 1024

KNOWN_KEYS = {"platform", "target", "dist", "neutral", "repo", "branch"}


@dataclass(frozen=True)
class Builder:
    platform: str  # core-<platform>.tar.gz, e.g. linux-x86_64
    target: str  # an ssh target, or "local"
    dist: str | None  # the parent of the per-version directories
    neutral: bool  # the one that supplies editors.tar.gz and fonts-core.tar.gz
    repo: str  # the checkout on that machine
    branch: str  # the branch it builds

    @property
    def remote(self) -> bool:
        return self.target != "local"


def read_builders(path: Path = BUILDERS) -> list[Builder]:
    """Parse build/builders.toml."""
    if not path.is_file():
        die(
            f"no builder list at {path}\n"
            f"  copy build/builders.toml.example to {path.name} and fill it in."
        )
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        die(f"{path}: {e}")

    defaults = doc.get("defaults", {})
    entries = doc.get("builders", [])
    if not entries:
        die(f"{path}: no [[builders]] entries")

    out = []
    for i, entry in enumerate(entries, start=1):
        if missing := [k for k in ("platform", "target") if k not in entry]:
            die(f"{path}: builder {i} has no {' or '.join(missing)}")
        if unknown := sorted(set(entry) - KNOWN_KEYS):
            die(f"{path}: builder {entry['platform']} has unknown key(s) {unknown}")
        out.append(
            Builder(
                platform=entry["platform"],
                target=entry["target"],
                dist=entry.get("dist"),
                neutral=bool(entry.get("neutral", False)),
                repo=entry.get("repo", defaults.get("repo", "~/liberasuite")),
                branch=entry.get("branch", defaults.get("branch", "main")),
            )
        )

    if len(neutrals := [b.platform for b in out if b.neutral]) > 1:
        die(
            f"{path}: {len(neutrals)} builders marked neutral "
            f"({', '.join(neutrals)}).\n"
            "  editors.tar.gz and fonts-core.tar.gz are not byte-identical\n"
            "  between machines, so exactly one builder supplies them."
        )
    return out


def die(message: str) -> None:
    print(f"\nFATAL: {message}", file=sys.stderr)
    raise SystemExit(1)


def say(message: str = "") -> None:
    print(message, flush=True)


def step(message: str) -> None:
    print(f"\n==> {message}", flush=True)


def remote_path(path: str) -> str:
    """Quote a path for the remote shell, leaving a leading ~ able to expand.

    shlex.quote would wrap `~/liberasuite` in single quotes and the remote
    shell would then look for a directory literally called `~`. Double quotes
    around $HOME expand and still survive a space in the rest.
    """
    if path.startswith("~/"):
        return f'"$HOME/{path[2:]}"'
    return shlex.quote(path)


def ssh_capture(target: str, script: str) -> str:
    """Run a shell script on a builder and return what it printed.

    The exit status is deliberately not returned: over ssh it describes the
    shell, including its login and logout scripts, rather than the work. Every
    caller decides on a line the script printed on purpose.
    """
    done = subprocess.run(
        [*SSH, target, "bash -l -s"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    return (done.stdout + done.stderr).strip()


def facts_from(out: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def run_local(argv: list[str]) -> tuple[int, str]:
    done = subprocess.run(argv, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr


def local_head() -> str:
    status, out = run_local(["git", "-C", str(REPO), "rev-parse", "HEAD"])
    if status != 0:
        die("this checkout has no HEAD")
    return out.strip()


def local_branch() -> str:
    _, out = run_local(["git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() or "main"


def local_dirty() -> list[str]:
    _, out = run_local(["git", "-C", str(REPO), "status", "--porcelain"])
    return [line for line in out.splitlines() if line.strip()]


def payload_version() -> str:
    """The payload version, as dist.sh, flatpak.sh and origin.sh read it.

    build/payload.version is a commented TOML-ish file, not a bare number, and
    reading it whole once printed the file's comment block as the version.
    """
    text = (REPO / "build" / "payload.version").read_text(encoding="utf-8")
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "version":
            return value.strip().strip('"')
    die("no version in build/payload.version")
    raise AssertionError  # die() exits; this is for the type checker


# --- prechecks ---------------------------------------------------------------
#
# All of them before any of the long work. A missing CDN token is a one-second
# discovery that used to be a two-hour one, because push is the last stage and
# the builds are the first.


def precheck(builders: list[Builder], phases: list[str]) -> None:
    step("before anything long")
    problems: list[str] = []

    if "push" in phases and not os.environ.get("CDN_TOKEN"):
        problems.append("push needs CDN_TOKEN in the environment")

    say(f"    payload {payload_version()}, here at {local_head()[:9]}")
    if dirty := local_dirty():
        say(f"    note: {len(dirty)} uncommitted file(s) here, which no builder sees")

    for b in builders:
        if not b.remote:
            say(f"    {b.platform:<14} local, left alone")
            continue
        out = ssh_capture(
            b.target,
            f"""
            echo "ARCH=$(uname -m)"
            if cd {remote_path(b.repo)} 2>/dev/null; then
                echo "DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
                echo "HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
            else
                echo "NOREPO=1"
            fi
            """,
        )
        facts = facts_from(out)
        if "ARCH" not in facts:
            problems.append(f"{b.platform}: no answer from {b.target}\n       {out}")
            continue
        if "NOREPO" in facts:
            problems.append(missing_repo(b, out))
            continue
        say(
            f"    {b.platform:<14} {b.target} "
            f"({facts['ARCH']}, {b.repo} at {facts.get('HEAD', '?')})"
        )
        # Before the pull, not after. A pull into a dirty tree either refuses
        # or merges over somebody's edits, and neither belongs in a script that
        # is about to run for two hours.
        if facts.get("DIRTY", "0") != "0":
            problems.append(
                f"{b.platform}: {facts['DIRTY']} uncommitted file(s) in "
                f"{b.repo} on {b.target}. Clean it before building."
            )

    if problems:
        say()
        for p in problems:
            say(f"    - {p}")
        die("nothing was started.")


def missing_repo(b: Builder, out: str) -> str:
    """Name the checkouts that are there, since the configured one is not."""
    found = ssh_capture(
        b.target,
        'for d in "$HOME"/*/; do '
        '[ -f "$d/build/payload.version" ] && echo "         $d"; done',
    )
    detail = (
        f"\n       checkouts on that machine:\n{found}" if found else f"\n       {out}"
    )
    return f"{b.platform}: no checkout at {b.repo} on {b.target}{detail}"


# --- update ------------------------------------------------------------------


def cmd_update(builders: list[Builder]) -> None:
    """Put every builder on its branch, up to date, and still clean."""
    remotes = [b for b in builders if b.remote]
    if not remotes:
        return
    step("updating the builders")
    here = local_head()
    problems: list[str] = []

    for b in remotes:
        out = ssh_capture(
            b.target,
            f"""
            cd {remote_path(b.repo)} || {{ echo "{MARK}=no such directory"; exit; }}
            git checkout --quiet {shlex.quote(b.branch)} 2>&1 \\
                || {{ echo "{MARK}=cannot check out {b.branch}"; exit; }}
            git pull --quiet --ff-only 2>&1 \\
                || {{ echo "{MARK}=pull --ff-only failed"; exit; }}
            echo "HEAD=$(git rev-parse HEAD)"
            echo "SHORT=$(git rev-parse --short HEAD)"
            echo "DIRTY=$(git status --porcelain | wc -l | tr -d ' ')"
            echo "{MARK}=ok"
            """,
        )
        facts = facts_from(out)
        if (verdict := facts.get(MARK, "")) != "ok":
            problems.append(
                f"{b.platform}: {verdict or 'the update said nothing'} "
                f"({b.branch} in {b.repo} on {b.target})\n       {out}"
            )
            continue
        # Clean again afterwards. A fast-forward cannot dirty a clean tree, but
        # a checkout crossing a mode change or a submodule can.
        if facts.get("DIRTY", "0") != "0":
            problems.append(
                f"{b.platform}: {facts['DIRTY']} file(s) dirty after the update"
            )
            continue
        drift = "" if facts["HEAD"] == here else "  (differs from this checkout)"
        say(f"    {b.platform:<14} {b.branch} at {facts['SHORT']}{drift}")

    if problems:
        say()
        for p in problems:
            say(f"    - {p}")
        die("no builder was started.")


# --- the build ---------------------------------------------------------------


def build_one(b: Builder, target: str, version: str) -> str | None:
    """Build on one machine. Returns a complaint, or None if it worked."""
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{b.platform}.log"

    # No `set -e`, and the verdict comes back as a printed line: over ssh an
    # exit status describes the shell rather than the work.
    script = f"""
    cd {remote_path(b.repo)} || {{ echo "{MARK}=no such directory"; exit; }}
    echo "== $(hostname) $(uname -m), {b.branch} at $(git rev-parse --short HEAD)"
    if make {target}
    then echo "{MARK}=ok"
    else echo "{MARK}=make {target} failed ($?)"
    fi
    """

    started = time.monotonic()
    with log.open("w", encoding="utf-8") as fh:
        process = subprocess.Popen(
            [*SSH, b.target, "bash -l -s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(script)
        process.stdin.close()

        # A heartbeat rather than the output itself. `make payload-container`
        # is tens of thousands of lines and two of them interleaved is noise;
        # silence for two hours is worse. The log has everything.
        lines, last, verdict = 0, started, ""
        for lines, line in enumerate(process.stdout, start=1):
            fh.write(line)
            if line.startswith(f"{MARK}="):
                verdict = line.split("=", 1)[1].strip()
            now = time.monotonic()
            if now - last >= HEARTBEAT_SECONDS:
                fh.flush()
                say(
                    f"    {b.platform:<14} {mmss(now - started)}"
                    f"  {lines} lines  {shorten(line)}"
                )
                last = now
        process.wait()

    elapsed = mmss(time.monotonic() - started)
    if not verdict:
        return (
            f"{b.platform}: stopped after {elapsed} without saying how.\n"
            f"       The connection dropped, or bash never reached the end.\n"
            f"       {log}\n{tail(log)}"
        )
    if verdict != "ok":
        return f"{b.platform}: {verdict} after {elapsed}\n       {log}\n{tail(log)}"
    return verify_artifact(b, version, elapsed, log)


def verify_artifact(b: Builder, version: str, elapsed: str, log: Path) -> str | None:
    """Ask the builder whether the tarball is really there, and really a payload."""
    dist = remote_path(b.dist) if b.dist else f"{remote_path(b.repo)}/out/dist"
    name = f"core-{b.platform}.tar.gz"
    out = ssh_capture(
        b.target,
        f"""
        f={dist}/{version}/{name}
        if [ -f "$f" ]; then echo "BYTES=$(wc -c < "$f" | tr -d ' ')"
        else echo "MISSING=$f"; fi
        """,
    )
    facts = facts_from(out)
    if "BYTES" not in facts:
        return (
            f"{b.platform}: make said it worked and {name} is not there.\n"
            f"       {out}\n       {log}"
        )
    if (size := int(facts["BYTES"])) < MIN_CORE_BYTES:
        return (
            f"{b.platform}: {name} is {size} bytes, which is not a payload.\n"
            f"       {log}"
        )
    say(f"    {b.platform:<14} done in {elapsed}, {size // 1048576} MB")
    return None


def cmd_build(builders: list[Builder], target: str) -> None:
    remotes = [b for b in builders if b.remote]
    if not remotes:
        say("    no remote builders; nothing to do")
        return
    version = payload_version()
    step(f"building on {len(remotes)} machine(s), in parallel")
    for b in remotes:
        say(f"    {b.platform:<14} {b.target}  ->  tmp/remote/{b.platform}.log")

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(remotes)) as pool:
        results = list(pool.map(lambda b: build_one(b, target, version), remotes))

    if failures := [r for r in results if r]:
        say()
        for f in failures:
            say(f"    - {f}")
        die(f"{len(failures)} of {len(remotes)} builder(s) failed.")


# --- the rest, which origin.sh already does ----------------------------------


def origin(command: str) -> None:
    step(f"origin.sh {command}")
    argv = ["sh", str(REPO / "build" / "origin.sh"), command]
    if subprocess.run(argv, check=False).returncode != 0:
        die(f"origin.sh {command} failed.")


# --- small helpers -----------------------------------------------------------


def mmss(seconds: float) -> str:
    return f"{int(seconds) // 60:d}m{int(seconds) % 60:02d}s"


def shorten(line: str) -> str:
    text = line.strip()
    if len(text) <= HEARTBEAT_WIDTH:
        return text
    return text[:HEARTBEAT_WIDTH] + "..."


def tail(log: Path, lines: int = 25) -> str:
    try:
        text = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(f"       | {line}" for line in text[-lines:])


def print_builders(default_dist: str) -> None:
    """The inventory as tab-separated lines, which is what origin.sh consumes.

    One parser for one file. origin.sh used to read a positional text format of
    its own, and two readers of one inventory is two chances to disagree.
    """
    for b in read_builders():
        flag = "neutral" if b.neutral else ""
        print("\t".join([b.platform, b.target, b.dist or default_dist, flag]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "phases",
        nargs="*",
        choices=[*PHASES, []],
        help=f"stages to run (default: all of {', '.join(PHASES)})",
    )
    parser.add_argument(
        "--target",
        default="payload-container",
        help="the make target to run on each builder (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan and run nothing"
    )
    parser.add_argument(
        "--print-builders", metavar="DEFAULT_DIST", help=argparse.SUPPRESS
    )
    args = parser.parse_args()

    if args.print_builders is not None:
        print_builders(args.print_builders)
        return

    phases = args.phases or list(PHASES)
    builders = read_builders()

    if args.dry_run:
        step("the plan")
        say(f"    phases   {', '.join(phases)}")
        say(f"    payload  {payload_version()}")
        say(f"    here     {local_branch()} at {local_head()[:9]}")
        for b in builders:
            where = f"{b.target}:{b.repo} ({b.branch})" if b.remote else "local"
            say(f"    {b.platform:<14} {where}{'  neutral' if b.neutral else ''}")
        return

    precheck(builders, phases)
    if "update" in phases:
        cmd_update(builders)
    if "build" in phases:
        cmd_build(builders, args.target)
    for command in ("collect", "push", "check"):
        if command in phases:
            origin(command)

    step("done")
    say("    the last word belongs to a machine that never built it:")
    say("        libera --payload-install")


if __name__ == "__main__":
    main()
