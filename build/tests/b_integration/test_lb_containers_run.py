"""Containers, really started: the command line a Run becomes is one the
engine here accepts, mounts and environment included.

Skips where there is no engine running, or no test image built yet
(`lb linux image`), and says which.
"""

from __future__ import annotations

import subprocess
import zipfile

import pytest
from libera_build import matrix
from libera_build.containers import Engine, Mount, Run, host_arch

from libera import payload


@pytest.fixture(scope="module")
def engine_and_image():
    engine = Engine.here()
    try:
        alive = subprocess.run([engine.name, "info"], capture_output=True, check=False)
    except FileNotFoundError:
        pytest.skip(f"no {engine.name} here")
    if alive.returncode != 0:
        pytest.skip(f"{engine.name} is not running")
    image = engine.image(f"libera-test-linux-{host_arch()}")
    if not engine.has_image(image):
        pytest.skip(f"no {image}: lb linux image")
    return engine, image


def test_a_run_starts_with_its_mounts_and_environment(engine_and_image, tmp_path):
    engine, image = engine_and_image
    (tmp_path / "in.txt").write_text("from the host")
    argv = engine.run_argv(
        Run(
            image,
            ("-c", 'cat /w/in.txt; echo " $GREETING"; touch /w/out.txt'),
            host_arch(),
            mounts=(Mount(tmp_path, "/w"),),
            env={"GREETING": "and the env"},
            extra=("--pull=never",),
        )
    )
    done = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "from the host and the env"
    assert (tmp_path / "out.txt").exists(), "the mount is writable"


def test_a_read_only_mount_is_read_only(engine_and_image, tmp_path):
    engine, image = engine_and_image
    argv = engine.run_argv(
        Run(
            image,
            ("-c", "touch /w/x"),
            host_arch(),
            mounts=(Mount(tmp_path, "/w", read_only=True),),
            extra=("--pull=never",),
        )
    )
    assert subprocess.run(argv, capture_output=True, check=False).returncode != 0
    assert not (tmp_path / "x").exists()


def test_the_sample_is_made_from_the_payloads_own_blank(tmp_path):
    """make_sample needs nothing but the staged files: the blank comes out of
    the libera-web wheel."""
    try:
        blank = payload.resolve().root / "empty" / "new.docx"
    except payload.PayloadError:
        pytest.skip("no payload here")
    dist = tmp_path / "dist"
    dist.mkdir()
    with zipfile.ZipFile(dist / "libera_web-9.9.9-py3-none-any.whl", "w") as wheel:
        wheel.write(blank, "libera_web/empty/new.docx")
    work = tmp_path / "work"
    work.mkdir()
    sample = matrix.make_sample(dist, work)
    assert sample.stat().st_size > blank.stat().st_size // 2
