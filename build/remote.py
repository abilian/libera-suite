#!/usr/bin/env python3
"""Build and publish a whole release, from here, using the remote builders.

    python3 build/remote.py                  every phase, in order: a release
    python3 build/remote.py build            just the remote builds
    python3 build/remote.py collect push     skip the building
    python3 build/remote.py --dry-run        print the plan, run nothing
    python3 build/remote.py --only linux-arm64 bundles     one builder, one phase

The phases, in the order they have to happen:

    update    git pull each builder onto its branch, and check it is clean
    native    the macOS core and its tarballs, here
    build     the Linux cores, on their own machines, in parallel
    collect   scp every core here and restamp the manifest over all of them
    push      upload the payload to the origin
    check     fetch it all back with no token and verify every hash
    bundles   the two .flatpak bundles, each on a machine of its architecture
    wheel     the test suite, then the wheel
    publish   the wheel to PyPI, the bundles and install.sh to the origin
    verify    read the *published* wheel back and check it against the origin

The builders come from build/builders.toml. `origin.sh` reads the same file
through `--print-builders` below, so there is one inventory of machines and one
parser for it rather than two of each.

Why a script at all. A release is a dozen commands on three machines, several
of which take hours, and the failure that costs the most is the quiet one: a
builder that built the wrong commit, or wrote an artifact that is there and
empty. So each stage asserts on what the machine printed, and says which
machine it is talking about.

The builds run in parallel. Two builders of two hours each, one after the
other, is an afternoon that did not need to be.

`publish` is the one phase that cannot be undone: PyPI does not accept a
version twice. It stops and asks unless --yes says otherwise.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import shlex
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import tomllib

REPO = Path(__file__).resolve().parent.parent
BUILDERS = REPO / "build" / "builders.toml"
LOGS = REPO / "tmp" / "remote"

# Non-interactive, and it should say so quickly rather than sit at a password
# prompt inside a thread whose output nobody is watching.
#
# ServerAlive* because a build is hours and the connection carries it: a NAT or
# a firewall that drops an idle session takes the build with it, and the
# symptom is a log that stops mid-compile with no error in it. Six missed
# thirty-second probes is three minutes of genuine silence before giving up.
#
# It does not survive the *local* process ending -- a closed terminal or a
# sleeping laptop still kills the build. Run this under tmux or screen for
# anything long.
SSH = [
    "ssh",
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "ServerAliveInterval=30",
    "-o",
    "ServerAliveCountMax=6",
]

PHASES = (
    "update",
    "native",
    "build",
    "collect",
    "push",
    "check",
    "bundles",
    "wheel",
    "publish",
    "verify",
)

# The phases that reach outside this machine and cannot be taken back. PyPI
# refuses a version it has already seen, so a mistaken `publish` costs a
# version number rather than a retry.
IRREVERSIBLE = ("publish",)

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

# A bundle carries the application, the payload and the wheels; the amd64 one
# measured 81 MB. The same argument as MIN_CORE_BYTES, one order down.
MIN_BUNDLE_BYTES = 20 * 1024 * 1024

KNOWN_KEYS = {"platform", "target", "dist", "neutral", "repo", "branch"}

# docker.sh defaults ARCH to amd64 whatever the host is, deliberately: on a Mac
# you want the amd64 core under Rosetta and pass ARCH=arm64 for the native one.
# On a builder whose whole job is its own architecture that default is wrong,
# and it fails late and obscurely -- `image ... does not provide the specified
# platform (linux/amd64)` at a COPY step, after several minutes of installing
# arm64 packages. So the platform each builder is *for* decides the flag.
DOCKER_ARCH = {"x86_64": "amd64", "arm64": "arm64", "aarch64": "arm64"}

# What `uname -m` says on a machine of that architecture.
UNAME_ARCH = {"amd64": {"x86_64", "amd64"}, "arm64": {"arm64", "aarch64"}}


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

    @property
    def arch(self) -> str | None:
        """The docker arch this builder builds, from the tail of its platform."""
        return DOCKER_ARCH.get(self.platform.rsplit("-", 1)[-1])


# What each phase brings to run_builds: the make target for a given builder,
# and the check that says whether it produced anything. Plain assignments and
# not `type` statements: ruff.toml targets py310, because build/ also runs on
# builders whose python3 is whatever the distribution gave them.
TargetFor = Callable[[Builder], str]
Verify = Callable[[Builder, str, Path], "str | None"]


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


def app_version() -> str:
    """The application version, which is not the payload's.

    They move independently on purpose -- a host fix should not force a 120 MB
    re-download -- so the wheel and the Flatpak bundles are named for this one
    and the payload directory on the origin for the other.
    """
    doc = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return str(doc["project"]["version"])


def make(target: str, what: str, env: dict[str, str] | None = None) -> None:
    """Run a make target here, streaming it, and die naming the phase if it fails.

    Unlike a builder over ssh, a local process's exit status means what it
    says, so this one is allowed to believe it.
    """
    say(f"    make {target}")
    done = subprocess.run(
        ["make", *target.split()],
        cwd=REPO,
        env={**os.environ, **(env or {})},
        check=False,
    )
    if done.returncode != 0:
        die(f"{what}: `make {target}` failed ({done.returncode}).")


# --- prechecks ---------------------------------------------------------------
#
# All of them before any of the long work. A missing CDN token is a one-second
# discovery that used to be a two-hour one, because push is the last stage and
# the builds are the first.


def precheck(builders: list[Builder], phases: list[str]) -> None:
    step("before anything long")
    problems: list[str] = []

    needs_token = {"push", "publish"} & set(phases)
    if needs_token and not os.environ.get("CDN_TOKEN"):
        problems.append(
            f"{'/'.join(sorted(needs_token))} needs CDN_TOKEN in the environment"
        )

    say(f"    libera {app_version()}, payload {payload_version()}")
    say(f"    here at {local_head()[:9]} on {local_branch()}")
    if dirty := local_dirty():
        # Not fatal for a build -- the builders pull from the remote and never
        # see this tree -- and fatal for anything published, because the
        # manifest records the commit it was stamped from and a dirty tree
        # names nothing anyone could check.
        published = {"collect", "push", "publish"} & set(phases)
        if published and os.environ.get("ALLOW_DIRTY") != "1":
            # origin.sh push refuses the same thing, and honours the same
            # escape. Both checks exist because they happen at different times:
            # this one costs a second, that one costs the hours in between.
            problems.append(
                f"{len(dirty)} uncommitted file(s) here, and "
                f"{'/'.join(sorted(published))} would stamp a commit that "
                f"describes none of them. Commit first, or ALLOW_DIRTY=1 to "
                f"publish with no reproducible provenance."
            )
        else:
            say(
                f"    note: {len(dirty)} uncommitted file(s) here, which no builder sees"
            )

    if (
        "publish" in phases
        and not (REPO / "src" / "libera" / "manifest.json").is_file()
    ):
        problems.append("publish needs src/libera/manifest.json; run collect first")

    for b in builders:
        if b.remote:
            problems.extend(check_builder(b))
        else:
            say(f"    {b.platform:<14} local, left alone")

    if problems:
        say()
        for p in problems:
            say(f"    - {p}")
        die("nothing was started.")


def check_builder(b: Builder) -> list[str]:
    """Ask one builder about itself, and report what is wrong with the answer."""
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
        return [f"{b.platform}: no answer from {b.target}\n       {out}"]
    if "NOREPO" in facts:
        return [missing_repo(b, out)]

    say(
        f"    {b.platform:<14} {b.target} "
        f"({facts['ARCH']}, {b.repo} at {facts.get('HEAD', '?')})"
    )
    problems = []
    # Cross-building is not what these machines are for: a container built for
    # the other architecture either runs under emulation for hours or fails
    # partway through with a platform mismatch.
    if b.arch and facts["ARCH"] not in UNAME_ARCH[b.arch]:
        problems.append(
            f"{b.platform}: wants {b.arch} and {b.target} reports "
            f"{facts['ARCH']}. Assign it a machine of that architecture."
        )
    # Before the pull, not after. A pull into a dirty tree either refuses or
    # merges over somebody's edits, and neither belongs in a script that is
    # about to run for two hours.
    if facts.get("DIRTY", "0") != "0":
        problems.append(
            f"{b.platform}: {facts['DIRTY']} uncommitted file(s) in "
            f"{b.repo} on {b.target}. Clean it before building."
        )
    return problems


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


def build_one(b: Builder, target: str, verify: Verify) -> str | None:
    """Build on one machine. Returns a complaint, or None if it worked."""
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{b.platform}.log"

    # `target` arrives complete, ARCH included: the caller knows what it is
    # asking for. Appending ARCH here as well produced `ARCH=arm64 ARCH=arm64`,
    # which make forgives and a reader does not.
    #
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
    return verify(b, elapsed, log)


def verify_core(b: Builder, elapsed: str, log: Path) -> str | None:
    """Ask the builder whether the core tarball is really there, and really one.

    Each phase brings its own checker, because a checker that guesses from the
    make target got it wrong: `bundles` once reported a pass after finding the
    core tarball that the *payload* build had left behind, which was a pass
    against something that run never produced.
    """
    version = payload_version()
    dist = remote_path(b.dist) if b.dist else f"{remote_path(b.repo)}/out/dist"
    return check_remote_file(
        b,
        f"{dist}/{version}/core-{b.platform}.tar.gz",
        MIN_CORE_BYTES,
        elapsed,
        log,
    )


def verify_bundle(b: Builder, elapsed: str, log: Path) -> str | None:
    """The bundle is named for the *application* version, not the payload's."""
    name = f"libera-{app_version()}-{b.arch}.flatpak"
    return check_remote_file(
        b,
        f"{remote_path(b.repo)}/build/out/{name}",
        MIN_BUNDLE_BYTES,
        elapsed,
        log,
    )


