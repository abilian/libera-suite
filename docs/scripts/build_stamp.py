"""Write site/build.json: the last commit to docs/ that this build comes from.

Installed in docs/scripts/ by `docsctl setup`, which replaces it whenever the
canonical copy (docsctl/build_stamp.py) changes: edit that one, not this one.
Run it after the site is built:

    python3 scripts/build_stamp.py [SITE_DIR]    # default: site

The file is deployed with the site; `docsctl status` compares it with the repo.
Standard library only, Python 3.11+.
"""

# A standalone script, not a package module (INP001), that runs `git` from PATH
# with fixed arguments (S404, S603, S607).
# ruff: file-ignore[INP001, S404, S603, S607]

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

DOCS = Path(__file__).resolve().parent.parent  # docs/scripts/build_stamp.py
STAMP_FILE = "build.json"


class Stamp(TypedDict):
    commit: str  # last commit that touched docs/
    date: str  # its date
    dirty: bool  # docs/ has uncommitted changes
    built: str  # when this stamp was made, UTC


def stamp(docs: Path) -> Stamp:
    """The last commit to `docs`, its date, and whether `docs` has changes."""
    commit, date = _git(docs, "log", "-1", "--format=%H %cI", "--", ".").split()
    return {
        "commit": commit,
        "date": date,
        "dirty": bool(_git(docs, "status", "--porcelain", "--", ".")),
        "built": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def _git(docs: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=docs, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> None:
    site = DOCS / (sys.argv[1] if len(sys.argv) > 1 else "site")
    (site / STAMP_FILE).write_text(json.dumps(stamp(DOCS)) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
