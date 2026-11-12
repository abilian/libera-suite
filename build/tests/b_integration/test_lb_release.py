"""A release's phases against real builders: LocalHost, real bash, real git.

The driving checkout is a scratch repository, not this one, so that it can be
committed to. Its build/src/libera_build is a stand-in that does what its
arguments say: `ok` succeeds, `fail` exits 3, `vanish` exits before the verdict
line. The builders are LocalHosts whose `~` is a scratch directory, so update
really pushes and checks out, and a build really runs `python3 -m
libera_build` there, as on a builder.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from libera_build import detached, repo
from libera_build.artifacts import (
    MIN_BUNDLE_BYTES,
    MIN_CORE_BYTES,
    run_bundles,
    run_pypi,
)
from libera_build.containers import host_arch, linux_platform
from libera_build.hosts import LocalHost
from libera_build.inventory import Builder
from libera_build.release import builds, precheck
from libera_build.release.context import Context
from libera_build.release.on import OnOptions, on
from libera_build.release.phases import (
    builders,
    components,
    staging,
    update,
)
from libera_build.release.ship import ShipOptions, ship
from libera_build.report import RefusedError
from libera_build.sources import source_problems

STAND_IN = """
import sys
args = sys.argv[1:]
print("stand-in lb", *args)
if "fail" in args:
    raise SystemExit(3)
if "vanish" in args:
    import os
    os.kill(os.getppid(), 9)
if "slow" in args:
    import time
    time.sleep(1.5)
    print("stand-in lb slept")
if "cp1252" in args:
    sys.stdout.flush()
    sys.stdout.buffer.write(b"a\\x85b\\n")
"""

GIT = [
    "git",
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@t",
    "-c",
    "init.defaultBranch=main",
]


def git(where: Path, *args: str) -> str:
    done = subprocess.run(
        [*GIT, "-C", str(where), *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


@pytest.fixture
def driver(tmp_path) -> Path:
    """A checkout to drive a release from, committed."""
    root = tmp_path / "driver"
    (root / "build" / "src" / "libera_build").mkdir(parents=True)
    (root / "build" / "src" / "libera_build" / "__init__.py").write_text("")
    (root / "build" / "src" / "libera_build" / "__main__.py").write_text(STAND_IN)
    (root / "src" / "libera" / "payload").mkdir(parents=True)
    (root / "src" / "libera" / "payload" / "payload.version").write_text(
        'version = "9.9"\n'
    )
    (root / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    (root / ".gitignore").write_text("tmp/\nbuild/builders.toml\n__pycache__/\n")
    subprocess.run([*GIT, "init", "-q", str(root)], check=True)
    # -f: a global gitignore often ignores build/, and then the stand-in
    # never reaches the builder, which runs whatever libera_build it finds.
    git(root, "add", "-f", ".")
    git(root, "commit", "-qm", "driver")
    return root


@pytest.fixture
def home(tmp_path) -> Path:
    """A builder's `~`."""
    found = tmp_path / "builder-home"
    found.mkdir()
    return found


# Named for this machine's own architecture, which precheck asks the builder
# for: a linux-arm64 stand-in failed it on every x86_64 machine.
ARM = Builder(linux_platform(host_arch()), "arm", "~/checkout")


def context(driver: Path, home: Path, phases: list[str]) -> Context:
    # A builder's job is polled every 15 s; here it ends at once.
    return Context(
        root=driver,
        builders=[ARM],
        phases=phases,
        host_for=lambda _: LocalHost(home),
        poll_seconds=0.05,
    )


def test_update_makes_the_checkout_and_puts_this_commit_in_it(driver, home):
    update.run(context(driver, home, ["update"]))
    checkout = home / "checkout"
    assert git(checkout, "rev-parse", "HEAD") == repo.head(driver)
    assert not git(checkout, "status", "--porcelain")
    # Detached: the builder's own branches are left alone.
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"


def test_update_moves_a_builder_that_is_at_another_commit(driver, home):
    update.run(context(driver, home, ["update"]))
    (driver / "new.txt").write_text("x")
    git(driver, "add", ".")
    git(driver, "commit", "-qm", "second")
    update.run(context(driver, home, ["update"]))
    assert git(home / "checkout", "rev-parse", "HEAD") == repo.head(driver)


