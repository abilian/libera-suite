"""Containers: which engine, which image name, and how to run one.

One definition of what four scripts each worked out for themselves: docker
or podman, an image name the engine will not guess at, the bind mounts, and
the flags that SELinux and a terminal ask for. The command line is built by a
pure function, so what a container is started with is testable without
starting one.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from libera_build.report import RefusedError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Docker on a Mac, because Docker Desktop shares the home directory across for
# you and podman would want a VM of its own; podman first elsewhere. ENGINE=
# overrides either way. Switching engines on a tree the other one built is the
# thing to know: its files carry uids this engine cannot write. See
# notes/08-build.md.
ORDER = {"Darwin": ("docker", "podman")}
DEFAULT_ORDER = ("podman", "docker")


def choose_engine(
    env: Mapping[str, str],
    system: str,
    which: Callable[[str], str | None] = shutil.which,
) -> str:
    """The engine to use: ENGINE if set, else the first installed in this
    system's order, else docker, so that the failure names the common one."""
    if env.get("ENGINE"):
        return env["ENGINE"]
    for name in ORDER.get(system, DEFAULT_ORDER):
        if which(name):
            return name
    return "docker"


# Every spelling of the two architectures, to docker's. `uname -m` says x86_64,
# or aarch64 (arm64 on a Mac); a platform, as in core-linux-x86_64.tar.gz, says
# x86_64 or arm64; docker and the options here say amd64 or arm64.
DOCKER_ARCH = {
    "amd64": "amd64",
    "x86_64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
}
# And from docker's to a platform's.
PLATFORM_ARCH = {"amd64": "x86_64", "arm64": "arm64"}


def docker_platform(arch: str) -> str:
    """linux/amd64 or linux/arm64, from any spelling of the architecture."""
    if arch not in DOCKER_ARCH:
        msg = f"no such architecture: {arch} (amd64 or arm64)"
        raise RefusedError(msg)
    return f"linux/{DOCKER_ARCH[arch]}"


def linux_platform(arch: str) -> str:
    """linux-x86_64 or linux-arm64, the platform a core is named for."""
    return f"linux-{PLATFORM_ARCH[DOCKER_ARCH[arch]]}"


def host_arch() -> str:
    """This machine's architecture, as docker spells it."""
    return DOCKER_ARCH.get(platform.machine(), "amd64")


@dataclass(frozen=True)
class Mount:
    source: Path | str  # a directory, or a named volume
    target: str
    read_only: bool = False

    def flag(self) -> str:
        return f"{self.source}:{self.target}{':ro' if self.read_only else ''}"


@dataclass(frozen=True)
class Run:
    """One container to run: what, on which architecture, with what around it."""

    image: str
    command: tuple[str, ...]
    arch: str
    mounts: tuple[Mount, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    workdir: str | None = None
    interactive: bool = False
    extra: tuple[str, ...] = ()  # more `run` options, before the image


@dataclass(frozen=True)
class Engine:
    name: str  # docker or podman
    # SELinux denies a container a bind mount it has not relabelled, and what
    # runs inside then fails with no output at all: fedora.zt runs enforcing.
    selinux: bool = field(default_factory=lambda: Path("/sys/fs/selinux").is_dir())

    @classmethod
    def here(cls) -> Engine:
        return cls(choose_engine(os.environ, platform.system()))

    def refuse_remote(self) -> None:
        """Refuse an engine that runs on another machine.

        Every command here bind-mounts this tree, and an engine reached
        through a docker context or DOCKER_HOST over ssh or tcp mounts the
        paths of the machine it runs on: an x86_64 one also builds an arm64
        image no further than "exec format error".
        """
        if host := remote_host(self.name, os.environ):
            msg = (
                f"{self.name} runs on {host}, not on this machine, so it cannot"
                " mount this tree.\n"
                "  on a builder:  lb on linux-x86_64 COMMAND...\n"
                "  or, here:      docker context use orbstack (or desktop-linux)"
            )
            raise RefusedError(msg)

    def image(self, name: str) -> str:
        """An image these scripts built, named the way the engine wants.

        Docker takes a bare name and reads it as docker.io/library/<name>.
        Podman refuses to guess: an unqualified name goes to its search list
        and, interactively, to a menu of registries, none of which can hold an
        image built here a moment ago. Podman stores those under localhost/.
        A name that already carries a registry is left as it is.
        """
        if self.name == "podman" and "/" not in name:
            return f"localhost/{name}"
        return name

    def run_argv(self, run: Run) -> list[str]:
        """The command line that runs `run` in a throwaway container."""
        argv = [self.name, "run", "--rm", "--platform", docker_platform(run.arch)]
        if self.selinux:
            argv += ["--security-opt", "label=disable"]
        if run.interactive:
            argv.append("-it")
        for mount in run.mounts:
            argv += ["-v", mount.flag()]
        for key, value in run.env.items():
            argv += ["-e", f"{key}={value}"]
        if run.workdir:
            argv += ["-w", run.workdir]
        return [*argv, *run.extra, run.image, *run.command]

    def build_argv(self, image: str, context: Path, *, arch: str) -> list[str]:
        return [
            self.name,
            "build",
            "--platform",
            docker_platform(arch),
            "-t",
            image,
            str(context),
        ]

    def has_image(self, image: str) -> bool:
        done = subprocess.run(
            [self.name, "image", "inspect", image], capture_output=True, check=False
        )
        return done.returncode == 0


def remote_host(
    name: str,
    env: Mapping[str, str],
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str | None:
    """Where docker's daemon is, when that is not this machine: DOCKER_HOST,
    else the current context's endpoint. None for a local socket or pipe."""
    if name != "docker":
        return None
    host = (
        env.get("DOCKER_HOST")
        or run(
            [name, "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    )
    return host if host and not host.startswith(("unix://", "npipe://")) else None


def interactive() -> bool:
    """Whether a terminal is there for -it, both ways."""
    return sys.stdin.isatty() and sys.stdout.isatty()
