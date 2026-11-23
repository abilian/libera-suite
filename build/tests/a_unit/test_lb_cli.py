"""`lb`: each command line reaches the scripts it names.

Commands are pure functions from their arguments to the steps they would run,
so these run nothing: they compare the steps.
"""

from __future__ import annotations

import inspect
import shlex
from pathlib import Path

import pytest
from libera_build import bench, buildbox, cli, flatpak, linux, tidy
from libera_build.buildbox import BoxOptions
from libera_build.cli import Step
from libera_build.containers import host_arch
from libera_build.flatpak import FlatpakOptions
from libera_build.linux import LinuxOptions
from libera_build.release.on import OnOptions
from libera_build.release.run import RunOptions, run


def sh(script, *args, **env):
    return Step(("sh", f"build/{script}", *args), env)


TOOLCHAIN = sh("engine/toolchain.sh", "check")


@pytest.mark.parametrize(
    ("argv", "steps"),
    [
        (["payload", "build", "fetch"], [TOOLCHAIN, sh("engine/build.sh", "fetch")]),
        (
            ["payload", "build", "fetch", "--repo", "core", "--mirror", "/m"],
            [
                sh("engine/toolchain.sh", "check", MIRROR="/m"),
                sh("engine/build.sh", "fetch", "core", MIRROR="/m"),
            ],
        ),
        (
            ["payload", "build", "core", "--v8-jobs", "4"],
            [
                sh("engine/toolchain.sh", "check", V8_BUILD_JOBS="4"),
                sh("engine/build.sh", "build", V8_BUILD_JOBS="4"),
            ],
        ),
        (
            ["payload", "build", "dist"],
            [TOOLCHAIN, sh("engine/dist.sh", "--fonts", "core")],
        ),
        (
            ["payload", "build", "dist", "--fonts", "full", "--manifest-only"],
            [TOOLCHAIN, sh("engine/dist.sh", "--fonts", "full", "--manifest-only")],
        ),
        (
            ["payload", "build"],
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
        (["payload", "check"], [sh("engine/check-patches.sh")]),
        (
            ["payload", "build", "configure", "fetch"],
            [
                TOOLCHAIN,
                sh("engine/build.sh", "fetch"),
                sh("engine/build.sh", "configure"),
            ],
        ),
        (["toolchain", "list"], [sh("engine/toolchain.sh", "list")]),
        (
            ["app", "build", "macos", "--standalone"],
            [sh("macos/macos-app.sh", STANDALONE="1")],
        ),
        (["app", "build", "macos-launcher"], [sh("macos/launcher.sh")]),
        (["app", "test", "windows"], [sh("windows/gui-test.sh")]),
        (
            ["app", "build", "windows", "--wheels", "/w"],
            [sh("windows/windows-app.sh", BUNDLE_WHEELS="/w")],
        ),
    ],
)
def test_a_command_line_runs_its_scripts(argv, steps):
    assert cli.plan(argv) == steps


@pytest.mark.parametrize(
    "argv",
    [
        ["payload", "build", "core", "--fonts", "full"],
        ["payload", "build", "dist", "--repo", "core"],
        ["app", "build", "flatpak", "--standalone"],
        ["app", "build", "macos", "--arch", "arm64"],
        ["app", "test", "windows", "--arch", "arm64"],
        ["app", "build", "macos", "--wheels", "/w"],
    ],
)
def test_an_option_for_a_stage_or_target_not_run_is_refused(argv):
    with pytest.raises(cli.RefusedError, match="which this does not run"):
        cli.plan(argv)


def test_check_is_called_here_with_its_phases_and_options():
    (call,) = cli.plan([
        "release",
        "check",
        "components",
        "bundles",
        "--only",
        "linux-arm64",
    ])
    options = RunOptions("check", ("components", "bundles"), only=("linux-arm64",))
    assert call == cli.Call(run, (options,))


def test_publish_asks_unless_yes_and_narrows_nothing():
    (call,) = cli.plan(["release", "publish", "0.7.5", "--yes"])
    assert call == cli.Call(run, (RunOptions("publish", version="0.7.5", yes=True),))
    with pytest.raises(SystemExit):
        cli.plan(["release", "publish", "0.7.5", "--only", "linux-arm64"])
    with pytest.raises(SystemExit):
        cli.plan(["release", "publish"])


def test_check_fast_is_passed_on():
    (call,) = cli.plan(["release", "check", "--fast"])
    assert call == cli.Call(run, (RunOptions("check", fast=True),))


def test_dry_run_runs_nothing():
    (call,) = cli.plan(["release", "check", "bundles", "--dry-run"])
    assert call == cli.Call(run, (RunOptions("check", ("bundles",), dry_run=True),))


def test_the_old_commands_are_gone():
    for old in ("ship", "plan", "upload", "bump"):
        with pytest.raises(SystemExit):
            cli.plan(["release", old])


# Commands that need arguments, and a line for each to plan with.
NEEDS_ARGUMENTS = {
    "on": ["linux-arm64", "app", "test", "flatpak"],
    "release publish": ["0.7.5"],
    "app build": ["macos"],
    "app check": ["flatpak"],
    "app test": ["flatpak"],
    "release check": ["distros"],
    "container run": ["payload"],
    "container export": ["payload"],
    "container shell": ["linux"],
    "container versions": ["linux"],
    "container image": ["linux"],
    "container clean": ["flatpak", "--yes"],
}


def every_command_line() -> list[list[str]]:
    """Every command the top-level help lists, with what it needs to plan."""
    groups = cli.Groups(cli.argparse.ArgumentParser())
    for add in cli.GROUPS:
        add(groups)
    return [[*n.split(), *NEEDS_ARGUMENTS.get(n, [])] for n, _ in groups.listing]


def test_every_listed_command_plans():
    """The top-level help lists them, so each must at least plan."""
    lines = every_command_line()
    assert len(lines) > 25
    for line in lines:
        assert cli.plan(line), line


def test_every_step_names_a_script_that_exists():
    for argv in (
        ["payload", "build"],
        ["container", "run", "payload"],
        ["app", "build", "flatpak"],
        ["linux", "screenshot"],
    ):
        for step in cli.plan(argv):
            if isinstance(step, Step) and step.argv[0] == "sh" and step.argv[1] != "-c":
                assert (cli.REPO / step.argv[1]).is_file(), step


def test_bench_passes_its_options_on():
    (call,) = cli.plan(["bench", "doc.docx", "--runs", "5"])
    assert call == cli.Call(bench.main, (["doc.docx", "--runs", "5"],))


def test_an_unknown_option_is_refused_where_nothing_takes_it():
    with pytest.raises(SystemExit):
        cli.plan(["payload", "build", "core", "--v8jobs", "4"])


def test_linux_is_called_here_with_its_options(monkeypatch):
    monkeypatch.delenv("ARCH", raising=False)
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
    (call,) = cli.plan(["linux", "screenshot"])
    assert call.args[0].payload == Path("/p")


def test_dry_still_works_as_an_environment_variable(monkeypatch):
    monkeypatch.setenv("DRY", "1")
    (call,) = cli.plan(["tidy"])
    assert call.kwargs["dry_run"]


@pytest.fixture
def no_knobs(monkeypatch):
    for name in (
        "ARCH", "BUILD_DIR", "VOLUME", "DOCKER_MEMORY", "MIRROR",
        "V8_BUILD_JOBS", "CORE_BUILD_JOBS", "BUILD_ROOT", "YES", "BUNDLE_WHEELS",
    ):  # fmt: skip
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    "argv",
    [
        ["container", "export", "payload"],
        ["container", "run", "payload"],
        ["tidy"],
    ],
)
def test_build_root_reaches_a_command_done_in_this_process(argv, no_knobs):
    """As its variable, the way it reaches a script: these read $BUILD_ROOT
    where the scripts they replaced did, and dropped the option."""
    (call,) = cli.plan([*argv, "--build-root", "/x"])
    assert call.env["BUILD_ROOT"] == "/x"


