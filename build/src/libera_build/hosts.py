"""Reaching a machine: run a script on it, send it a commit, fetch a file.

Two kinds. `SshHost` is a builder over ssh. `LocalHost` is a builder in a
directory of this machine, whose `~` is that directory: the integration tests
drive it as a real builder, with real bash and real git, and no mocks.

Over ssh an exit status describes the shell, including its login and logout
scripts, rather than the work: a login bash returns 1 from `set -eu; exit 0`,
because ~/.bash_logout runs with -u still in force (see
notes/lessons-learned/scripts-and-builds.md). So a script run on a host prints
the facts it wants believed as KEY=value lines, MARK=... among them, and the
caller reads those.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from libera_build.process import capture

if TYPE_CHECKING:
    from libera_build.inventory import Builder

# The verdict line a host's script prints, rather than an exit status.
MARK = "__LIBERA__"

# Non-interactive, and it should say so quickly rather than sit at a password
# prompt inside a thread whose output nobody is watching.
#
# ServerAlive* because a build is hours and the connection carries it: a NAT or
# a firewall that drops an idle session takes the build with it, and the
# symptom is a log that stops mid-compile with no error in it. Six missed
# thirty-second probes is three minutes of genuine silence before giving up.
#
# It does not survive the *local* process ending -- a closed terminal or a
# sleeping laptop still kills the build. Run a release under tmux or screen.
#
# scp takes the same options, and needs them as much: a copy is a connection.
SSH_OPTIONS = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "ServerAliveInterval=30",
    "-o",
    "ServerAliveCountMax=6",
]
SSH = ["ssh", *SSH_OPTIONS]
SCP = ["scp", "-q", *SSH_OPTIONS]


# How a builder runs `lb`: from its checkout, with nothing installed, so as a
# module with the two source trees on PYTHONPATH. Absolute, because on Windows
# the Python is native and its separator is `;`: Git Bash rewrites an absolute
# colon-separated list into C:\...;C:\... for it, and a relative one reaches
# it as one path that does not exist (measured on the Windows builder).
# PYTHONUTF8 because Python on Windows writes a pipe in the ANSI code page:
# the manifest's `…` reached the reader here as cp1252's 0x85.
LB = 'PYTHONUTF8=1 PYTHONPATH="$PWD/build/src:$PWD/src" python3 -m libera_build'


def facts_from(out: str) -> dict[str, str]:
    """The KEY=value lines a host's script printed."""
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def remote_path(path: str) -> str:
    """Quote a path for the remote shell, leaving a leading ~ able to expand.

    shlex.quote would wrap `~/liberasuite` in single quotes and the remote
    shell would then look for a directory literally called `~`. Double quotes
    around $HOME expand and still survive a space in the rest.
    """
    if path.startswith("~/"):
        return f'"$HOME/{path[2:]}"'
    return shlex.quote(path)


class Host(Protocol):
    @property
    def name(self) -> str: ...

    def capture(self, script: str) -> str:
        """Run a bash script there and return what it printed, both streams."""
        ...

    def start(self, script: str) -> subprocess.Popen[str]:
        """Start a bash script there, its output one stream to read."""
        ...

    def receive(self, root: Path, commit: str, repo: str) -> tuple[int, str]:
        """Push `commit` from the checkout at `root` to the checkout `repo`
        there, as refs/heads/lb-build."""
        ...

    def fetch(self, path: str, dest: Path) -> tuple[int, str]:
        """Copy a file from there to here."""
        ...

    def send(self, source: Path, path: str) -> tuple[int, str]:
        """Copy a file from here to there."""
        ...


def _start(
    argv: list[str], script: str, env: dict[str, str] | None
) -> subprocess.Popen[str]:
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        # What a builder prints is other people's bytes -- a compiler, a
        # Windows tool in its console code page -- and one that is not UTF-8
        # must not end the run that is reading it.
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert process.stdin is not None  # ken: PIPE was asked for, so it is there
    process.stdin.write(script)
    process.stdin.close()
    return process


@dataclass(frozen=True)
class SshHost:
    """A builder over ssh, through a login shell, which is where its PATH is."""

    name: str  # anything ssh and scp take; a Host alias in ~/.ssh/config

    def capture(self, script: str) -> str:
        _, out = capture_input([*SSH, self.name, "bash -l -s"], script)
        return out.strip()

    def start(self, script: str) -> subprocess.Popen[str]:
        return _start([*SSH, self.name, "bash -l -s"], script, None)

    def receive(self, root: Path, commit: str, repo: str) -> tuple[int, str]:
        # The same ssh options as everything else here, for git's own ssh.
        env = {**os.environ, "GIT_SSH_COMMAND": shlex.join(SSH)}
        return push(root, commit, f"{self.name}:{repo}", env)

    def fetch(self, path: str, dest: Path) -> tuple[int, str]:
        return capture([*SCP, f"{self.name}:{path}", str(dest)])

    def send(self, source: Path, path: str) -> tuple[int, str]:
        return capture([*SCP, str(source), f"{self.name}:{path}"])


@dataclass(frozen=True)
class LocalHost:
    """A builder in a directory of this machine: `~` is `home`."""

    home: Path

    @property
    def name(self) -> str:
        return str(self.home)

    def _env(self) -> dict[str, str]:
        return {**os.environ, "HOME": str(self.home)}

    def _path(self, path: str) -> Path:
        """As scp reads one: from the home directory unless absolute."""
        given = Path(path)
        return given if given.is_absolute() else self.home / path.removeprefix("~/")

    def capture(self, script: str) -> str:
        _, out = capture_input(["bash", "-s"], script, env=self._env())
        return out.strip()

    def start(self, script: str) -> subprocess.Popen[str]:
        return _start(["bash", "-s"], script, self._env())

    def receive(self, root: Path, commit: str, repo: str) -> tuple[int, str]:
        return push(root, commit, str(self._path(repo)), self._env())

    def fetch(self, path: str, dest: Path) -> tuple[int, str]:
        source = self._path(path)
        if not source.is_file():
            return 1, f"{source}: no such file"
        shutil.copyfile(source, dest)
        return 0, ""

    def send(self, source: Path, path: str) -> tuple[int, str]:
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return 0, ""


# Where `update` puts the commit on each builder, which then checks it out
# detached: a branch of its own, so that the push never meets the branch a
# builder has checked out, which git refuses to update in place.
BUILD_REF = "lb-build"


def push(root: Path, commit: str, url: str, env: dict[str, str]) -> tuple[int, str]:
    return capture(
        [
            "git",
            "-C",
            str(root),
            "push",
            "--quiet",
            "--force",
            url,
            f"{commit}:refs/heads/{BUILD_REF}",
        ],
        env=env,
    )


def capture_input(
    argv: list[str], script: str, env: dict[str, str] | None = None
) -> tuple[int, str]:
    done = subprocess.run(
        argv,
        input=script,
        capture_output=True,
        encoding="utf-8",
        errors="replace",  # as in _start
        check=False,
        env=env,
    )
    return done.returncode, done.stdout + done.stderr


def ssh_host(builder: Builder) -> Host:
    """How a run reaches a builder unless told otherwise: ssh to its target."""
    return SshHost(builder.target)
