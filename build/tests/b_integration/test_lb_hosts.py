"""SshHost's copies, against an `scp` that is a script on PATH: it writes its
arguments down, and reports success whatever happened, as the real one has
been seen to for a transfer that wrote nothing."""

from __future__ import annotations

import os
import shlex
import sys
from typing import TYPE_CHECKING

import pytest
from libera_build.hosts import SshHost

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def scp_log(tmp_path, monkeypatch) -> Path:
    """Where the stand-in scp writes the arguments of each call, a line each."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    log = tmp_path / "scp.log"
    scp = bin_ / "scp"
    scp.write_text(f'#!/bin/sh\necho "$*" >> {shlex.quote(str(log))}\nexit 0\n')
    scp.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_), prepend=os.pathsep)
    return log


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the stand-in is an sh script, which Windows does not run",
)
def test_a_copy_cannot_sit_at_a_password_prompt(scp_log, tmp_path):
    """The options ssh gets, scp gets, both ways: an unattended release must
    fail fast rather than wait for a password nobody will type."""
    host = SshHost("builder")
    host.fetch("~/a.tar.gz", tmp_path / "a.tar.gz")
    host.send(tmp_path / "a.tar.gz", "~/b.tar.gz")
    fetched, sent = scp_log.read_text().splitlines()
    for line in (fetched, sent):
        assert "-o BatchMode=yes" in line
        assert "-o ConnectTimeout=10" in line
