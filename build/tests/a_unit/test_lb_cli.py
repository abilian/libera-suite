"""`lb`: each command line reaches the scripts it names.

Commands are pure functions from their arguments to the steps they would run,
so these run nothing: they compare the steps.
"""

from __future__ import annotations

import inspect
import shlex
from pathlib import Path

import pytest
from libera_build import bench, buildbox, cli, containers, flatpak, linux, matrix, tidy
from libera_build.buildbox import BoxOptions
from libera_build.cli import Step
from libera_build.containers import host_arch
from libera_build.flatpak import FlatpakOptions
from libera_build.linux import LinuxOptions
from libera_build.matrix import MatrixOptions
from libera_build.origin import verbs
from libera_build.origin.verbs import OriginOptions
from libera_build.release.on import OnOptions
from libera_build.release.ship import ShipOptions, ship


def sh(script, *args, **env):
    return Step(("sh", f"build/{script}", *args), env)


TOOLCHAIN = sh("engine/toolchain.sh", "check")


@pytest.mark.parametrize(
    ("argv", "steps"),
    [
        (["payload", "fetch"], [TOOLCHAIN, sh("engine/build.sh", "fetch")]),
        (
            ["payload", "fetch", "core", "--mirror", "/m"],
            [
                sh("engine/toolchain.sh", "check", MIRROR="/m"),
                sh("engine/build.sh", "fetch", "core", MIRROR="/m"),
            ],
        ),
        (
            ["payload", "core", "--v8-jobs", "4"],
            [
                sh("engine/toolchain.sh", "check", V8_BUILD_JOBS="4"),
                sh("engine/build.sh", "build", V8_BUILD_JOBS="4"),
            ],
        ),
        (["payload", "dist"], [TOOLCHAIN, sh("engine/dist.sh", "--fonts", "core")]),
        (
            ["payload", "dist", "--fonts", "full", "--manifest-only"],
            [TOOLCHAIN, sh("engine/dist.sh", "--fonts", "full", "--manifest-only")],
        ),
        (
            ["payload", "all"],
            [
                TOOLCHAIN,
                sh("engine/build.sh", "fetch"),
                sh("engine/build.sh", "configure"),
                sh("engine/build.sh", "build"),
                sh("engine/payload.sh"),
                sh("engine/dist.sh", "--fonts", "core"),
                sh("engine/smoke.sh"),
            ],
        ),
        (
            ["payload", "install", "--from", "/d"],
            [Step(("uv", "run", "libera", "--payload-install", "--from", "/d"))],
        ),
        (["payload", "patches"], [sh("engine/check-patches.sh")]),
        (["toolchain", "list"], [sh("engine/toolchain.sh", "list")]),
        (["app", "macos", "--standalone"], [sh("macos/macos-app.sh", STANDALONE="1")]),
    ],
)
def test_a_command_line_runs_its_scripts(argv, steps):
    assert cli.plan(argv) == steps


def test_ship_is_called_here_with_its_phases_and_options():
    (call,) = cli.plan([
        "release",
        "ship",
        "build",
        "bundles",
        "--only",
        "linux-arm64",
        "--yes",
    ])
    assert call == cli.Call(
        ship,
        (ShipOptions(phases=("build", "bundles"), only=("linux-arm64",), yes=True),),
    )


def test_plan_is_ship_dry():
    (call,) = cli.plan(["release", "plan", "build"])
    assert call == cli.Call(ship, (ShipOptions(phases=("build",), dry_run=True),))


def test_an_unknown_phase_is_refused():
    with pytest.raises(SystemExit):
        cli.plan(["release", "ship", "biuld"])


# Commands that need arguments, and a line for each to plan with.
NEEDS_ARGUMENTS = {"on": ["linux-arm64", "app", "flatpak-smoke"]}


def every_command_line() -> list[list[str]]:
    """Every command the top-level help lists, with what it needs to plan."""
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
    return [[*n.split(), *NEEDS_ARGUMENTS.get(n, [])] for n, _ in groups.listing]


def test_every_listed_command_plans():
    """The top-level help lists them, so each must at least plan."""
    lines = every_command_line()
    assert len(lines) > 30
    for line in lines:
        assert cli.plan(line), line


def test_every_step_names_a_script_that_exists():
    for argv in (
        ["payload", "all"],
        ["payload", "container"],
        ["app", "flatpak"],
        ["linux", "gui"],
    ):
        for step in cli.plan(argv):
            if isinstance(step, Step) and step.argv[0] == "sh" and step.argv[1] != "-c":
                assert (cli.REPO / step.argv[1]).is_file(), step


def test_bench_passes_its_options_on():
    (call,) = cli.plan(["bench", "doc.docx", "--runs", "5"])
    assert call == cli.Call(bench.main, (["doc.docx", "--runs", "5"],))