def test_a_dirty_builder_is_refused_before_anything_starts(driver, home):
    update.run(context(driver, home, ["update"]))
    (home / "checkout" / "stray.txt").write_text("somebody's edit")
    ctx = context(driver, home, ["update"])
    (problem,) = precheck.check_builder(ctx, ARM)
    assert "1 uncommitted file(s)" in problem


def test_a_builder_with_no_checkout_is_fine_only_if_update_will_make_one(driver, home):
    assert (
        precheck.check_builder(context(driver, home, ["update", "components"]), ARM)
        == []
    )
    (problem,) = precheck.check_builder(context(driver, home, ["components"]), ARM)
    assert "no checkout at ~/checkout" in problem


@pytest.mark.skipif(
    sys.platform == "win32", reason="Git Bash spells this machine's paths its own way"
)
def test_a_missing_checkout_names_the_checkouts_that_are_there(driver, home):
    other = home / "elsewhere" / "src" / "libera" / "payload"
    other.mkdir(parents=True)
    (other / "payload.version").write_text('version = "9.9"\n')
    (problem,) = precheck.check_builder(context(driver, home, ["components"]), ARM)
    assert "checkouts on that machine" in problem
    assert f"{home}/elsewhere/" in problem


def believe(_builder, _host) -> None:
    return None


def ran(driver: Path, home: Path, command: str, verify=believe) -> str | None:
    ctx = context(driver, home, ["update", "components"])
    update.run(ctx)
    return builds.build_one(ctx, ARM, command, verify)


def test_a_build_that_says_ok_is_then_checked_for_its_artifact(driver, home):
    asked = []

    def verify(b, host):
        asked.append(b.platform)

    assert ran(driver, home, "ok --arch arm64", verify) is None
    assert asked == [ARM.platform]
    log = (driver / "tmp" / "remote" / f"{ARM.platform}.log").read_text(
        encoding="utf-8"
    )
    assert "stand-in lb ok --arch arm64" in log


def test_a_build_that_fails_says_how_and_skips_the_check(driver, home):
    def never(_builder, _host):
        pytest.fail("a failed build was checked for its artifact")

    problem = ran(driver, home, "fail", verify=never)
    assert "lb fail failed (3)" in problem


def test_a_byte_that_is_not_utf8_is_logged_and_does_not_end_the_run(driver, home):
    """Python on Windows writes a pipe in cp1252, and its `…` ended a ship."""
    assert ran(driver, home, "cp1252") is None
    log = (driver / "tmp" / "remote" / f"{ARM.platform}.log").read_text(
        encoding="utf-8"
    )
    assert "a\N{REPLACEMENT CHARACTER}b" in log


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="killing the parent on Windows does not reach the wrapper that reports",
)
def test_a_build_that_never_says_how_is_not_believed(driver, home):
    problem = ran(driver, home, "vanish")
    assert "without saying how" in problem


def core_of_at_least(minimum: int):
    def verify(b, host):
        return builds.check_remote_file(b, host, "~/out/core.tar.gz", minimum)

    return verify


def test_an_artifact_that_is_not_there_fails_the_build(driver, home):
    assert "is not there" in ran(driver, home, "ok", core_of_at_least(1))


def test_an_artifact_that_is_there_passes_the_build(driver, home):
    (home / "out").mkdir()
    (home / "out" / "core.tar.gz").write_bytes(b"x" * 10)
    assert ran(driver, home, "ok", core_of_at_least(1)) is None


def test_an_artifact_under_its_floor_fails_the_build(driver, home):
    (home / "out").mkdir()
    (home / "out" / "core.tar.gz").write_bytes(b"x" * 10)
    assert "is 10 bytes" in ran(driver, home, "ok", core_of_at_least(100))