@pytest.mark.parametrize(
    "argv",
    [
        ["release", "status"],
        ["linux", "lint"],
        ["container", "image", "linux"],
    ],
)
def test_a_command_offers_only_the_options_it_reads(argv, no_knobs):
    """`release status` never reads $BUILD_ROOT, and the Linux commands
    that start no libera install no components."""
    for option in ("--build-root", "--wheels", "--payload"):
        with pytest.raises(SystemExit):
            cli.plan([*argv, option, "/x"])


def test_the_container_builds_what_payload_all_builds():
    """One sequence, run here by `payload build` and in the container by
    `container run payload`: the two were written out twice."""
    _toolchain, *steps = cli.plan(["payload", "build"])
    assert buildbox.ALL.splitlines() == [
        "set -e",
        *(shlex.join(step.argv[1:]) for step in steps),
    ]


def test_the_payload_container_is_the_whole_build_or_one_script(no_knobs):
    (call,) = cli.plan([
        "container", "run", "payload", "--arch", "arm64", "--memory", "12g"
    ])  # fmt: skip
    assert call.fn.__name__ == "all"
    assert call.fn.__self__.options == BoxOptions(arch="arm64", memory="12g")
    (call,) = cli.plan(["container", "run", "payload", "dist.sh", "--fonts", "core"])
    assert call.fn.__name__ == "script"
    assert call.args == ("dist.sh", ["--fonts", "core"])


