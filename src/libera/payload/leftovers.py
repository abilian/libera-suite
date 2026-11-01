"""What 0.6 and earlier downloaded: a payload per version under
`locate.get_data_dir()`, about 400 MB each, which nothing reads from 0.7 on.

Removed only when asked: by `libera --payload-remove`, or from the start
window, which offers it once. A copy of an earlier version still installed
beside this one would use its own, so the question is the user's.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from libera.payload import locate

if TYPE_CHECKING:
    from pathlib import Path

# In the state folder: the start window has asked, and the answer stands.
ASKED = "old-payloads-asked"


def find() -> list[Path]:
    folder = locate.get_data_dir()
    return sorted(folder.iterdir()) if folder.is_dir() else []


def measure(root: Path) -> int:
    return sum(f.stat().st_size for f in root.rglob("*") if f.is_file())


def remove() -> int:
    """Delete them all, and say how many bytes that freed."""
    folder = locate.get_data_dir()
    if not folder.exists():
        return 0
    size = measure(folder)
    shutil.rmtree(folder)
    return size


def should_offer() -> bool:
    """There are some, and the start window has not asked about them yet."""
    return not (locate.get_state_dir() / ASKED).exists() and bool(find())


def mark_asked() -> None:
    (locate.get_state_dir() / ASKED).touch()
