"""The canary's judgement of our queue against upstream's head."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from libera_build import canary
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
PINS = """[repos]
core       = "{a}"  # 2026-11-19, Euro-Office main
sdkjs      = "{a}"  # 2026-11-19, Euro-Office main
core-fonts = "{a}"  # 2026-10-13, DesktopEditors v9.3.8
"""


def git(where: Path, *args: str) -> str:
    done = subprocess.run(
        [*GIT, "-C", str(where), *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def test_the_canary_moves_the_repositories_asked_and_no_other():
    text = PINS.format(a="a" * 40)
    moved = canary.at_heads(text, {"core": "b" * 40, "sdkjs": "c" * 40}, "main")
    assert f'core       = "{"b" * 40}"  # main, for the canary' in moved
    assert f'sdkjs      = "{"c" * 40}"  # main, for the canary' in moved
    assert f'core-fonts = "{"a" * 40}"  # 2026-10-13' in moved
    with pytest.raises(RefusedError, match="no single line for web-apps"):
        canary.at_heads(text, {"web-apps": "d" * 40}, "main")


def edit(repo: Path, old: str, new: str, message: str) -> None:
    f = repo / "a.txt"
    f.write_text(f.read_text().replace(old, new))
    git(repo, "commit", "-qam", message)


def test_each_patch_applies_is_already_upstream_or_conflicts(tmp_path):
    """Three patches on our pin; upstream's head then merges the first and
    rewrites the line the third changes. The second still applies."""
    up = tmp_path / "upstream"
    git(tmp_path, "init", "-q", str(up))
    (up / "a.txt").write_text("".join(f"line {n}\n" for n in range(30)))
    git(up, "add", ".")
    git(up, "commit", "-qm", "pin")
    pin = git(up, "rev-parse", "HEAD")
    edit(up, "line 2\n", "ours 2\n", "merged upstream")
    edit(up, "line 12\n", "ours 12\n", "still ours")
    edit(up, "line 22\n", "ours 22\n", "conflicting")
    queue = tmp_path / "queue"
    git(up, "format-patch", "-q", "-o", str(queue), f"{pin}..HEAD")
    git(up, "checkout", "-q", pin)
    edit(up, "line 2\n", "ours 2\n", "upstream takes our first")
    edit(up, "line 22\n", "theirs 22\n", "upstream rewrites the third's line")
    head = git(up, "rev-parse", "HEAD")

    verdicts = canary.classify(up, head, sorted(queue.iterdir()))

    assert [v for _, v in verdicts] == [
        canary.UPSTREAM,
        canary.APPLIES,
        canary.CONFLICTS,
    ]
    assert not git(up, "status", "--porcelain"), "the clone was only read"
