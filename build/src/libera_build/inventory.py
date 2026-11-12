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

from libera_build import repo
from libera_build.containers import DOCKER_ARCH
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

KNOWN_KEYS = frozenset({"platform", "target", "dist", "neutral", "repo"})
DEFAULT_REPO = "~/liberasuite"

# A platform's first half, as `platform.system()` says it on that machine.
SYSTEMS = {"macos": "Darwin", "linux": "Linux", "windows": "Windows"}


@dataclass(frozen=True)
class Builder:
    platform: str  # core-<platform>.tar.gz, e.g. linux-x86_64
    target: str  # an ssh target, or "local"
    dist: str | None  # the parent of the per-version directories
    neutral: bool  # the one that supplies editors.tar.gz and fonts-core.tar.gz
    repo: str  # the checkout on that machine

    @property
    def remote(self) -> bool:
        return self.target != "local"

    @property
    def arch(self) -> str | None:
        """The docker arch this builder builds, from the tail of its platform.

        buildbox.py defaults ARCH to amd64 whatever the host is, deliberately:
        on a Mac you want the amd64 core under Rosetta. On a builder whose whole
        job is its own architecture that default is wrong, and it fails late
        and obscurely -- `image ... does not provide the specified platform
        (linux/amd64)` at a COPY step, after several minutes of installing
        arm64 packages. So the platform each builder is *for* decides the flag.
        """
        return DOCKER_ARCH.get(self.platform.rsplit("-", 1)[-1])


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
        out.append(
            Builder(
                platform=entry["platform"],
                target=entry["target"],
                dist=entry.get("dist"),
                neutral=bool(entry.get("neutral", False)),
                repo=entry.get("repo", defaults.get("repo", DEFAULT_REPO)),
            )
        )

    if len(neutrals := [b.platform for b in out if b.neutral]) > 1:
        msg = (
            f"{source}: {len(neutrals)} builders marked neutral "
            f"({', '.join(neutrals)}).\n"
            "  editors.tar.gz and fonts-core.tar.gz are not byte-identical\n"
            "  between machines, so exactly one builder supplies them."
        )
        raise RefusedError(msg)
    return out


def gui_remotes(builders: list[Builder]) -> list[Builder]:
    """The remote Linux and Windows builders: the ones `release check downloads` opens a
    window on. A Mac has nothing published to open: Homebrew and pip build it."""
    return [
        b
        for b in builders
        if b.remote and b.platform.startswith(("linux-", "windows-"))
    ]


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


def dist_of(b: Builder) -> str:
    """The parent of the per-version directories on that builder, `~` left for
    whoever reaches it to expand: its `dist`, else where its build writes them.

    `ship` builds a Linux core with `container run payload`, into
    $BUILD_ROOT/linux-<arch> there, and anything else with `payload build`, into
    $BUILD_ROOT. A remote builder's $BUILD_ROOT is taken to be its system's
    default; this machine's is whatever it is here.
    """
    if b.dist:
        return b.dist
    if not b.remote:
        return str(repo.build_root() / "out" / "dist")
    system, _, _ = b.platform.partition("-")
    root = repo.default_build_root(SYSTEMS.get(system, system))
    if system == "linux":
        return f"{root}/linux-{b.arch}/out/dist"
    return f"{root}/out/dist"