def check_remote_file(
    b: Builder, path: str, minimum: int, elapsed: str, log: Path
) -> str | None:
    """One remote stat, asserted on the size it printed."""
    out = ssh_capture(
        b.target,
        f"""
        f={path}
        if [ -f "$f" ]; then echo "BYTES=$(wc -c < "$f" | tr -d ' ')"
        else echo "MISSING=$f"; fi
        """,
    )
    facts = facts_from(out)
    name = path.rsplit("/", 1)[-1]
    if "BYTES" not in facts:
        return (
            f"{b.platform}: make said it worked and {name} is not there.\n"
            f"       {out}\n       {log}"
        )
    if (size := int(facts["BYTES"])) < minimum:
        return f"{b.platform}: {name} is {size} bytes, which is not an artifact.\n       {log}"
    say(f"    {b.platform:<14} done in {elapsed}, {size // 1048576} MB")
    return None


def run_builds(
    remotes: list[Builder], target_for: TargetFor, verify: Verify, what: str
) -> None:
    """Run one make target per builder, in parallel, and report every failure."""
    step(f"{what} on {len(remotes)} machine(s), in parallel")
    for b in remotes:
        say(
            f"    {b.platform:<14} {b.target}  make {target_for(b)}"
            f"  ->  tmp/remote/{b.platform}.log"
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(remotes)) as pool:
        results = list(pool.map(lambda b: build_one(b, target_for(b), verify), remotes))

    if failures := [r for r in results if r]:
        say()
        for f in failures:
            say(f"    - {f}")
        die(f"{len(failures)} of {len(remotes)} builder(s) failed.")


