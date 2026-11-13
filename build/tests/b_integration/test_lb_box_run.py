"""tidy, the build container's export, and the window check, run for real
against scratch directories and a LocalHost builder."""

from __future__ import annotations

import shutil
import sys

import pytest
from libera_build import buildbox, released_gui, tidy, versions
from libera_build.buildbox import BoxOptions
from libera_build.containers import Engine
from libera_build.hosts import LocalHost
from libera_build.repo import REPO
from libera_build.report import RefusedError


def test_tidy_lists_on_a_dry_run_then_removes(tmp_path, capsys):
    root = tmp_path / "repo"
    (root / "build" / "out").mkdir(parents=True)
    (root / "build" / "out" / "big").write_bytes(b"x" * 4096)
    build_root = tmp_path / "build-root"
    (build_root / "src").mkdir(parents=True)
    tidy.tidy(root, build_root, dry_run=True)
    assert "nothing removed" in capsys.readouterr().out
    assert (root / "build" / "out").exists()
    tidy.tidy(root, build_root, yes=True)
    assert not (root / "build" / "out").exists()
    assert not build_root.exists()
    tidy.tidy(root, build_root, yes=False)
    assert "nothing to tidy" in capsys.readouterr().out


def test_an_export_is_believed_by_its_content(tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path))
    version = versions.payload_version(REPO)
    out = tmp_path / "linux-arm64" / "out" / "dist" / version
    box = buildbox.Box(BoxOptions(arch="arm64"))
    with pytest.raises(RefusedError, match=r"no manifest\.json"):
        box.exported()
    out.mkdir(parents=True)
    (out / "manifest.json").write_text("{}")
    with pytest.raises(RefusedError, match="no tarballs"):
        box.exported()
    (out / "core-linux-arm64.tar.gz").write_bytes(b"x")
    assert box.exported() == out


# An engine that runs the container's script here instead, with /build being
# $FAKE_VOLUME: the tar pipe, both ends real, and no container.
ENGINE = """#!/bin/sh
for last; do :; done
exec sh -c "$(printf '%s' "$last" | sed "s#/build#$FAKE_VOLUME#g")"
"""


@pytest.fixture
def volume_box(tmp_path, monkeypatch):
    """A Box on a volume, the volume a directory, and this machine's dist."""
    engine = tmp_path / "engine"
    engine.write_text(ENGINE)
    engine.chmod(0o755)
    monkeypatch.setenv("FAKE_VOLUME", str(tmp_path / "volume"))
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "here"))
    box = buildbox.Box(BoxOptions(volume="vol"), Engine(str(engine), selinux=False))
    version = versions.payload_version(REPO)
    return (
        box,
        tmp_path / "volume" / "out" / "dist" / version,
        tmp_path / "here" / "out" / "dist" / version,
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the stand-in is an sh script, which Windows does not run",
)
def test_an_export_that_brought_nothing_is_not_an_earlier_ones(volume_box):
    """The volume holds no build; this machine holds an earlier export's
    manifest and tarball, which the check used to find and believe."""
    box, _, here = volume_box
    here.mkdir(parents=True)
    (here / "manifest.json").write_text("{}")
    (here / "core-linux-x86_64.tar.gz").write_bytes(b"the last one")
    with pytest.raises(RefusedError, match="out of the volume vol failed"):
        box.exported()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the stand-in is an sh script, which Windows does not run",
)
def test_an_export_lands_beside_what_this_machine_has(volume_box):
    box, built, here = volume_box
    built.mkdir(parents=True)
    (built / "manifest.json").write_text("{}")
    (built / "core-linux-x86_64.tar.gz").write_bytes(b"this one")
    here.mkdir(parents=True)
    (here / "core-macos-arm64.tar.gz").write_bytes(b"this machine's")
    assert box.exported() == here
    assert (here / "core-linux-x86_64.tar.gz").read_bytes() == b"this one"
    assert (here / "core-macos-arm64.tar.gz").read_bytes() == b"this machine's"
    assert sorted(p.name for p in here.parent.iterdir()) == [here.name]


def test_a_machine_without_the_tools_says_which_and_is_no_pass(tmp_path, capsys):
    """The real script, on a LocalHost builder: this machine has no Xvfb, or
    no flatpak, and the script must say so rather than pass."""
    if shutil.which("xvfb-run") and shutil.which("flatpak"):
        pytest.skip("this machine could actually draw the window")
    # A checkout of its own, with the real script and one builder: this one.
    root = tmp_path / "repo"
    shutil.copytree(REPO / "build" / "install", root / "build" / "install")
    (root / "tests" / "d_gui").mkdir(parents=True)
    shutil.copy(REPO / "tests" / "d_gui" / "driver.py", root / "tests" / "d_gui")
    (root / "build" / "builders.toml").write_text(
        '[[builders]]\nplatform = "linux-x86_64"\ntarget = "here"\n'
    )
    options = released_gui.ReleasedGuiOptions(
        root=root, host_for=lambda _: LocalHost(tmp_path)
    )
    assert not released_gui.on_host(LocalHost(tmp_path), "here", options)
    out = capsys.readouterr().out
    assert "this machine has no" in out or "is not installed" in out
    assert (tmp_path / "released-gui.sh").is_file(), "the script was sent"
    with pytest.raises(RefusedError, match="did not draw a window"):
        released_gui.run(options)