def test_each_container_answers_the_same_four_verbs(no_knobs):
    (call,) = cli.plan(["container", "shell", "payload", "--arch", "arm64"])
    assert call.args == ("exec /bin/bash",)
    assert call.fn.__self__.options.arch == "arm64"
    (call,) = cli.plan(["container", "versions", "flatpak"])
    assert call == cli.Call(flatpak.run, (FlatpakOptions("versions", host_arch()),))
    (call,) = cli.plan(["container", "image", "linux"])
    assert call.args[0] == linux.LinuxOptions("image", arch=host_arch())
    with pytest.raises(SystemExit):
        cli.plan(["container", "clean", "linux"])


def test_dropping_the_flatpak_volume_asks_unless_yes(no_knobs):
    asked, call = cli.plan(["container", "clean", "flatpak"])
    assert asked.fn is cli.ask
    assert call.args[0] == FlatpakOptions("clean", host_arch())
    (call,) = cli.plan(["container", "clean", "flatpak", "--yes"])
    assert call.args[0].action == "clean"


def test_the_flatpak_defaults_to_this_machines_architecture(no_knobs):
    (call,) = cli.plan(["app", "test", "flatpak"])
    assert call == cli.Call(flatpak.run, (FlatpakOptions("smoke", arch=host_arch()),))
    (call,) = cli.plan(["app", "build", "flatpak", "--arch", "amd64"])
    assert call.args[0] == FlatpakOptions("build", arch="amd64")
    (call,) = cli.plan(["app", "build", "flatpak", "--arch", "amd64", "--wheels", "/w"])
    assert call.args[0] == FlatpakOptions("build", arch="amd64", wheels=Path("/w"))


def test_tidy_asks_unless_yes_and_lists_on_a_dry_run(no_knobs):
    (call,) = cli.plan(["tidy", "--yes", "--build-root", "/b"])
    assert call == cli.Call(
        tidy.tidy,
        (cli.REPO, Path("/b")),
        {"yes": True, "dry_run": False},
        env={"YES": "1", "BUILD_ROOT": "/b"},
    )
    (call,) = cli.plan(["tidy"])
    assert call.kwargs == {"yes": False, "dry_run": False}
    (call,) = cli.plan(["tidy", "--dry-run"])
    assert call.kwargs == {"yes": False, "dry_run": True}


def test_yes_still_works_as_an_environment_variable(no_knobs, monkeypatch):
    monkeypatch.setenv("YES", "1")
    (call,) = cli.plan(["tidy"])
    assert call.kwargs == {"yes": True, "dry_run": False}


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


def test_linux_gui_takes_a_language(monkeypatch):
    monkeypatch.delenv("LINUX_LANG", raising=False)
    (call,) = cli.plan(["linux", "screenshot", "--lang", "fr_FR.UTF-8"])
    assert call.args[0].lang == "fr_FR.UTF-8"
