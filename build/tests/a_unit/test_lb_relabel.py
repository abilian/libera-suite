"""A wheel given another version: every place that says it, and nothing else."""

from __future__ import annotations

import base64
import hashlib
import time
import types
import zipfile
from typing import TYPE_CHECKING

import pytest
from libera_build.relabel import relabel, version_of
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

INFO = "libera-1.0.dist-info"
FILES = {
    "libera/__init__.py": b"",
    "libera/payload/payload.version": b'# the payload\nversion = "1.0"\n',
    f"{INFO}/METADATA": (
        b"Metadata-Version: 2.4\nName: libera\nVersion: 1.0\n"
        b"Requires-Dist: libera-core==1.0\nRequires-Dist: libera-web==1.0\n"
        b"Requires-Dist: pywebview>=6\n"
    ),
    f"{INFO}/WHEEL": b"Wheel-Version: 1.0\n",
}


def wheel(tmp_path: Path, files: dict[str, bytes] = FILES) -> Path:
    made = tmp_path / "libera-1.0-py3-none-any.whl"
    with zipfile.ZipFile(made, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr(f"{INFO}/RECORD", "stale")
    return made


def test_every_place_says_the_new_version_and_the_record_holds(tmp_path):
    made = relabel(wheel(tmp_path), "1.0+abc1234", tmp_path / "out")

    assert made.name == "libera-1.0+abc1234-py3-none-any.whl"
    assert version_of(made) == "1.0+abc1234"
    with zipfile.ZipFile(made) as z:
        info = "libera-1.0+abc1234.dist-info"
        metadata = z.read(f"{info}/METADATA").decode()
        assert "Version: 1.0+abc1234\n" in metadata
        assert "libera-core==1.0+abc1234" in metadata
        assert "libera-web==1.0+abc1234" in metadata
        assert "pywebview>=6" in metadata
        assert (
            'version = "1.0+abc1234"'
            in z.read("libera/payload/payload.version").decode()
        )
        assert not [n for n in z.namelist() if n.startswith(INFO)]
        rows = z.read(f"{info}/RECORD").decode().splitlines()
        assert rows[-1] == f"{info}/RECORD,,"
        for row in rows[:-1]:
            path, digest, size = row.split(",")
            data = z.read(path)
            want = base64.urlsafe_b64encode(hashlib.sha256(data).digest())
            assert digest == f"sha256={want.rstrip(b'=').decode()}", path
            assert int(size) == len(data), path


def test_a_file_that_says_its_version_another_way_is_refused(tmp_path):
    files = {**FILES, "libera/payload/payload.version": b"version = '1.0'\n"}
    with pytest.raises(RefusedError, match=r"payload\.version"):
        relabel(wheel(tmp_path, files), "2.0", tmp_path / "out")


def test_the_same_wheel_relabelled_later_is_the_same_file(tmp_path, monkeypatch):
    """What lets a check run again reuse the bundles made of its wheels."""
    original = wheel(tmp_path)
    first = relabel(original, "1.0+abc1234", tmp_path / "first")
    # An hour on, for zipfile alone, which dates an entry it is given by name.
    later = time.time() + 3600
    clock = types.SimpleNamespace(time=lambda: later, localtime=time.localtime)
    monkeypatch.setattr(zipfile, "time", clock)
    second = relabel(original, "1.0+abc1234", tmp_path / "second")
    assert first.read_bytes() == second.read_bytes()
