"""The installed `lb` command, end to end: the console script, real scripts.

Read-only commands only: each runs a real script from build/ and checks what it
printed. The long ones, a build or a release, are checked by running them on
the builders, which no test here can stand in for.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sysconfig
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from libera_build import cli, repo, versions
from libera_build.containers import Engine, host_arch

from libera.manifest import Manifest


def find_lb() -> str:
    """The console script uv installed, beside this interpreter's."""
    found = Path(sysconfig.get_path("scripts")) / "lb"
    if found.is_file():
        return str(found)
    return shutil.which("lb") or pytest.skip("no `lb` installed: run `uv sync`")


def lb(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [find_lb(), *args],
        cwd=cli.REPO,
        env=None if env is None else os.environ | env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def test_help_lists_every_command():
    done = lb("--help")
    assert done.returncode == 0, done.stderr
    groups = cli.Groups(cli.argparse.ArgumentParser())
    for add in (
        cli.add_payload,
        cli.add_toolchain,
        cli.add_app,
        cli.add_linux,
        cli.add_release,
        cli.add_others,
    ):
        add(groups)
    for name, _ in groups.listing:
        assert f"  {name} " in done.stdout, name


def test_a_mistyped_command_says_so_and_runs_nothing():
    done = lb("payload", "biuld")
    assert done.returncode == 2
    assert "invalid choice" in done.stderr
    assert "+ " not in done.stdout


def test_tidy_lists_without_deleting(tmp_path):
    """Against an empty BUILD_ROOT: the real one is millions of files, which du
    took more than the timeout to sum on the Windows builder."""
    done = lb("tidy", env={"BUILD_ROOT": str(tmp_path / "build-root")})
    assert done.returncode == 0, done.stderr
    assert "nothing removed" in done.stdout or "nothing to tidy" in done.stdout


def test_toolchain_list_names_this_machines_packages():
    done = lb("toolchain", "list")
    assert done.returncode == 0, done.stderr
    assert "+ sh build/engine/toolchain.sh list" in done.stdout


def test_patches_still_apply_to_the_pins():
    """The real check, in scratch worktrees of the pinned sources (~20 s).

    check-patches.sh says SKIP for a repository it has no checkout of, and
    still ends with "patch queue: clean": so the SKIP lines are what decide
    whether this checked anything.
    """
    done = lb("payload", "patches")
    skipped = [line for line in done.stdout.splitlines() if line.startswith("SKIP")]
    if skipped:
        pytest.skip(f"pinned sources not cloned here: {skipped[0]}")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "patch queue: clean" in done.stdout
    assert done.stdout.count("  ok   ") >= 2, done.stdout


def test_release_plan_names_every_builder():
    builders = cli.REPO / "build" / "builders.toml"
    if not builders.is_file():
        pytest.skip("no build/builders.toml here")
    done = lb("release", "plan")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "phases   update, native, build" in done.stdout
    platforms = [
        line.split('"')[1]
        for line in builders.read_text(encoding="utf-8").splitlines()
        if line.startswith("platform")
    ]
    for platform in platforms:
        assert platform in done.stdout


def test_a_refusal_is_a_sentence_and_a_failure():
    if not (cli.REPO / "build" / "builders.toml").is_file():
        pytest.skip("no build/builders.toml here")
    done = lb("release", "ship", "--only", "linux-riscv")
    assert done.returncode == 1
    assert "FATAL: no such builder: linux-riscv" in done.stderr
    assert "Traceback" not in done.stderr


def test_linux_versions_runs_the_test_image():
    """`lb linux versions`: the engine, the image, a container, its output.

    Only where the image is already built: `lb linux` builds a missing one
    first, which is minutes, and not this test's to spend.
    """
    engine = Engine.here()
    if shutil.which(engine.name) is None:
        pytest.skip(f"no {engine.name} here")
    if subprocess.run(
        [engine.name, "info"], capture_output=True, check=False
    ).returncode:
        pytest.skip(f"{engine.name} is not running")
    if not engine.has_image(engine.image(f"libera-test-linux-{host_arch()}")):
        pytest.skip("no test image here: lb linux image")
    done = lb("linux", "versions")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "==> versions, on Linux" in done.stdout
    assert "uv" in done.stdout


def test_push_dry_lists_every_upload_and_needs_no_token(monkeypatch):
    stamped = cli.REPO / "src" / "libera" / "manifest.json"
    if not stamped.is_file():
        pytest.skip("no manifest stamped in this checkout")
    version = versions.payload_version(cli.REPO)
    if Manifest.read(stamped).payload_version != version:
        pytest.skip(f"payload {version} is not collected yet")
    collected = repo.dist(version)
    if not (collected / "manifest.json").is_file():
        pytest.skip(f"nothing collected to push in {collected}")
    monkeypatch.delenv("CDN_TOKEN", raising=False)
    done = lb("release", "push", "--dry-run")
    if "dirty tree" in done.stderr:
        pytest.skip("the stamped manifest is from a dirty tree; push refuses it first")
    assert done.returncode == 0, done.stdout + done.stderr
    puts = [line for line in done.stdout.splitlines() if "would PUT" in line]
    assert puts
    assert "manifest.json" in puts[-1], "the manifest goes last"


def origin_reachable() -> bool:
    try:
        with urllib.request.urlopen("https://cdn.abilian.com/libera/", timeout=10):
            return True
    except urllib.error.HTTPError:
        return True  # it answered
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def test_status_reads_the_tree_the_origin_and_pypi():
    if not origin_reachable():
        pytest.skip("the origin cannot be reached from here")
    done = lb("release", "status")
    assert done.returncode == 0, done.stdout + done.stderr
    for heading in ("versions", "this tree", "the origin, and PyPI", "next"):
        assert f"==> {heading}" in done.stdout
    assert "PyPI         latest " in done.stdout, "PyPI was not read"


def test_check_quick_reads_the_live_origin_as_a_stranger(monkeypatch):
    if not origin_reachable():
        pytest.skip("the origin cannot be reached from here")
    monkeypatch.delenv("CDN_TOKEN", raising=False)
    done = lb("release", "check", "--quick", "--wheel", "pypi")
    if "is not on PyPI" in done.stdout + done.stderr:
        pytest.skip("this version is between its bump and its publish")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "as PyPI serves it" in done.stdout
    assert "manifest.json                present" in done.stdout


def test_the_build_container_says_what_it_is_pinned_to():
    engine = Engine.here()
    if shutil.which(engine.name) is None:
        pytest.skip(f"no {engine.name} here")
    if subprocess.run(
        [engine.name, "info"], capture_output=True, check=False
    ).returncode:
        pytest.skip(f"{engine.name} is not running")
    arch = host_arch()
    if not engine.has_image(engine.image(f"libera-build-linux-{arch}")):
        pytest.skip("no build image here: lb payload container --image")
    done = lb("payload", "container", "--arch", arch, "--versions")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "base:" in done.stdout