def arch_suffix(b: Builder) -> str:
    return f" ARCH={b.arch}" if b.arch else ""


def cmd_build(builders: list[Builder], target: str) -> None:
    remotes = [b for b in builders if b.remote]
    if not remotes:
        say("    no remote builders; nothing to do")
        return
    run_builds(remotes, lambda b: f"{target}{arch_suffix(b)}", verify_core, "building")


# --- the Flatpak bundles ------------------------------------------------------
#
# One per architecture, each on a machine of that architecture. They cannot be
# cross-built: flatpak-builder runs every module inside bubblewrap, whose
# seccomp filter is built for the architecture it is running on, and qemu-user
# does not carry one across. See notes/15-builders.md.


def cmd_bundles(builders: list[Builder]) -> None:
    remotes = [b for b in builders if b.remote and b.arch]
    if not remotes:
        say("    no remote builders that can hold a bundle; nothing to do")
        return
    version = payload_version()

    def target_for(b: Builder) -> str:
        dist = b.dist or f"{b.repo}/out/dist"
        return f"flatpak DIST={dist.replace('~', '$HOME')}/{version}{arch_suffix(b)}"

    run_builds(remotes, target_for, verify_bundle, "bundling")
    fetch_bundles(remotes)


def fetch_bundles(remotes: list[Builder]) -> None:
    """Bring both bundles here, so that one directory holds the whole release."""
    step("collecting the bundles")
    app = app_version()
    dest = REPO / "build" / "out" / "bundles"
    dest.mkdir(parents=True, exist_ok=True)
    problems = []
    for b in remotes:
        name = f"libera-{app}-{b.arch}.flatpak"
        source = f"{b.target}:{b.repo}/build/out/{name}"
        status, out = run_local(["scp", "-q", source, str(dest / name)])
        landed = dest / name
        # scp reports success for a transfer that wrote nothing often enough
        # that the size is the thing to believe.
        if (
            status != 0
            or not landed.is_file()
            or landed.stat().st_size < MIN_BUNDLE_BYTES
        ):
            problems.append(
                f"{b.platform}: {source} did not arrive\n       {out.strip()}"
            )
            continue
        say(f"    {b.platform:<14} {name}  {landed.stat().st_size // 1048576} MB")
    if problems:
        say()
        for problem in problems:
            say(f"    - {problem}")
        die("the bundles are not all here.")


