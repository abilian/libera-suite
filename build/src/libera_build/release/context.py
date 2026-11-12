"""What one run of `lb release check` or `lb release publish` is about."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libera_build.hosts import ssh_host

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder


@dataclass(frozen=True)
class Context:
    root: Path  # the driving checkout: its HEAD is what the builders build
    builders: list[Builder]
    phases: list[str]
    yes: bool = False  # publish without asking
    # How a builder is reached. ssh, unless a test hands builders it made.
    host_for: Callable[[Builder], Host] = field(default=ssh_host)
    # How often a builder's detached job is polled, and how long it may not
    # answer before the watch gives up (release.builds.watch): builder-windows
    # was off the network for twenty minutes at a time on 2026-11-01, its
    # build going on meanwhile.
    poll_seconds: float = 15
    unreachable_seconds: float = 45 * 60

    @property
    def logs(self) -> Path:
        return self.root / "tmp" / "remote"

    @property
    def remotes(self) -> list[Builder]:
        return [b for b in self.builders if b.remote]
