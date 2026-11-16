"""build/builders.toml, parsed: what it accepts, and what it refuses."""

from __future__ import annotations

import pytest
from libera_build import inventory
from libera_build.hosts import remote_path
from libera_build.inventory import Builder
from libera_build.report import RefusedError

GOOD = """
[defaults]
repo = "~/muchado"

[[builders]]
platform = "macos-arm64"
target = "local"

[[builders]]
platform = "linux-x86_64"
target = "fedora.zt"

[[builders]]
platform = "linux-arm64"
target = "arm"
repo = "~/elsewhere"
"""


def test_a_good_file_gives_every_builder_with_its_defaults():
    mac, x86, arm = inventory.parse(GOOD, "builders.toml")
    assert mac == Builder("macos-arm64", "local", "~/muchado")
    assert x86 == Builder("linux-x86_64", "fedora.zt", "~/muchado")
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
        # Read until the release stopped collecting core tarballs.
        (
            "[[builders]]\nplatform = 'linux-arm64'\ntarget = 'x'\ndist = '~/d'\n",
            "unknown key(s) ['dist']",
        ),
        ("[[builders]\n", "builders.toml:"),
        # A typo once read as no architecture, which skipped the check that a
        # builder is the machine it says and built a path into linux-None.
        (
            "[[builders]]\nplatform = 'linux-x86-64'\ntarget = 'x'\n",
            "builder 1: platform 'linux-x86-64' is not",
        ),
        ("[[builders]]\nplatform = 'freebsd-arm64'\ntarget = 'x'\n", "is not"),
    ],
)
def test_a_wrong_file_is_refused_saying_why(text, says):
    with pytest.raises(RefusedError) as e:
        inventory.parse(text, "builders.toml")
    assert says in str(e.value)


def test_a_missing_file_is_refused(tmp_path):
    with pytest.raises(RefusedError, match="no builder list"):
        inventory.read(tmp_path / "builders.toml")


def test_only_narrows_and_refuses_a_builder_that_is_not_there():
    builders = inventory.parse(GOOD, "builders.toml")
    assert [b.platform for b in inventory.narrow(builders, ["linux-arm64"])] == [
        "linux-arm64"
    ]
    assert inventory.narrow(builders, []) == builders
    with pytest.raises(RefusedError) as e:
        inventory.narrow(builders, ["linux-riscv"])
    assert "no such builder: linux-riscv" in str(e.value)


def test_a_path_on_a_builder_reaches_its_shell_with_the_tilde_expandable():
    assert remote_path("~/euro-office-build/linux-arm64/out/dist/0.4") == (
        '"$HOME/euro-office-build/linux-arm64/out/dist/0.4"'
    )
