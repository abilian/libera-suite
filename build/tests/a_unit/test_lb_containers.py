"""Containers: the engine chosen, image names, and the command line a run is."""

from __future__ import annotations

import re
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


def test_the_container_mounts_the_wheels_or_the_payload_it_was_given(tmp_path):
    names = [m.target for m in linux.mounts_for("arm64", None, None)]
    assert names == ["/repo", "/venv", "/state"]
    names = [m.target for m in linux.mounts_for("arm64", tmp_path, None)]
    assert names == ["/repo", "/venv", "/state", "/wheels"]
    names = [m.target for m in linux.mounts_for("arm64", None, tmp_path)]
    assert names == ["/repo", "/venv", "/state", "/payload"]
    assert linux.env_for(tmp_path)["LIBERA_PAYLOAD"] == "/payload"
    assert "LIBERA_PAYLOAD" not in linux.env_for(None)


def test_the_suite_takes_the_wheels_of_its_architecture_only(tmp_path):
    """A Mac's own wheels are macOS binaries: the folder counts only with a
    Linux core of the container's architecture in it."""
    (tmp_path / "libera_core-0.7-py3-none-macosx_14_0_arm64.whl").touch()
    options = linux.LinuxOptions("test", wheels=tmp_path)

    with pytest.raises(RefusedError, match="no libera-core wheel for linux-x86_64"):
        linux.choose_payload(options, "amd64")

    (tmp_path / "libera_core-0.7-py3-none-manylinux_2_34_x86_64.whl").touch()
    assert linux.choose_payload(options, "amd64") == (tmp_path, None)


def test_the_suite_installs_the_core_of_its_architecture_only(tmp_path):
    """A folder of wheels keeps what earlier builds left, and uv refuses to
    install two wheels of one package: `lb linux test` stopped on a core built
    before the Linux tag changed."""
    kept = "libera_core-0.7-py3-none-manylinux_2_34_x86_64.whl"
    (tmp_path / kept).touch()
    (tmp_path / "libera_core-0.7-py3-none-manylinux_2_35_x86_64.whl").touch()
    (tmp_path / "libera_core-0.7-py3-none-macosx_14_0_arm64.whl").touch()

    script = linux.script_for(linux.LinuxOptions("test", arch="amd64"))
    pattern = re.search(r"/wheels/(libera_core-\S+)", script)[1]

    assert [path.name for path in tmp_path.glob(pattern)] == [kept]


def test_the_container_speaks_the_language_asked_for_and_no_other():
    assert linux.env_for(None, "fr_FR.UTF-8")["LANG"] == "fr_FR.UTF-8"
    assert "LANG" not in linux.env_for(None)


def test_every_action_that_runs_the_suite_prepares_first():
    for action in ("test", "gui", "gui-test", "dialog"):
        script = linux.script_for(linux.LinuxOptions(action, arch="amd64"))
        assert script.startswith(linux.prepare("amd64")), action
    lint = linux.script_for(linux.LinuxOptions("lint"))
    assert lint.startswith(linux.SYNC)
    assert "components unpack" not in lint
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


def test_the_matrix_runs_the_staged_wheel_with_its_modes(tmp_path):
    whl = tmp_path / "libera_core-9.9.9-py3-none-manylinux_2_34_aarch64.whl"
    with zipfile.ZipFile(whl, "w") as z:
        x2t = zipfile.ZipInfo("libera_core/bin/x2t")
        x2t.external_attr = 0o755 << 16
        z.writestr(x2t, "elf")
    assert matrix.core_of(tmp_path, "arm64") == whl
    with pytest.raises(RefusedError, match="x86_64"):
        matrix.core_of(tmp_path, "amd64")
    core = matrix.unpack(whl, tmp_path / "core")
    assert (core / "bin" / "x2t").stat().st_mode & 0o777 == 0o755


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


def test_an_engine_that_is_not_installed_is_refused_by_name():
    with pytest.raises(RefusedError, match="no libera-no-such-engine here"):
        Engine("libera-no-such-engine").refuse_absent()