def test_bundles_makes_the_installer_on_windows_and_brings_it_here(driver, home):
    """The whole phase against a Windows builder: `lb app build windows` run there,
    the installer looked for there, then it and its SHA-256 fetched here."""
    win = Builder("windows-x86_64", "win", "~/checkout")
    ctx = replace(context(driver, home, ["update", "bundles"]), builders=[win])
    update.run(ctx)
    made = home / "checkout" / "build" / "out" / "bundles"
    made.mkdir(parents=True)
    setup = made / "Libera-Suite-Setup-9.9.9.exe"
    with setup.open("wb") as f:
        f.truncate(MIN_BUNDLE_BYTES)
    (made / f"{setup.name}.sha256").write_text(f"0  {setup.name}\n")
    builders.bundles(ctx)
    log = (driver / "tmp" / "remote" / "windows-x86_64.log").read_text()
    assert "stand-in lb app build windows" in log
    here = run_bundles(driver)
    assert (here / setup.name).stat().st_size == MIN_BUNDLE_BYTES
    assert (here / f"{setup.name}.sha256").read_text() == f"0  {setup.name}\n"


def test_bundles_fails_when_the_installer_was_not_made(driver, home):
    win = Builder("windows-x86_64", "win", "~/checkout")
    ctx = replace(context(driver, home, ["update", "bundles"]), builders=[win])
    update.run(ctx)
    with pytest.raises(RefusedError, match="1 of 1 builder"):
        builders.bundles(ctx)


def builders_toml(driver: Path) -> None:
    (driver / "build" / "builders.toml").write_text(
        '[[builders]]\nplatform = "linux-arm64"\ntarget = "arm"\nrepo = "~/checkout"\n'
    )


def test_ship_refuses_publishing_from_a_tree_it_cannot_vouch_for(
    driver, home, capsys, monkeypatch
):
    builders_toml(driver)
    (driver / "dirty.txt").write_text("uncommitted")
    options = ShipOptions(
        phases=("publish",), root=driver, host_for=lambda _: LocalHost(home)
    )
    monkeypatch.delenv("ALLOW_DIRTY", raising=False)
    with pytest.raises(RefusedError, match="nothing was started"):
        ship(options)
    assert "would stamp a commit" in capsys.readouterr().out


def test_ship_dry_names_the_builders_and_runs_nothing(driver, home, capsys):
    builders_toml(driver)
    options = ShipOptions(root=driver, dry_run=True, host_for=lambda _: LocalHost(home))
    assert ship(options) == 0
    out = capsys.readouterr().out
    assert "linux-arm64    arm:~/checkout" in out
    assert "publish cannot be undone" in out
    assert not (home / "checkout").exists()


def test_on_runs_a_command_there_and_returns_its_status(driver, home, capsys):
    builders_toml(driver)
    options = OnOptions(
        "linux-arm64", ("ok", "x"), update=True, host_for=lambda _: LocalHost(home)
    )
    assert on(replace(options, root=driver)) == 0
    assert "stand-in lb ok x" in capsys.readouterr().out
    failing = replace(options, root=driver, command=("fail",), update=False)
    assert on(failing) == 3


def test_on_says_when_the_builder_is_at_another_commit(driver, home, capsys):
    builders_toml(driver)
    options = OnOptions(
        "linux-arm64",
        ("ok",),
        update=True,
        root=driver,
        host_for=lambda _: LocalHost(home),
    )
    on(options)
    (driver / "new.txt").write_text("x")
    git(driver, "add", "-f", ".")
    git(driver, "commit", "-qm", "second")
    capsys.readouterr()
    on(replace(options, update=False))
    assert "--update sends this commit first" in capsys.readouterr().out


def test_on_says_why_a_command_never_ran(driver, home):
    """A verdict that is not a status is the reason, and it used to be read
    and dropped: `lb on` exited 1 and said nothing at all."""
    builders_toml(driver)
    options = OnOptions(
        "linux-arm64", ("ok",), root=driver, host_for=lambda _: LocalHost(home)
    )
    with pytest.raises(RefusedError, match="linux-arm64: no checkout at ~/checkout"):
        on(options)


# --- sources: is a tree its pin plus the queue ------------------------------


