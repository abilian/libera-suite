"""The repository, and what git says about a checkout of it.

Every function takes the checkout's root rather than assuming this one, so the
tests can drive a scratch repository with them.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from libera_build.report import RefusedError

# Paths in a checkout, from its root: each is spelt here once.
PAYLOAD_VERSION = Path("src", "libera", "payload", "payload.version")
BUILDERS = Path("build", "builders.toml")
PINS = Path("build", "upstream", "pins.toml")
PATCHES = Path("build", "upstream", "patches")  # a directory per pinned repo


def find_repo() -> Path:
    """The repository root: the first directory up with the payload version file.

    Walked to, never counted: this file moved once already, from build/lb.py to
    build/src/libera_build/.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / PAYLOAD_VERSION).is_file():
            return parent
    msg = f"no repository above {here}"
    raise RuntimeError(msg)


REPO = find_repo()

# $BUILD_ROOT unset, by `platform.system()`: build/engine/common.sh's defaults,
# restated until the build engine scripts that read them are ported. An
# external case-sensitive volume on the Mac, because V8 needs one and the
# internal disk is not. Short on Windows, because V8's checkout is deep enough
# to meet the 260-character limit from under a home directory.
DEFAULT_BUILD_ROOTS = {
    "Darwin": "/Volumes/T7-EXT-2T/euro-office-build",
    "Windows": "C:/b",
}
LINUX_BUILD_ROOT = "~/euro-office-build"


def default_build_root(system: str) -> str:
    """$BUILD_ROOT's default on a system, `~` unexpanded: it may be a builder's."""
    return DEFAULT_BUILD_ROOTS.get(system, LINUX_BUILD_ROOT)


def build_root() -> Path:
    """Where the payload's sources and builds live: $BUILD_ROOT, else this
    system's default."""
    if found := os.environ.get("BUILD_ROOT"):
        return Path(found)
    return Path(default_build_root(platform.system())).expanduser()


def dist(version: str) -> Path:
    """$BUILD_ROOT/out/dist/<version>: where dist.sh writes a payload version's
    artifacts on this machine."""
    return build_root() / "out" / "dist" / version


def git(root: Path, *args: str) -> str:
    """What git printed, its standard output only; refused, with what it said,
    if it failed. Its errors once read as an answer: `branch -r --contains`
    failing printed to stderr, and a commit no remote had passed as pushed."""
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        msg = f"git {' '.join(args)} failed in {root}:\n  {done.stderr.strip()}"
        raise RefusedError(msg)
    return done.stdout


def head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").strip()


def branch(root: Path) -> str:
    return git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()


def dirty(root: Path) -> list[str]:
    out = git(root, "status", "--porcelain")
    return [line for line in out.splitlines() if line.strip()]


def on_a_remote(root: Path) -> bool:
    """Whether a remote has this commit, after asking every remote."""
    git(root, "fetch", "--quiet", "--all")
    return bool(git(root, "branch", "-r", "--contains", "HEAD").strip())
