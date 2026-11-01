"""build/builders.toml, parsed: what it accepts, and what it refuses."""

from __future__ import annotations

from pathlib import Path

import pytest
from libera_build import inventory
from libera_build.inventory import Builder
from libera_build.release.phases import builders
from libera_build.report import RefusedError

GOOD = """
[defaults]
repo = "~/muchado"

[[builders]]
platform = "macos-arm64"
target = "local"
neutral = true

[[builders]]
platform = "linux-x86_64"
target = "fedora.zt"
dist = "~/b/out/dist"

[[builders]]
platform = "linux-arm64"
target = "arm"
repo = "~/elsewhere"
"""


def test_a_good_file_gives_every_builder_with_its_defaults():
    mac, x86, arm = inventory.parse(GOOD, "builders.toml")
    assert mac == Builder("macos-arm64", "local", None, True, "~/muchado")
    assert x86 == Builder(
        "linux-x86_64", "fedora.zt", "~/b/out/dist", False, "~/muchado"
    )
    assert arm.repo == "~/elsewhere"
    assert not mac.remote
    assert x86.remote


def test_the_architecture_comes_from_the_platform():
    mac, x86, arm = inventory.parse(GOOD, "builders.toml")
    assert (mac.arch, x86.arch, arm.arch) == ("arm64", "amd64", "arm64")


@pytest.mark.parametrize(
    ("text", "says"),
    [
        ("", "no [[builders]] entries"),
        ("[[builders]]\nplatform = 'linux-arm64'\n", "builder 1 has no target"),
        (
            "[[builders]]\nplatform = 'x'\ntarget = 'y'\nbranch = 'main'\n",
            "unknown key(s) ['branch']",
        ),
        (
            (
                "[[builders]]\nplatform = 'a'\ntarget = 'x'\nneutral = true\n"
                "[[builders]]\nplatform = 'b'\ntarget = 'y'\nneutral = true\n"
            ),
            "2 builders marked neutral",
        ),
        ("[[builders]\n", "builders.toml:"),
    ],
)
def test_a_wrong_file_is_refused_saying_why(text, says):
    with pytest.raises(RefusedError) as e:
        inventory.parse(text, "builders.toml")
    assert says in str(e.value)


def test_a_missing_file_says_how_to_make_one(tmp_path):
    with pytest.raises(RefusedError) as e:
        inventory.read(tmp_path / "builders.toml")
    assert "builders.toml.example" in str(e.value)


def test_only_narrows_and_refuses_a_builder_that_is_not_there():
    builders = inventory.parse(GOOD, "builders.toml")
    assert [b.platform for b in inventory.narrow(builders, ["linux-arm64"])] == [
        "linux-arm64"
    ]
    assert inventory.narrow(builders, []) == builders
    with pytest.raises(RefusedError) as e:
        inventory.narrow(builders, ["linux-riscv"])
    assert "no such builder: linux-riscv" in str(e.value)


def test_a_builder_with_no_dist_is_read_where_its_build_writes(monkeypatch):
    """`payload container` on Linux, `payload all` elsewhere, each under that
    system's default BUILD_ROOT; this machine's own, here. `build` checked
    one directory and `collect` fetched from another."""
    monkeypatch.setenv("BUILD_ROOT", "/here")
    mac, x86, arm = inventory.parse(GOOD, "builders.toml")
    assert inventory.dist_of(mac) == str(Path("/here") / "out" / "dist")
    assert inventory.dist_of(x86) == "~/b/out/dist"
    assert inventory.dist_of(arm) == "~/euro-office-build/linux-arm64/out/dist"
    windows = Builder("windows-x86_64", "win", None, False, "~/r")
    assert inventory.dist_of(windows) == "C:/b/out/dist"
    remote_mac = Builder("macos-x86_64", "mac", None, False, "~/r")
    assert inventory.dist_of(remote_mac).startswith("/Volumes/")


def test_a_builders_dist_reaches_its_shell_with_the_tilde_expandable():
    _, _, arm = inventory.parse(GOOD, "builders.toml")
    assert builders.version_dist(arm, "0.4") == (
        '"$HOME/euro-office-build/linux-arm64/out/dist/0.4"'
    )