def sources(tmp_path: Path, patches: int) -> tuple[Path, Path, list[str]]:
    """A checkout whose queue holds `patches` patches against one pinned repo,
    and a $BUILD_ROOT/src with that repo cloned at the pin, nothing applied.
    The queue is made the way it is maintained, with format-patch."""
    upstream = tmp_path / "upstream"
    subprocess.run([*GIT, "init", "-q", str(upstream)], check=True)
    (upstream / "a.txt").write_text("pinned\n")
    git(upstream, "add", ".")
    git(upstream, "commit", "-qm", "pinned")
    pin = git(upstream, "rev-parse", "HEAD")
    root = tmp_path / "checkout"
    queue = root / "build" / "upstream" / "patches" / "core"
    queue.mkdir(parents=True)
    (root / "build" / "upstream" / "pins.toml").write_text(f'[repos]\ncore = "{pin}"\n')
    for n in range(patches):
        (upstream / f"p{n}.txt").write_text(f"patch {n}\n")
        git(upstream, "add", ".")
        git(upstream, "commit", "-qm", f"patch {n}")
    git(upstream, "format-patch", "-q", "-o", str(queue), f"{pin}..HEAD")
    src = tmp_path / "src"
    subprocess.run([*GIT, "clone", "-q", str(upstream), str(src / "core")], check=True)
    git(src / "core", "checkout", "-q", "--detach", pin)
    return root, src, sorted(str(p) for p in queue.iterdir())


def test_a_tree_at_its_pin_plus_the_queue_passes(tmp_path):
    root, src, queue = sources(tmp_path, 2)
    git(src / "core", "am", "-q", *queue)
    assert source_problems(root, src) == []


def test_a_tree_fetched_before_a_patch_was_added_is_refused(tmp_path):
    root, src, queue = sources(tmp_path, 2)
    git(src / "core", "am", "-q", queue[0])
    (problem,) = source_problems(root, src)
    assert "carries 1 commit(s) on its pin" in problem
    assert "the 2 patch(es) in the queue" in problem


def test_a_patch_that_changed_since_it_was_applied_is_refused(tmp_path):
    root, src, queue = sources(tmp_path, 1)
    git(src / "core", "am", "-q", *queue)
    edited = Path(queue[0])
    text = edited.read_text(encoding="utf-8")
    edited.write_text(text.replace("+patch 0", "+patch zero"), encoding="utf-8")
    (problem,) = source_problems(root, src)
    assert "not the 1 patch(es)" in problem


def test_a_tree_off_its_pin_or_missing_is_refused(tmp_path):
    root, src, _ = sources(tmp_path, 0)
    git(src / "core", "checkout", "-q", "--orphan", "elsewhere")
    git(src / "core", "commit", "-qm", "elsewhere")
    (problem,) = source_problems(root, src)
    assert "is not on its pin" in problem
    (problem,) = source_problems(root, tmp_path / "nowhere")
    assert "no source tree" in problem


class Flaky:
    """A builder whose polls go unanswered `misses` times, as builder-windows'
    did when it dropped off the network, while the job itself goes on."""

    def __init__(self, home: Path, misses: int) -> None:
        self.real = LocalHost(home)
        self.misses = misses

    def __getattr__(self, name):
        return getattr(self.real, name)

    def capture(self, script: str) -> str:
        if detached.POLL_MARK in script and self.misses > 0:
            self.misses -= 1
            return "ssh: connect to host builder port 22: Operation timed out"
        return self.real.capture(script)


def test_a_build_outlives_polls_that_go_unanswered(driver, home):
    """A dropped connection ended the phase that streamed a build, while the
    build went on there; now it is a poll that missed."""
    host = Flaky(home, misses=5)
    ctx = replace(
        context(driver, home, ["update", "components"]), host_for=lambda _: host
    )
    update.run(ctx)

    assert builds.build_one(ctx, ARM, "slow", believe) is None

    assert host.misses == 0
    log = (driver / "tmp" / "remote" / f"{ARM.platform}.log").read_text()
    assert "stand-in lb slept" in log


