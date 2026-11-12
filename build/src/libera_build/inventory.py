"""The builders: build/builders.toml, parsed once, into frozen values.

The file is gitignored, because it is an inventory of machines;
builders.toml.example is the committed template. This is its one reader: the
origin script once read a positional format of its own, and two readers of
one inventory is two chances to disagree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import tomllib

from libera_build.containers import DOCKER_ARCH
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

KNOWN_KEYS = frozenset({"platform", "target", "repo"})
DEFAULT_REPO = "~/liberasuite"

# A platform's first half, as `platform.system()` says it on that machine.
SYSTEMS = {"macos": "Darwin", "linux": "Linux", "windows": "Windows"}


@dataclass(frozen=True)
class Builder:
    platform: str  # what it builds for, e.g. linux-x86_64
    target: str  # an ssh target, or "local"
    repo: str  # the checkout on that machine

    @property
    def remote(self) -> bool:
        return self.target != "local"

    @property
    def os(self) -> str:
        """linux, macos or windows: the platform's first half."""
        return self.platform.partition("-")[0]

    @property
    def arch(self) -> str:
        """The docker arch this builder builds, from the tail of its platform.

        A container built for the wrong architecture fails late and
        obscurely -- `image ... does not provide the specified platform
        (linux/amd64)` at a COPY step, after several minutes of installing
        arm64 packages. So the platform each builder is *for* decides the
        flag, not the host it happens to run on.
        """
        return arch_of(self.platform)


def arch_of(platform: str) -> str:
    """amd64 or arm64, from a platform such as linux-x86_64."""
    return DOCKER_ARCH[platform.rpartition("-")[2]]


def platform_problem(platform: str) -> str | None:
    """Why `platform` is not one a builder can be, or None. A typo once read
    as no architecture at all, which skipped the check that a builder is the
    machine it says, and built a path into linux-None."""
    system, _, arch = platform.partition("-")
    if system in SYSTEMS and arch in DOCKER_ARCH:
        return None
    return (
        f"platform {platform!r} is not <{'|'.join(SYSTEMS)}>-<arch>, "
        f"the arch one of {', '.join(DOCKER_ARCH)}"
    )


def read(path: Path) -> list[Builder]:
    if not path.is_file():
        msg = (
            f"no builder list at {path}\n"
            f"  copy build/builders.toml.example to {path.name} and fill it in."
        )
        raise RefusedError(msg)
    return parse(path.read_text(encoding="utf-8"), str(path))


def parse(text: str, source: str) -> list[Builder]:
    """Every builder in the file, or the first reason the file is wrong."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        msg = f"{source}: {e}"
        raise RefusedError(msg) from e

    defaults = doc.get("defaults", {})
    entries = doc.get("builders", [])
    if not entries:
        msg = f"{source}: no [[builders]] entries"
        raise RefusedError(msg)

    out = []
    for i, entry in enumerate(entries, start=1):
        if missing := [k for k in ("platform", "target") if k not in entry]:
            msg = f"{source}: builder {i} has no {' or '.join(missing)}"
            raise RefusedError(msg)
        if unknown := sorted(set(entry) - KNOWN_KEYS):
            msg = f"{source}: builder {entry['platform']} has unknown key(s) {unknown}"
            raise RefusedError(msg)
        if problem := platform_problem(entry["platform"]):
            msg = f"{source}: builder {i}: {problem}"
            raise RefusedError(msg)
        out.append(
            Builder(
                platform=entry["platform"],
                target=entry["target"],
                repo=entry.get("repo", defaults.get("repo", DEFAULT_REPO)),
            )
        )
    return out


def gui_remotes(builders: list[Builder]) -> list[Builder]:
    """The remote Linux and Windows builders: the ones `release check downloads` opens a
    window on. A Mac has nothing published to open: Homebrew and pip build it."""
    return [b for b in builders if b.remote and b.os != "macos"]


def narrow(builders: list[Builder], only: list[str]) -> list[Builder]:
    """The builders `--only` names, refusing one that is not in the file."""
    if not only:
        return builders
    known = {b.platform for b in builders}
    if unknown := sorted(set(only) - known):
        msg = (
            f"no such builder: {', '.join(unknown)}\n  have: {', '.join(sorted(known))}"
        )
        raise RefusedError(msg)
    return [b for b in builders if b.platform in only]