# --- the phases that run here -------------------------------------------------


def cmd_native(builders: list[Builder]) -> None:
    """The macOS core, on this machine, because there is nowhere else for it.

    `payload-dist` re-tars a core that is already built and takes a minute;
    building one takes an afternoon and is `make payload-all`. Which of the two
    is wanted is decided by whether the core is there, and said out loud.
    """
    local = [b for b in builders if not b.remote]
    if not local:
        say("    no local builder in builders.toml; nothing to do here")
        return
    step("the native core, here")
    if sys.platform != "darwin":
        say(f"    this is {sys.platform}, not a Mac; skipping")
        return
    make("payload-dist", "native")


def cmd_wheel() -> None:
    """The suite, then the wheel -- in that order, and the order is the point.

    The wheel carries the manifest, which `collect` has just restamped over
    every core. Building it before the suite has run means publishing a wheel
    nothing has exercised; running the suite before `collect` means testing
    against the previous payload.
    """
    step("the suite, then the wheel")
    make("verify", "wheel")
    make("build", "wheel")

    dist = REPO / "dist"
    wheels = sorted(dist.glob(f"libera-{app_version()}-*.whl"))
    if not wheels:
        die(
            f"make build reported success and there is no "
            f"libera-{app_version()}-*.whl in {dist}."
        )
    for wheel in wheels:
        say(f"    {wheel.name}  {wheel.stat().st_size // 1024} kB")


def cmd_publish(yes: bool) -> None:
    """PyPI, then the bundles and install.sh. The one phase with no undo.

    PyPI refuses a version it has already seen, even after a yank, so a
    mistaken publish costs a version number. It asks unless told not to, and it
    asks on /dev/tty: this script is sometimes run under tmux with its output
    redirected, and a prompt nobody can see is a hang.
    """
    step(f"publishing libera {app_version()}")
    if not yes:
        say("    PyPI accepts a version once. There is no undo, and a yank")
        say("    does not free the number.")
        try:
            with Path("/dev/tty").open(encoding="utf-8") as tty:
                say("")
                print(
                    f"    publish {app_version()} to PyPI? [y/N] ", end="", flush=True
                )
                answer = tty.readline().strip().lower()
        except OSError:
            die("no terminal to ask on. Re-run with --yes when you mean it.")
        if answer not in {"y", "yes"}:
            die("nothing was published.")

    make("publish", "publish")
    origin("extras")