def test_a_build_still_running_is_watched_not_started_again(driver, home):
    """The driver died, or gave up on an unreachable builder: the same phase,
    run again, watches the job there rather than starting a second build on
    the same tree."""
    ctx = context(driver, home, ["update", "components"])
    update.run(ctx)
    name = f"{ARM.platform} slow"
    script = f"cd ~/checkout && {builds.LB} slow && echo {builds.MARK}=ok"
    first = LocalHost(home).capture(detached.start_script(name, script))
    assert "STARTED=1" in first

    assert builds.build_one(ctx, ARM, "slow", believe) is None

    log = (driver / "tmp" / "remote" / f"{ARM.platform}.log").read_text()
    assert log.count("stand-in lb slept") == 1


def test_a_builder_silent_too_long_ends_the_watch_saying_so(driver, home):
    host = Flaky(home, misses=10**6)
    ctx = replace(
        context(driver, home, ["update", "components"]),
        host_for=lambda _: host,
        unreachable_seconds=0.3,
    )
    update.run(ctx)

    problem = builds.build_one(ctx, ARM, "slow", believe)

    assert "may still be running there" in problem


class Silent:
    """A builder that does not answer its first `misses` questions."""

    def __init__(self, home: Path, misses: int) -> None:
        self.real = LocalHost(home)
        self.misses = misses

    def __getattr__(self, name):
        return getattr(self.real, name)

    def capture(self, script: str) -> str:
        if self.misses > 0:
            self.misses -= 1
            return "ssh: connect to host builder port 22: No route to host"
        return self.real.capture(script)


def test_a_builder_that_answers_on_its_third_try_is_checked(driver, home):
    """One unanswered question refused the beta's whole run, twice."""
    host = Silent(home, misses=2)
    ctx = replace(
        context(driver, home, ["update", "components"]), host_for=lambda _: host
    )

    assert precheck.check_builder(ctx, ARM) == []


def test_a_builder_that_never_answers_is_refused_after_its_tries(driver, home):
    host = Silent(home, misses=10**6)
    ctx = replace(
        context(driver, home, ["update", "components"]), host_for=lambda _: host
    )

    (problem,) = precheck.check_builder(ctx, ARM)

    assert f"in {precheck.ANSWER_TRIES} tries" in problem


WIN = Builder("windows-x86_64", "win", "~/checkout")


def test_the_components_phase_brings_each_builders_core_wheel_here(driver, home):
    """`lb components build` run there, its wheel looked for there, then
    fetched into this commit's run directory here, where stage gathers from."""
    ctx = replace(context(driver, home, ["update", "components"]), builders=[WIN])
    update.run(ctx)
    made = home / "checkout" / "build" / "out" / "pypi" / "9.9"
    made.mkdir(parents=True)
    wheel = made / "libera_core-9.9-py3-none-win_amd64.whl"
    with wheel.open("wb") as f:
        f.truncate(MIN_CORE_BYTES)

    components.run(ctx)

    log = (driver / "tmp" / "remote" / "windows-x86_64.log").read_text()
    assert "stand-in lb components build --out build/out/pypi/9.9" in log
    here = run_pypi(driver) / wheel.name
    assert here.stat().st_size == MIN_CORE_BYTES


def test_the_components_phase_fails_when_a_wheel_was_not_made(driver, home):
    ctx = replace(context(driver, home, ["update", "components"]), builders=[WIN])
    update.run(ctx)

    with pytest.raises(RefusedError, match="1 of 1 builder"):
        components.run(ctx)


def test_stage_refuses_before_copying_when_the_components_are_missing(
    driver, home, capsys
):
    """Before anything is copied, and so long before anything goes up."""
    ctx = replace(context(driver, home, ["stage"]), builders=[WIN], yes=False)
    run_pypi(driver).mkdir(parents=True)
    (run_pypi(driver) / "libera-9.9.9-py3-none-any.whl").write_bytes(b"")

    with pytest.raises(RefusedError, match="nothing was staged"):
        staging.run(ctx)
    assert not staging.folder(driver).exists()

    said = capsys.readouterr().out
    assert "libera_core-9.9-py3-none-win_amd64.whl is not here" in said
    assert "asks for nothing" in said
