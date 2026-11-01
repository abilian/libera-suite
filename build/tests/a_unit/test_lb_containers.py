"""Containers: the engine chosen, image names, and the command line a run is."""

from __future__ import annotations

import subprocess
import zipfile

import pytest
from libera_build import linux, matrix
from libera_build.containers import (
    Engine,
    Mount,
    Run,
    choose_engine,
    docker_platform,
    linux_platform,
    remote_host,
)
from libera_build.report import RefusedError


def nothing(_name):
    return None


def podman_only(name):
    return "/usr/bin/podman" if name == "podman" else None


def both(name):
    return f"/usr/bin/{name}"


def test_the_engine_is_engine_else_the_first_installed_else_docker():
    assert choose_engine({"ENGINE": "podman"}, "Darwin", both) == "podman"
    assert choose_engine({}, "Darwin", both) == "docker"
    assert choose_engine({}, "Linux", both) == "podman"
    assert choose_engine({}, "Darwin", podman_only) == "podman"
    assert choose_engine({}, "Linux", nothing) == "docker"


def test_podman_is_told_an_image_is_local_docker_is_not():
    assert (
        Engine("podman", selinux=False).image("libera-test") == "localhost/libera-test"
    )
    assert (
        Engine("podman", selinux=False).image("docker.io/library/x")
        == "docker.io/library/x"
    )
    assert Engine("docker", selinux=False).image("libera-test") == "libera-test"


def test_either_spelling_of_an_architecture_is_a_platform():
    assert docker_platform("x86_64") == docker_platform("amd64") == "linux/amd64"
    assert docker_platform("aarch64") == "linux/arm64"
    with pytest.raises(RefusedError):
        docker_platform("riscv64")


def test_every_spelling_of_an_architecture_names_one_core():
    assert linux_platform("amd64") == linux_platform("x86_64") == "linux-x86_64"
    assert linux_platform("arm64") == linux_platform("aarch64") == "linux-arm64"


def test_a_run_is_one_command_line():
    run = Run(
        "img",
        ("-c", "true"),
        "arm64",
        mounts=(Mount("/r", "/repo"), Mount("/d", "/dist", read_only=True)),
        env={"HOME": "/state"},
        workdir="/repo",
        interactive=True,
        extra=("--pull=never",),
    )
    assert Engine("docker", selinux=False).run_argv(run) == [
        "docker", "run", "--rm", "--platform", "linux/arm64", "-it",
        "-v", "/r:/repo", "-v", "/d:/dist:ro", "-e", "HOME=/state", "-w", "/repo",
        "--pull=never", "img", "-c", "true",
    ]  # fmt: skip


def test_under_selinux_a_run_asks_not_to_be_relabelled():
    argv = Engine("podman", selinux=True).run_argv(Run("img", ("true",), "amd64"))
    assert argv[5:7] == ["--security-opt", "label=disable"]


def test_the_newest_complete_payload_is_by_number(tmp_path, monkeypatch):
    for version in ("0.9", "0.10", "0.11"):
        (tmp_path / version).mkdir()
    monkeypatch.setattr(linux.locate, "is_complete", lambda d: d.name != "0.11")
    assert linux.newest_complete_payload(tmp_path).name == "0.10"
    assert linux.newest_complete_payload(tmp_path / "none") is None


def test_the_container_mounts_the_payload_and_artifacts_only_when_there(tmp_path):
    names = [m.target for m in linux.mounts_for("arm64", tmp_path / "missing", None)]
    assert names == ["/repo", "/venv", "/state"]
    names = [m.target for m in linux.mounts_for("arm64", tmp_path, tmp_path)]
    assert names == ["/repo", "/venv", "/state", "/payload", "/dist"]
    assert linux.env_for(tmp_path)["LIBERA_PAYLOAD"] == "/payload"
    assert "LIBERA_PAYLOAD" not in linux.env_for(None)


def test_every_action_that_runs_the_suite_prepares_first():
    for action in ("test", "gui", "gui-test", "dialog"):
        script = linux.script_for(linux.LinuxOptions(action))
        assert script.startswith(linux.PREPARE), action
    lint = linux.script_for(linux.LinuxOptions("lint"))
    assert lint.startswith(linux.SYNC)
    assert "--payload-install" not in lint
    assert "pytest -p no:cacheprovider -k x" in linux.script_for(
        linux.LinuxOptions("test", pytest_args=("-k", "x"))
    )
    assert not linux.script_for(linux.LinuxOptions("versions")).startswith("set -e")
    # The gui tier runs nowhere without a display and without `-m gui`: the
    # root conftest skips it twice over, so both have to be in the script.
    gui_test = linux.script_for(linux.LinuxOptions("gui-test"))
    assert "xvfb-run" in gui_test
    assert "-m gui" in gui_test


def odt(path, text):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("content.xml", f"<office:text><text:p>{text}</text:p></office:text>")
    return path


def test_a_conversion_is_believed_by_its_text(tmp_path):
    assert matrix.holds_text(
        odt(tmp_path / "a.odt", "Second paragraph"), "Second paragraph"
    )
    assert not matrix.holds_text(odt(tmp_path / "b.odt", "nothing"), "Second paragraph")
    assert not matrix.holds_text(tmp_path / "missing.odt", "x")
    (tmp_path / "c.odt").write_bytes(b"not a zip")
    assert not matrix.holds_text(tmp_path / "c.odt", "x")


def answer(endpoint: str):
    def run(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, stdout=f"{endpoint}\n")

    return run


def test_a_docker_context_over_ssh_is_another_machine():
    run = answer("ssh://fermigier@fedora.local")
    assert remote_host("docker", {}, run) == "ssh://fermigier@fedora.local"
    assert remote_host("docker", {}, answer("unix:///var/run/docker.sock")) is None
    assert remote_host("docker", {"DOCKER_HOST": "tcp://x:2375"}, run) == "tcp://x:2375"
    assert remote_host("podman", {}, run) is None
