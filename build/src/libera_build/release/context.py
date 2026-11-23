"""What one run of `lb release check` or `lb release publish` is about."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from libera_build.hosts import ssh_host

if TYPE_CHECKING:
    from collections.abc import Callable

    from libera_build.hosts import Host
    from libera_build.inventory import Builder


# Where the Homebrew tap is cloned, unless --tap (TAP) says otherwise.
DEFAULT_TAP = Path.home() / "projects" / "homebrew-tap"


@dataclass(frozen=True)
class Context:
    root: Path  # the driving checkout: its HEAD is what the builders build
    builders: list[Builder]
    phases: list[str]
    # The version this run's files carry: a candidate's, the tree's version
    # with the checked commit as a local label (0.7.4+69906cd, which PyPI
    # refuses), for `check`; the release's, for `publish`.
    version: str
    # The checked commit's run directory (artifacts.run_dir), read once: a
    # publish moves HEAD to its version's commit, and goes on from here.
    run: Path
    yes: bool = False  # publish without asking
    fast: bool = False  # check without the suite and the distributions
    # How a builder is reached. ssh, unless a test hands builders it made.
    host_for: Callable[[Builder], Host] = field(default=ssh_host)
    # How often a builder's detached job is polled, and how long it may not
    # answer before the watch gives up (release.builds.watch): builder-windows
    # was off the network for twenty minutes at a time on 2026-11-01, its
    # build going on meanwhile.
    poll_seconds: float = 15
    unreachable_seconds: float = 45 * 60
    # The Homebrew tap's clone, which the tap phase updates (phases.chores).
    tap: Path = DEFAULT_TAP

    @property
    def files(self) -> Path:
        """This version's files: pypi/, bundles/, staged/ and origin/."""
        return self.run / self.version

    @property
    def logs(self) -> Path:
        return self.root / "tmp" / "remote"

    @property
    def remotes(self) -> list[Builder]:
        return [b for b in self.builders if b.remote]