def cmd_verify() -> None:
    """Read the *published* wheel back and check it against the origin.

    Not the manifest in this tree, which is correct by construction. `libera`
    0.1.0 went up naming a payload that was rebuilt two days later, and every
    check that existed passed, because each read the copy that agreed with it.
    """
    step("the published wheel against the published payload")
    argv = ["sh", str(REPO / "build" / "origin.sh"), "check"]
    done = subprocess.run(
        argv, cwd=REPO, env={**os.environ, "WHEEL": "pypi"}, check=False
    )
    if done.returncode != 0:
        die(
            "what PyPI serves and what the origin serves do not agree.\n"
            "       This is the check 0.1.0 never had; believe it."
        )


# --- the rest, which origin.sh already does ----------------------------------


def origin(command: str) -> None:
    step(f"origin.sh {command}")
    argv = ["sh", str(REPO / "build" / "origin.sh"), command]
    if subprocess.run(argv, cwd=REPO, check=False).returncode != 0:
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


def run_phases(
    phases: list[str], builders: list[Builder], args: argparse.Namespace
) -> None:
    """Every requested phase, in the one order they can happen in.

    Driven off PHASES rather than off the order they were typed in: `remote.py
    push collect` means the same as `remote.py collect push`, because there is
    only one order in which they work and a command line is a poor place to
    discover that.
    """
    started = time.monotonic()
    actions: dict[str, Callable[[], None]] = {
        "update": lambda: cmd_update(builders),
        "native": lambda: cmd_native(builders),
        "build": lambda: cmd_build(builders, args.target),
        "collect": lambda: origin("collect"),
        "push": lambda: origin("push"),
        "check": lambda: origin("check"),
        "bundles": lambda: cmd_bundles(builders),
        "wheel": cmd_wheel,
        "publish": lambda: cmd_publish(args.yes),
        "verify": cmd_verify,
    }
    for phase in PHASES:
        if phase in phases:
            actions[phase]()

    step(f"done in {mmss(time.monotonic() - started)}")
    if "publish" in phases:
        # A separate repository, so nothing here can keep it in step. Naming
        # the command is the difference between a tap that lags one release
        # and a tap that lags five.
        say("    the Homebrew tap is a separate repository and does not follow:")
        say("        cd ~/projects/homebrew-tap && make update FORMULA=libera")
        say("")
    say("    the last word belongs to a machine that never built it:")
    say("        libera --payload-install")


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
        "--only",
        action="append",
        metavar="PLATFORM",
        help="just this builder; repeatable. Default: all of them",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan and run nothing"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="do not stop to confirm the phases that cannot be undone",
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

    # One platform at a time, because the reasons to build them differ: an
    # arm64 flatpak can only be built on an arm64 machine, and a machine short
    # of disk should not be handed a build just because its neighbour is free.
    if args.only:
        known = {b.platform for b in builders}
        if unknown := sorted(set(args.only) - known):
            die(
                f"no such builder: {', '.join(unknown)}\n  have: {', '.join(sorted(known))}"
            )
        builders = [b for b in builders if b.platform in args.only]

    if args.dry_run:
        step("the plan")
        say(f"    phases   {', '.join(phases)}")
        say(f"    libera   {app_version()}")
        say(f"    payload  {payload_version()}")
        say(f"    here     {local_branch()} at {local_head()[:9]}")
        for b in builders:
            where = f"{b.target}:{b.repo} ({b.branch})" if b.remote else "local"
            say(f"    {b.platform:<14} {where}{'  neutral' if b.neutral else ''}")
        if irreversible := [p for p in IRREVERSIBLE if p in phases]:
            say(f"    note     {', '.join(irreversible)} cannot be undone")
        return

    precheck(builders, phases)
    run_phases(phases, builders, args)


if __name__ == "__main__":
    main()
