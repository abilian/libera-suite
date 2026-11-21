"""The canary: our patch queues against upstream's main, before a sync.

A sync moved the pins five weeks at once on 2026-11-19, and the queues, the
engine's loader and its API snapshot all had to follow at the same time. Run
weekly, this says what a sync would meet while it is a week's drift:

- each patch against upstream's head: it applies, it is already upstream (a
  patch we sent was merged: drop it at the sync), or it conflicts;
- whether the JavaScript builds, with the patches that apply;
- what the engine's tests in Node make of it (E1's suites, E2's API snapshot,
  E3's names check, our patches' own tests).

It builds in a build root of its own, `<build root>-canary`, so nothing it
fetches or builds reaches the trees the releases use. Core is fetched and its
queue judged, but not compiled: the payload takes x2t from the main build
root, which the JavaScript needs only to write its themes and font index.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import tomllib

from libera_build import repo, sources
from libera_build.report import RefusedError

# The repositories that move on upstream's main. The fonts, the blanks and the
# dictionaries are pinned to a desktop release and stay there.
MOVING = ("core", "sdkjs", "web-apps")
ENGINE_TEST = "tests/b_integration/payload/test_engine.py"
APPLIES, UPSTREAM, CONFLICTS = "applies", "already upstream", "conflicts"


def repo_url(pins: dict, name: str) -> str:
    """Where build.sh fetches `name` from: its own address, else upstream's."""
    return pins.get("urls", {}).get(name) or f"{pins['remote']['base']}/{name}.git"


def at_heads(pins_text: str, heads: dict[str, str], branch: str) -> str:
    """pins.toml's text with each repository in `heads` at that revision."""
    for name, sha in heads.items():
        pins_text, found = re.subn(
            rf'^({re.escape(name)}\s*=\s*")[0-9a-f]{{40}}".*$',
            rf'\g<1>{sha}"  # {branch}, for the canary',
            pins_text,
            flags=re.MULTILINE,
        )
        if found != 1:
            msg = f"pins.toml has no single line for {name}"
            raise RefusedError(msg)
    return pins_text