def test_an_unknown_option_is_refused_where_nothing_takes_it():
    with pytest.raises(SystemExit):
        cli.plan(["payload", "core", "--v8jobs", "4"])


def test_linux_is_called_here_with_its_options(monkeypatch):
    monkeypatch.delenv("ARCH", raising=False)
    monkeypatch.delenv("DIST", raising=False)
    monkeypatch.delenv("PAYLOAD", raising=False)
    monkeypatch.delenv("LINUX_LANG", raising=False)
    (call,) = cli.plan(["linux", "test", "-k", "bridge", "--arch", "arm64"])
    assert call == cli.Call(
        linux.run,
        (LinuxOptions("test", arch="arm64", pytest_args=("-k", "bridge")),),
        env={"ARCH": "arm64"},
    )


def test_an_argument_for_pytest_with_a_space_in_it_stays_one():
    (call,) = cli.plan(["linux", "test", "-k", "bridge and save"])
    line = linux.script_for(call.args[0]).splitlines()[-1]
    assert shlex.split(line)[-2:] == ["-k", "bridge and save"]


def test_an_environment_variable_still_sets_a_knob(monkeypatch):
    monkeypatch.setenv("PAYLOAD", "/p")
    monkeypatch.delenv("ARCH", raising=False)
    monkeypatch.delenv("DIST", raising=False)
    (call,) = cli.plan(["linux", "gui"])
    assert call.args[0].payload == Path("/p")


def test_matrix_takes_its_lists_as_words(monkeypatch):
    for name in ("DIST", "DISTROS", "ARCHES"):
        monkeypatch.delenv(name, raising=False)
    (call,) = cli.plan([
        "release",
        "matrix",
        "--distros",
        "a:1 b:2",
        "--arches",
        "arm64",
    ])
    assert call == cli.Call(
        matrix.run,
        (MatrixOptions(distros=("a:1", "b:2"), arches=("arm64",)),),
        env={"DISTROS": "a:1 b:2", "ARCHES": "arm64"},
    )


@pytest.mark.parametrize(
    ("argv", "options", "env"),
    [
        (["release", "status"], OriginOptions("status"), {}),
        (
            ["release", "push", "--dry-run"],
            OriginOptions("push", dry_run=True),
            {"DRY": "1"},
        ),
        (
            ["release", "check", "--quick", "--wheel", "pypi"],
            OriginOptions("check", quick=True, wheel="pypi"),
            {"QUICK": "1", "WHEEL": "pypi"},
        ),
        (["release", "windows"], OriginOptions("windows"), {}),
    ],
)
def test_the_origin_verbs_are_called_here(argv, options, env, monkeypatch):
    for name in ("DRY", "QUICK", "WHEEL", "BUILD_ROOT"):
        monkeypatch.delenv(name, raising=False)
    assert cli.plan(argv) == [cli.Call(verbs.run, (options,), env=env)]


def test_dry_still_works_as_an_environment_variable(monkeypatch):
    monkeypatch.setenv("DRY", "1")
    (call,) = cli.plan(["release", "push"])
    assert call.args[0].dry_run


@pytest.fixture
def no_knobs(monkeypatch):
    for name in (
        "ARCH", "DIST", "BUILD_DIR", "VOLUME", "DOCKER_MEMORY", "MIRROR",
        "V8_BUILD_JOBS", "CORE_BUILD_JOBS", "BUILD_ROOT", "YES",
    ):  # fmt: skip
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    "argv",
    [
        ["payload", "export"],
        ["payload", "install"],
        ["payload", "container", "--versions"],
        ["release", "status"],
        ["release", "push"],
    ],
)
def test_build_root_reaches_a_command_done_in_this_process(argv, no_knobs):
    """As its variable, the way it reaches a script: these read $BUILD_ROOT
    where the scripts they replaced did, and dropped the option."""
    (call,) = cli.plan([*argv, "--build-root", "/x"])
    assert call.env["BUILD_ROOT"] == "/x"


def test_the_container_builds_what_payload_all_builds():
    """One sequence, run here by `payload all` and in the container by
    `payload container`: the two were written out twice."""
    _toolchain, *steps = cli.plan(["payload", "all"])
    assert buildbox.ALL.splitlines() == [
        "set -e",
        *(shlex.join(step.argv[1:]) for step in steps),
    ]


