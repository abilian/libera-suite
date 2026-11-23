"""The install checks leave nothing behind.

Each one makes a virtualenv in a directory of its own, 414 MB, and left it in
/tmp: seven of them filled the arm64 builder's, a tmpfs with a quota per user,
and the next release check failed there with "Disk quota exceeded". These run
the scripts as the builders do, with bash, and with tools that fail at once,
and look for what is left in TMPDIR.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from libera_build.release.phases import publishing

if TYPE_CHECKING:
    from pathlib import Path

# Stand-ins that fail, so each script stops at its first install step: what
# matters is the exit, not the install. curl's output is piped to sh, whose
# status is the pipe's, so it hands sh a failure rather than failing itself.
FAILING = {"uv": "exit 1", "curl": "echo 'exit 1'"}


def run(script: str, tmp_path: Path) -> list[Path]:
    """`script` run by bash with TMPDIR in `tmp_path`; what is left there."""
    scratch = tmp_path / "tmp"
    tools = tmp_path / "bin"
    scratch.mkdir()
    tools.mkdir()
    for name, body in FAILING.items():
        tool = tools / name
        tool.write_text(f"#!/bin/sh\n{body}\n")
        tool.chmod(0o755)
    env = {
        **os.environ,
        "TMPDIR": str(scratch),
        "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
    }
    subprocess.run(
        ["bash", "-s"],
        input=script,
        text=True,
        env=env,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return sorted(
        p for p in scratch.iterdir() if not p.name.startswith("libera-origin-")
    )


def test_the_staged_install_removes_its_environment(tmp_path):
    script = publishing.install_script(
        "9.9.9", staged="libera-stage/9.9.9", deps=["pywebview>=6"]
    )
    assert run(script, tmp_path) == []


def test_the_install_from_the_origin_removes_its_home_and_stops_serving(tmp_path):
    zone = tmp_path / "zone"
    zone.mkdir()
    script = publishing.origin_install_script("9.9.9", zone, tmp_path, "macos-arm64")
    assert run(script, tmp_path) == []
