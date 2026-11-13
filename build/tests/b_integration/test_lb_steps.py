"""`lb`'s steps, run for real: processes, their order, their environment.

The unit tests check which steps a command line plans; these check that
running them does what the plan says, with real processes and no mocks.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from libera_build import cli, process
from libera_build.cli import Step
from libera_build.containers import host_arch
from libera_build.report import RefusedError

SRC = cli.REPO / "src"
BUILD_SRC = cli.REPO / "build" / "src"


def py(code: str, **env: str) -> Step:
    return Step((sys.executable, "-c", code), env)


def test_steps_run_in_order_from_the_repository_root(tmp_path, capsys):
    log = tmp_path / "log"
    write = "import os, sys; open(sys.argv[1], 'a').write(os.getcwd() + ' ' + sys.argv[2] + '\\n')"
    steps = [
        Step((sys.executable, "-c", write, str(log), "one")),
        Step((sys.executable, "-c", write, str(log), "two")),
    ]
    assert cli.run_steps(steps) == 0
    assert log.read_text().splitlines() == [f"{cli.REPO} one", f"{cli.REPO} two"]
    # Each step is said before it runs, so a long one is never a mystery.
    out = capsys.readouterr().out
    assert out.index("one") < out.index("two")
    assert out.startswith("+ ")


def test_the_first_failure_stops_the_rest_and_is_the_status(tmp_path):
    ran = tmp_path / "ran"
    steps = [
        py("raise SystemExit(3)"),
        py(f"open({str(ran)!r}, 'w')"),
    ]
    assert cli.run_steps(steps) == 3
    assert not ran.exists()


def test_a_step_gets_its_environment_on_top_of_ours(tmp_path):
    out = tmp_path / "env"
    code = f"import os; open({str(out)!r}, 'w').write(os.environ['ARCH'] + ' ' + os.environ['PATH'][:1])"
    assert cli.run_steps([py(code, ARCH="arm64")]) == 0
    arch, path = out.read_text().split()
    assert arch == "arm64"
    assert path, "PATH was not inherited"


def run_as_a_builder(*args: str) -> subprocess.CompletedProcess:
    """`python3 -m libera_build` the way `lb release check` runs it on a builder: no
    site-packages (-S), so nothing installed is visible, and the two source
    trees on PYTHONPATH."""
    return subprocess.run(
        [sys.executable, "-S", "-m", "libera_build", *args],
        cwd=cli.REPO,
        env={**os.environ, "PYTHONPATH": f"{BUILD_SRC}{os.pathsep}{SRC}"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_builder_runs_it_with_nothing_installed():
    done = run_as_a_builder("--help")
    assert done.returncode == 0, done.stderr
    assert "payload container" in done.stdout


# What a builder lacks, or should never pay to load: the CLI and the host pull
# in the GUI, and pywebview is not installed there at all.
NEVER_ON_A_BUILDER = ("libera.cli", "libera.host", "libera.gui", "webview")


def test_a_builder_never_imports_the_application():
    """Importing what lb needs of libera must stay cheap: libera.manifest, and
    libera.payload for where payloads live, both the standard library only.
    Never the CLI, the host or pywebview. -S hides site-packages, so an import
    of pywebview would fail outright."""
    done = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import sys, libera_build.cli; print(sorted(sys.modules))",
        ],
        env={**os.environ, "PYTHONPATH": f"{BUILD_SRC}{os.pathsep}{SRC}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    loaded = done.stdout
    assert [m for m in NEVER_ON_A_BUILDER if f"'{m}" in loaded] == []
    assert "'libera.manifest'" in loaded, "the check itself would see an import"


def test_build_root_reaches_the_code_and_goes_no_further(tmp_path, capsys, monkeypatch):
    """`container export payload` done in this process, with --build-root: it looks
    under that root, and the variable is ours again afterwards."""
    for name in ("ARCH", "BUILD_DIR", "VOLUME"):
        monkeypatch.delenv(name, raising=False)
    before = os.environ.get("BUILD_ROOT")
    assert (
        cli.run_steps(
            cli.plan(["container", "export", "payload", "--build-root", str(tmp_path)])
        )
        == 1
    )
    built_for = tmp_path / f"linux-{host_arch()}"
    assert f"no manifest.json in {built_for}" in capsys.readouterr().err
    assert os.environ.get("BUILD_ROOT") == before


def test_a_quiet_command_that_fails_is_refused_with_what_it_said():
    """Not a CalledProcessError, whose traceback carries the command line and
    drops the tool's own message."""
    with pytest.raises(
        RefusedError, match=r"the sample: .* failed \(3\)\nno blank here"
    ):
        process.run_quietly(
            [sys.executable, "-c", "import sys; print('no blank here'); sys.exit(3)"],
            "the sample",
        )
    process.run_quietly([sys.executable, "-c", "print('fine')"], "the sample")
