"""x2t is stopped when it holds too much memory or runs too long, and never
started on a package that says it unpacks to more than the host allows.

A small document can take x2t to gigabytes (notes/plans/converter-hardening.md):
the conversion has to fail before the machine swaps. A Python child stands in
for x2t, allocating what x2t would.
"""

from __future__ import annotations

import os
import pathlib
import sys
import time
import zipfile

import pytest

from libera.host import convert, desktop
from libera.host.convert import ConversionError

# A venv's python.exe on Windows is a launcher that runs the real interpreter as
# its own child, so what the stand-in holds would be its grandchild's, which
# the watchdog does not look at (measured: 0 MB against 306). x2t is started
# directly, so the stand-in is too.
PYTHON = (
    str(pathlib.Path(sys.base_prefix, "python.exe"))
    if sys.platform == "win32"
    else sys.executable
)
# Touches every page, so the memory is resident, not merely reserved.
HOLD = (
    "import time; b = bytearray({mb} << 20); b[::4096] = b'x' * len(b[::4096]);"
    " time.sleep(30)"
)


def test_a_converter_holding_too_much_is_stopped(monkeypatch):
    monkeypatch.setattr(convert, "X2T_MEMORY", 100 << 20)
    start = time.monotonic()

    with pytest.raises(ConversionError, match="more than 100 MB"):
        convert.run_watched([PYTHON, "-c", HOLD.format(mb=300)], {**os.environ})

    assert time.monotonic() - start < 10


def test_a_converter_past_its_time_is_stopped(monkeypatch):
    monkeypatch.setattr(convert, "X2T_TIMEOUT", 1)
    start = time.monotonic()

    with pytest.raises(ConversionError, match="did not finish in 1 s"):
        convert.run_watched(
            [PYTHON, "-c", "import time; time.sleep(30)"], {**os.environ}
        )

    assert time.monotonic() - start < 10


def test_a_converter_within_bounds_gives_its_output(monkeypatch):
    monkeypatch.setattr(convert, "X2T_MEMORY", 1 << 30)
    done = convert.run_watched(
        [
            PYTHON,
            "-c",
            HOLD.format(mb=20).replace("time.sleep(30)", "print('done')"),
        ],
        {**os.environ},
    )

    assert done.returncode == 0
    assert done.stdout.strip() == "done"


def test_a_process_that_is_gone_holds_nothing():
    assert desktop.memory_bytes(os.getpid()) > 0
    # A pid this large is never handed out (pid_max is at most 4194304).
    assert desktop.memory_bytes(2**30) == 0


def make_package(path, members: dict[str, int]):
    """A ZIP whose members are that many zero bytes each, which compress to
    almost nothing: what a package that unpacks to gigabytes looks like."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        for name, size in members.items():
            with package.open(name, "w", force_zip64=True) as member:
                member.write(bytes(size))
    return path


def test_a_package_that_unpacks_too_large_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(convert, "PACKAGE_LIMIT", 1 << 20)
    big = make_package(tmp_path / "big.docx", {"a.xml": 600 << 10, "b.xml": 600 << 10})

    with pytest.raises(
        ConversionError, match=r"big\.docx unpacks to 1 MB, more than 1 MB"
    ):
        convert.check_package(big)


def test_a_package_within_its_limit_or_not_a_package_goes_to_x2t(tmp_path, monkeypatch):
    monkeypatch.setattr(convert, "PACKAGE_LIMIT", 1 << 20)
    convert.check_package(make_package(tmp_path / "small.docx", {"a.xml": 500 << 10}))
    (tmp_path / "old.doc").write_bytes(b"\xd0\xcf\x11\xe0" + bytes(2 << 20))
    convert.check_package(tmp_path / "old.doc")
