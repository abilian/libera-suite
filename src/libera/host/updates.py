"""Saying once that a newer version is out.

At most once a day, one small object from the CDN: the version the release
pointer names. Nothing is downloaded and nothing is sent; the request shows the
server an IP address, as `docs/src/index.md` says. A newer version is told once,
with how to update for the channel this copy came from, since each one updates
differently. Offline, or with an answer that is not a version, nothing is said.
`check_updates = false` in config.toml turns it off: no request at all.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING

from libera.host import hooks, language, session
from libera.payload import installer, locate

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

DAY = 24 * 60 * 60
# Short: the check runs on a thread of its own, and a connection that hangs
# holds nothing up, but there is no reason for it to linger either.
FETCH_TIMEOUT = 10.0


@dataclass(frozen=True)
class Channel:
    """Where this copy came from: the pointer its releases move, and how a user
    of it updates."""

    pointer: str
    how: str


def find_channel() -> Channel:
    # A Flatpak bundle has no remote to update from: the install script
    # reinstalls it. `bundles/latest` moves with the Flatpaks and PyPI.
    if os.environ.get("FLATPAK_ID"):
        return Channel(
            "latest",
            language.translate(
                "Run the install command again:\n\n{command}",
                command=f"curl -fsSL {installer.DEFAULT_ORIGIN}/install.sh | sh",
            ),
        )
    # The installer's PyInstaller build. Its pointer moves only when the
    # Windows installer is published, which can be days after the rest.
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        return Channel(
            "latest-windows",
            language.translate(
                "In PowerShell:\n\n{command}",
                command=f"irm {installer.DEFAULT_ORIGIN}/install.ps1 | iex",
            ),
        )
    if "/Cellar/" in sys.prefix:
        return Channel(
            "latest",
            language.translate(
                "In a terminal:\n\n{command}", command="brew upgrade libera"
            ),
        )
    return Channel(
        "latest",
        language.translate(
            "Update it the way you installed it: {pipx}, {uv}, "
            "or the install command again.",
            pipx="pipx upgrade libera",
            uv="uv tool upgrade libera",
        ),
    )


def parse_version(text: str) -> tuple[tuple[int, ...], int, str, int]:
    """Parse "0.4.0" as ((0, 4, 0), 1, "", 0), and a pre-release below its
    release: "0.4.0rc1" as ((0, 4, 0), 0, "rc", 1). A pointer only ever names
    a release, but the copy asking may be a pre-release, and a tester's 0.4.0rc1
    has to hear about 0.4.0. A ValueError for anything that is not one."""
    m = re.fullmatch(r"(\d+(?:\.\d+)*)(?:(a|b|rc)(\d+))?", text.strip())
    if not m:
        msg = f"not a version: {text!r}"
        raise ValueError(msg)
    release = tuple(int(p) for p in m[1].split("."))
    if m[2]:
        return release, 0, m[2], int(m[3])
    return release, 1, "", 0


def check(current: str, origin: str, state: Path, now: float) -> None:
    """Fetch the pointer unless today's check is done, and tell a newer
    version once. Raises what the fetch or the answer raises."""
    seen = json.loads(session.read_atomically(state)) if state.is_file() else {}
    if now - seen.get("checked", 0) < DAY:
        return
    channel = find_channel()
    url = f"{origin}/bundles/{channel.pointer}"
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT) as r:
        latest = r.read(64).decode("ascii").strip()
    newer = parse_version(latest) > parse_version(current)
    announce = newer and seen.get("announced") != latest
    seen = {**seen, "checked": now}
    if announce:
        seen["announced"] = latest
    state.parent.mkdir(parents=True, exist_ok=True)
    session.write_atomically(state, json.dumps(seen))
    if announce:
        hooks.shell.tell(
            language.translate("Libera Suite {version} is available", version=latest),
            language.translate("This is version {version}.", version=current)
            + " "
            + channel.how,
        )


def wanted() -> bool:
    """Unless config.toml says `check_updates = false`: for a machine whose
    owner, or whose organisation, wants no request it did not ask for."""
    return locate.read_config_bool("check_updates") is not False


def check_in_background() -> None:
    """The check, on a thread of its own, once the application runs.

    A failure is logged at info and shown to no one. Offline is the normal
    case on a train; an answer that is not a version is ours to fix.
    """

    # Off when the switch cannot be read, too: whoever wrote it meant
    # something. A request is the one thing that cannot be taken back.
    try:
        if not wanted():
            logger.info("update check: off, check_updates = false in config.toml")
            return
    except locate.PayloadError as e:
        logger.warning("update check: off, %s", e)
        return

    def run() -> None:
        try:
            check(
                metadata.version("libera"),
                installer.DEFAULT_ORIGIN,
                locate.get_state_dir() / "updates.json",
                time.time(),
            )
        except (OSError, ValueError) as e:
            logger.info("update check: %s", e)

    threading.Thread(target=run, daemon=True, name="update-check").start()