def head_of(url: str, branch: str) -> str:
    done = subprocess.run(
        ["git", "ls-remote", url, f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    sha = done.stdout.split()[0] if done.stdout.split() else ""
    if done.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        msg = f"no {branch} at {url}: {done.stderr.strip() or 'no such branch'}"
        raise RefusedError(msg)
    return sha


def applies(tree: Path, env: dict[str, str], patch: bytes, *how: str) -> bool:
    """Whether git apply takes `patch` into the scratch index (with --check,
    only whether it would). git's no is exit 1; anything else, a failure."""
    done = subprocess.run(
        [*sources.git(tree), "apply", "--cached", "--whitespace=nowarn", *how],
        input=patch,
        env=env,
        capture_output=True,
        check=False,
    )
    if done.returncode not in {0, 1}:
        said = done.stderr.decode(errors="replace").strip()
        msg = f"git apply in {tree} failed ({done.returncode}): {said}"
        raise RefusedError(msg)
    return done.returncode == 0


def classify(tree: Path, head: str, queue: list[Path]) -> list[tuple[Path, str]]:
    """Each patch of `queue`, in order, against `head` plus the patches before
    it that applied. Reading the clone only, as the source check does."""
    verdicts = []
    with tempfile.TemporaryDirectory() as scratch:
        env = sources.scratch_env(tree, Path(scratch))
        sources.git_out(tree, "read-tree", head, env=env)
        for patch in queue:
            data = patch.read_bytes()
            if applies(tree, env, data):
                verdicts.append((patch, APPLIES))
            elif applies(tree, env, data, "--check", "--reverse"):
                verdicts.append((patch, UPSTREAM))
            else:
                verdicts.append((patch, CONFLICTS))
    return verdicts


def script(name: str, *args: str, env: dict[str, str]) -> bool:
    """One of build/engine's scripts, its output shown; whether it passed."""
    argv = ["sh", str(repo.REPO / "build" / "engine" / name), *args]
    print(f"+ {' '.join(argv)}", flush=True)
    return subprocess.run(argv, env=os.environ | env, check=False).returncode == 0


def engine_tests(env: dict[str, str]) -> bool:
    """The engine's tests in Node, through the test that puts them in `make
    test`, on the canary's payload. A skip counts as a failure: it means the
    tests did not look at what the canary built."""
    argv = ["uv", "run", "--no-sync", "pytest", "-q", "-rs", "-p", "no:cacheprovider"]
    done = subprocess.run(
        [*argv, ENGINE_TEST],
        cwd=repo.REPO,
        env=os.environ | env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(done.stdout[-6000:], done.stderr[-2000:], sep="\n")
    return done.returncode == 0 and bool(re.search(r"\b1 passed\b", done.stdout))


def write_pins(into: Path, branch: str) -> dict[str, str]:
    """The canary's pins.toml: ours, the moving repositories at the head of
    `branch` upstream. Their heads, and how far each moved, said."""
    text = (repo.REPO / repo.PINS).read_text(encoding="utf-8")
    pins = tomllib.loads(text)
    heads = {name: head_of(repo_url(pins, name), branch) for name in MOVING}
    into.mkdir(parents=True, exist_ok=True)
    (into / "pins.toml").write_text(at_heads(text, heads, branch), encoding="utf-8")
    print(f"==> the canary, in {into}")
    for name, sha in heads.items():
        pinned = pins["repos"][name]
        moved = "unchanged" if sha == pinned else f"pinned {pinned[:10]}"
        print(f"    {name:<9} {branch} {sha[:10]}  ({moved})")
    return heads


def judge(into: Path, heads: dict[str, str]) -> dict[str, list[tuple[Path, str]]]:
    """Each queue against its head, fetched bare into the canary; the patches
    that apply copied to the canary's own queue, which is what gets built."""
    queue = into / "patches"
    shutil.rmtree(queue, ignore_errors=True)
    report = {}
    for name, head in heads.items():
        ours = sorted((repo.REPO / repo.PATCHES / name).glob("*.patch"))
        report[name] = classify(into / "src" / name, head, ours)
        (queue / name).mkdir(parents=True)
        for patch, verdict in report[name]:
            if verdict == APPLIES:
                shutil.copy2(patch, queue / name / patch.name)
    return report


def verdict(
    branch: str, report: dict[str, list[tuple[Path, str]]], built: bool, tested: bool
) -> int:
    """What a sync would meet, said; 1 when it would need work beyond
    dropping the patches upstream merged."""
    print(f"\n==> upstream's {branch}, against our queues")
    for name, verdicts in report.items():
        counts = {
            v: sum(1 for _, x in verdicts if x == v)
            for v in (APPLIES, UPSTREAM, CONFLICTS)
        }
        print(f"    {name:<9} " + ", ".join(f"{n} {v}" for v, n in counts.items()))
        for patch, said in verdicts:
            if said != APPLIES:
                print(f"        {said:<16} {patch.name}")
    print(f"    JavaScript   {'built' if built else 'FAILED (above)'}")
    ran = "pass" if tested else "FAILED (above)" if built else "not run"
    print(f"    engine tests {ran}")
    if any(v == CONFLICTS for vs in report.values() for _, v in vs) or not tested:
        print("==> FAIL: a sync would need work now")
        return 1
    print("==> PASS: a sync would need no more than dropping what upstream merged")
    return 0


def run(main: Path, into: Path, branch: str) -> int:
    """The whole canary, from the main build root's x2t and clones."""
    core_bin = main / "out" / "core" / "bin"
    if not any(core_bin.glob("x2t*")):
        msg = (
            f"no x2t in {core_bin}: the canary takes the main build root's\n"
            "  lb payload build    (or set BUILD_ROOT to a tree that has one)"
        )
        raise RefusedError(msg)
    heads = write_pins(into, branch)
    tree = {"BUILD_ROOT": str(into), "PINS": str(into / "pins.toml")}
    fetching = {**tree, "MIRROR": str(main / "src")}
    # The heads, nothing applied: what each patch is judged against.
    (into / "no-patches").mkdir(exist_ok=True)
    bare = {**fetching, "PATCHES": str(into / "no-patches")}
    if not script("build.sh", "fetch", *MOVING, env=bare):
        msg = "could not fetch upstream's heads"
        raise RefusedError(msg)
    report = judge(into, heads)
    # Everything fetched again, with the patches that apply: what is built.
    built = script(
        "build.sh", "fetch", env={**fetching, "PATCHES": str(into / "patches")}
    )
    built = built and script("payload.sh", env={**tree, "CORE_BIN": str(core_bin)})
    payload = {**tree, "LIBERA_PAYLOAD": str(into / "out" / "payload")}
    return verdict(branch, report, built, built and engine_tests(payload))
