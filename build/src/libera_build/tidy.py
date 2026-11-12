"""`lb tidy`: remove every build on this machine.

Two places hold builds and both go: the repository, where the Flatpak's
builddir and ostree store are the bulk of it, and $BUILD_ROOT, which is the
payload, the native core and the Linux container trees. On the laptop this was
written on that is 1.4 GB and 44 GB.

$BUILD_ROOT/src goes too. It is a clone of the upstream repositories at the
pinned SHAs, so a build input rather than a build -- but it lives in the build
area, `lb payload build fetch` recreates it, and leaving 6.5 GB behind after a
command called tidy would be its own surprise.

**It lists, then asks.** Not a guard against the person who typed it: they
asked. It is that this deletes a day of V8, ICU and container builds, and the
list is worth seeing first. --yes does not ask; --dry-run lists and stops.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from libera_build import report
from libera_build.report import say

if TYPE_CHECKING:
    from pathlib import Path

# Everything the repository's own builds write. All of it is gitignored; a test
# keeps it that way, because `rm -rf build` once took the patch queue with it.
REPO_PATHS = (
    "build/out",
    "build/flatpak/.flatpak-builder",
    "build/flatpak/builddir",
    "build/flatpak/repo",
    "build/flatpak/wheels",
    "build/flatpak/wheels.tmp",
    # Written by builds before 0.7, and still on the builders that ran them.
    "build/flatpak/payload",
    "build/flatpak/payload.tmp",
    "docs/site",
    "docs/.cache",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
)


def size_of(path: Path) -> int:
    """Bytes on disk, from du: $BUILD_ROOT is millions of files, which du sums
    in seconds and a walk in Python in minutes."""
    done = subprocess.run(
        ["du", "-sk", str(path)], capture_output=True, text=True, check=False
    )
    return int(done.stdout.split()[0]) * 1024 if done.stdout else 0


def found(root: Path, build_root: Path) -> list[Path]:
    """What tidy would remove, of what is there."""
    paths = [root / p for p in REPO_PATHS]
    paths += sorted((root / "build" / "flatpak").glob("*.flatpak"))
    paths.append(build_root)
    return [p for p in paths if p.exists()]


def tidy(
    root: Path, build_root: Path, *, yes: bool = False, dry_run: bool = False
) -> int:
    present = found(root, build_root)
    if not present:
        say("    nothing to tidy")
        return 0
    total = 0
    for path in present:
        size = size_of(path)
        total += size
        shown = path.relative_to(root) if path.is_relative_to(root) else path
        say(f"    {size / 1e9:7.1f} GB  {shown}")
    say(f"\n    {total / 1e9:.1f} GB in total")
    if dry_run:
        say("\n    nothing removed (--dry-run)")
        return 0
    if not yes:
        report.confirm("remove all of it?", "nothing was removed.")
    for path in present:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    # adt owns its own caches and knows where they are, where it is installed.
    if shutil.which("adt"):
        subprocess.run(["adt", "clean"], cwd=root, capture_output=True, check=False)
    say(f"\n    removed. {build_root} is gone too, so the next payload build starts")
    say("    from the fetch: make payload")
    return 0
