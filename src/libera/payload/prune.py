"""Old payloads: which ones are still used, and removing the rest.

Every update leaves the previous version on disk, about 400 MB each, and
nothing removed them: 1.26 GB on one Mac by 0.5. The folder is shared by every
channel that installs a payload (pip, pipx, uvx, Homebrew), so a version this
copy does not name may be another copy's, perhaps running while this one
installs. Removal therefore goes by use, not by name. A launch marks the
payload it runs on, and a running copy marks it again every hour, so a version
nobody has marked for four weeks is also one nothing is running.

Only versions under `locate.get_data_dir()`: a payload found through
LIBERA_PAYLOAD, the configuration or a bundle lives elsewhere, and is the
user's to remove.
"""

from __future__ import annotations

import logging
import re
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera.payload import locate

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

MARKER = ".last-used"
DAY = 24 * 3600
UNUSED_FOR = 28 * DAY
REFRESH = 3600
# What `install` names a version's folder; its staging folders start with a dot.
VERSION = re.compile(r"\d+(\.\d+)*([a-z]+\d+)?")
# A version on its way out: renamed first, so that two copies pruning at once
# never both walk the same tree, and one that stopped halfway is finished next.
REMOVING = ".removing-"


@dataclass(frozen=True)
class Version:
    root: Path
    last_used: float

    @property
    def name(self) -> str:
        return self.root.name


def note_use(root: Path) -> None:
    """Mark the payload at `root` as used now, and every hour for as long as
    this process runs. Only an installed one: no other is ours to remove."""
    if root.parent != locate.get_data_dir():
        return
    marker = root / MARKER
    marker.touch()
    threading.Thread(
        target=_keep_marking, args=(marker,), name="payload-use", daemon=True
    ).start()


def _keep_marking(marker: Path) -> None:
    # ponytail: a machine asleep for four weeks with a copy open can come back
    # to find its payload removed; its next x2t start fails until it reinstalls.
    while True:
        time.sleep(REFRESH)
        try:
            marker.touch()
        except FileNotFoundError:  # --payload-remove took it: nothing to mark
            return


def list_versions(folder: Path) -> list[Version]:
    """The payloads installed in `folder`, oldest use first.

    One that no launch has marked was installed by a copy older than 0.5,
    which marks nothing: it counts as used when it was installed.
    """
    if not folder.is_dir():
        return []
    found = []
    for root in folder.iterdir():
        if not (root.is_dir() and VERSION.fullmatch(root.name)):
            continue
        marker, record = root / MARKER, root / "payload.json"
        when = marker if marker.exists() else record if record.exists() else root
        found.append(Version(root, when.stat().st_mtime))
    return sorted(found, key=lambda v: v.last_used)


def find_unused(folder: Path, keep: str, now: float) -> list[Version]:
    """The versions in `folder` nobody has used for UNUSED_FOR, `keep` aside."""
    return [
        v
        for v in list_versions(folder)
        if v.name != keep and now - v.last_used > UNUSED_FOR
    ]


def remove_unused(folder: Path, keep: str, now: float | None = None) -> list[str]:
    """Remove the unused versions, and any removal an earlier run left
    halfway. Says what it removed, as `0.3 (412 MB)`."""
    for left in folder.glob(f"{REMOVING}*"):
        shutil.rmtree(left, ignore_errors=True)
    removed = []
    for v in find_unused(folder, keep, time.time() if now is None else now):
        size = measure(v.root)
        doomed = folder / f"{REMOVING}{v.name}-{uuid.uuid4().hex[:8]}"
        try:
            v.root.rename(doomed)
        except OSError as e:  # another copy got there first, or something holds it
            logger.info("payload %s left in place: %s", v.name, e)
            continue
        shutil.rmtree(doomed, ignore_errors=True)
        removed.append(f"{v.name} ({size / 1e6:.0f} MB)")
    return removed


def remove_unused_behind(folder: Path, keep: str) -> None:
    """remove_unused on a thread of its own: 400 MB takes seconds to delete,
    and a launch has a window to open."""

    def run() -> None:
        for gone in remove_unused(folder, keep):
            logger.info("removed the unused payload %s", gone)

    threading.Thread(target=run, name="payload-prune", daemon=True).start()


def measure(root: Path) -> int:
    return sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