def test_the_payload_container_is_the_whole_build_or_one_script(no_knobs):
    (call,) = cli.plan(["payload", "container", "--arch", "arm64", "--memory", "12g"])
    assert call.fn.__name__ == "all"
    assert call.fn.__self__.options == BoxOptions(arch="arm64", memory="12g")
    (call,) = cli.plan(["payload", "container", "dist.sh", "--fonts", "core"])
    assert call.fn.__name__ == "script"
    assert call.args == ("dist.sh", ["--fonts", "core"])
    (call,) = cli.plan(["payload", "container", "--shell"])
    assert call.args == ("exec /bin/bash",)


def test_install_without_a_source_takes_the_container_build(no_knobs):
    (call,) = cli.plan(["payload", "install", "--arch", "arm64"])
    assert call == cli.Call(
        cli.install_exported, (BoxOptions(arch="arm64"),), env={"ARCH": "arm64"}
    )


def test_the_flatpak_defaults_to_this_machines_architecture(no_knobs):
    (call,) = cli.plan(["app", "flatpak-smoke"])
    assert call == cli.Call(flatpak.run, (FlatpakOptions("smoke", arch=host_arch()),))
    (call,) = cli.plan(["app", "flatpak", "--arch", "amd64", "--dist", "/d"])
    assert call.args[0] == FlatpakOptions("build", arch="amd64", dist=Path("/d"))


def test_released_gui_is_every_builder_unless_one_is_named():
    (call,) = cli.plan(["release", "released-gui", "--on", "h"])
    assert call.args[0].on == "h"
    (call,) = cli.plan(["release", "released-gui"])
    assert call.args[0].on is None


def test_tidy_is_a_list_unless_yes(no_knobs):
    (call,) = cli.plan(["tidy", "--yes", "--build-root", "/b"])
    assert call == cli.Call(
        tidy.tidy,
        (cli.REPO, Path("/b")),
        {"yes": True},
        env={"YES": "1", "BUILD_ROOT": "/b"},
    )
    (call,) = cli.plan(["tidy"])
    assert call.kwargs == {"yes": False}


def test_yes_still_works_as_an_environment_variable(no_knobs, monkeypatch):
    monkeypatch.setenv("YES", "1")
    (call,) = cli.plan(["tidy"])
    assert call.kwargs == {"yes": True}


def test_every_call_matches_the_signature_it_calls(no_knobs):
    """A Call is planned in one place and made in another, and a unit test that
    compares the plan never makes it: tidy's `yes` was passed by position to a
    keyword-only parameter, and only running `lb tidy` found it."""
    for line in every_command_line():
        for step in cli.plan(line):
            if isinstance(step, cli.Call):
                inspect.signature(step.fn).bind(*step.args, **step.kwargs)


def test_on_runs_the_rest_of_the_line_on_a_builder():
    (call,) = cli.plan([
        "on",
        "linux-arm64",
        "--update",
        "linux",
        "lint",
        "--arch",
        "arm64",
    ])
    assert call.args[0] == OnOptions(
        "linux-arm64", ("linux", "lint", "--arch", "arm64"), update=True
    )


def test_on_wants_a_command():
    with pytest.raises(SystemExit):
        cli.plan(["on", "linux-arm64"])


def test_toolchain_install_on_windows_is_the_setup_script():
    (step,) = cli.toolchain_steps("install", "win32")
    assert step.argv[0] == "powershell"
    assert step.argv[-1] == "build/windows/windows-setup.ps1"
    assert cli.toolchain_steps("check", "win32") == [sh("engine/toolchain.sh", "check")]
    assert cli.toolchain_steps("install", "linux") == [
        sh("engine/toolchain.sh", "install")
    ]


def test_a_dry_toolchain_install_installs_nothing():
    (step,) = cli.toolchain_steps("install", "win32", dry=True)
    assert step.argv[-1] == "-DryRun"
    assert cli.toolchain_steps("install", "linux", dry=True) == [
        sh("engine/toolchain.sh", "list")
    ]
    (step,) = cli.plan(["toolchain", "install", "--dry-run"])
    assert step.argv[-1] in {"-DryRun", "list"}


def test_the_flatpak_takes_the_container_builds_payload_when_given_none(
    monkeypatch, tmp_path
):
    """A Linux builder builds its payload in the container, so `out/dist` is
    empty there: a hand-run `app flatpak` failed on a manifest it never had."""
    monkeypatch.setattr(buildbox, "exported_dist", lambda arch: tmp_path / arch)
    engine = containers.Engine("docker", selinux=False)

    builder = flatpak.Builder(FlatpakOptions("build", arch="amd64"), engine)

    assert builder.dist == tmp_path / "amd64"


def test_linux_gui_takes_a_language(monkeypatch):
    monkeypatch.delenv("LINUX_LANG", raising=False)
    (call,) = cli.plan(["linux", "gui", "--lang", "fr_FR.UTF-8"])
    assert call.args[0].lang == "fr_FR.UTF-8"
