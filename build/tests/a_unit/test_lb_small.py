"""The small pure parts: artifact names, the host protocol's helpers, versions,
the benchmark's trace."""

from __future__ import annotations

import pytest
from libera_build import artifacts, bench, versions
from libera_build.hosts import facts_from, remote_path
from libera_build.release import on
from libera_build.report import RefusedError


def test_artifacts_are_named_for_the_right_version():
    assert artifacts.core_name("linux-arm64") == "core-linux-arm64.tar.gz"
    assert artifacts.bundle_name("0.3.3", "amd64") == "libera-0.3.3-amd64.flatpak"


def test_an_artifact_under_its_floor_is_not_one():
    floor = artifacts.MIN_CORE_BYTES
    assert artifacts.size_problem("p", "c.tar.gz", floor - 1, floor)
    assert artifacts.size_problem("p", "c.tar.gz", floor, floor) is None


def test_facts_are_the_key_value_lines_only():
    out = "noise\nARCH=x86_64\nPATH=a=b\nmore noise"
    assert facts_from(out) == {"ARCH": "x86_64", "PATH": "a=b"}


def test_a_remote_path_keeps_its_tilde_expandable():
    assert remote_path("~/muchado") == '"$HOME/muchado"'
    assert remote_path("/a b") == "'/a b'"


def test_the_payload_version_is_read_from_its_line(tmp_path):
    (tmp_path / "src" / "libera" / "payload").mkdir(parents=True)
    (tmp_path / "src" / "libera" / "payload" / "payload.version").write_text(
        '# a comment = no\nversion = "0.4"\n'
    )
    assert versions.payload_version(tmp_path) == "0.4"
    (tmp_path / "src" / "libera" / "payload" / "payload.version").write_text(
        "# nothing\n"
    )
    with pytest.raises(RefusedError):
        versions.payload_version(tmp_path)


def test_the_application_version_is_pyprojects(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    assert versions.app_version(tmp_path) == "1.2.3"


def test_on_reads_the_status_from_the_verdict():
    assert on.status_of("linux-arm64", "0") == 0
    assert on.status_of("linux-arm64", "3") == 3


@pytest.mark.parametrize(
    ("verdict", "says"),
    [
        ("no checkout at ~/x", "linux-arm64: no checkout at ~/x"),
        ("", "linux-arm64: the command stopped without saying how"),
    ],
)
def test_a_verdict_that_is_not_a_status_is_said(verdict, says):
    with pytest.raises(RefusedError) as e:
        on.status_of("linux-arm64", verdict)
    assert str(e.value) == says


def test_a_pointer_names_digits_and_dots_and_nothing_else_is_a_release():
    assert not versions.is_prerelease("0.4.0")
    assert not versions.is_prerelease("1.10")
    for pre in ("0.4.0rc1", "0.4.0a2", "0.4.0.post1", "0.4.0+local", "0.4.0.dev3"):
        assert versions.is_prerelease(pre), pre


def test_the_document_is_on_screen_when_the_window_last_changed(tmp_path):
    """The window changes many times, and the editor says it is ready twice,
    before the last of them. `settled` is the last change; `editor-ready` the
    first time it was said."""
    trace = tmp_path / "startup.trace"
    trace.write_text(
        "100.5 python\n101.0 screen\n102.0 editor-ready\n102.4 screen\n"
        "102.7 editor-ready\n103.1 screen\n",
        encoding="utf-8",
    )
    reached = bench.read_trace(trace, started=100.0)
    assert reached == pytest.approx({
        "python": 0.5,
        "editor-ready": 2.0,
        "settled": 3.1,
    })


def test_a_run_waits_for_the_window_to_be_still_after_the_editor_is_ready():
    ready = {"editor-ready": 4.0, "settled": 5.0}
    assert not bench.is_done({"first-request": 2.0}, 60.0, watching=True)
    assert not bench.is_done(ready, 5.0 + bench.QUIET - 0.1, watching=True)
    assert bench.is_done(ready, 5.0 + bench.QUIET + 0.1, watching=True)
    assert bench.is_done(ready, 4.1, watching=False)


def test_a_document_opened_in_the_running_application_is_timed_on_its_own(
    tmp_path,
):
    """The host writes its stages again for a later document, into the trace
    the launch filled; the first window's watcher goes on writing there too.
    Only what came after the second document was asked for counts, and its
    window's changes are its own watcher's."""
    trace, screen = tmp_path / "startup.trace", tmp_path / "again.trace"
    trace.write_text(
        "100.5 python\n101.0 converted\n102.0 editor-ready\n103.0 screen\n"
        "110.3 python\n110.9 window\n111.2 converted\n112.6 screen\n"
        "113.0 editor-ready\n",
        encoding="utf-8",
    )
    screen.write_text("111.0 screen\n113.5 screen\n", encoding="utf-8")
    reached = bench.read_again(trace, screen, asked=110.0)
    assert reached == pytest.approx({
        "python": 0.3,
        "window": 0.9,
        "converted": 1.2,
        "editor-ready": 3.0,
        "settled": 3.5,
    })


def test_a_poll_ignores_what_ssh_says_before_it():
    from libera_build import detached

    out = (
        "** WARNING: connection is not using a post-quantum key exchange\n"
        f"{detached.POLL_BEGIN}\n  indented line\nlast\n"
        f"{detached.POLL_MARK} SIZE=42 DONE= ALIVE=1"
    )
    poll = detached.parse_poll(out)
    assert poll is not None
    assert poll.text == "  indented line\nlast"
    assert (poll.size, poll.done, poll.alive) == (42, "", True)


def test_a_poll_that_is_no_answer_is_none():
    from libera_build import detached

    assert detached.parse_poll("ssh: connect to host x: Host is down") is None
    assert detached.parse_poll(f"{detached.POLL_MARK} SIZE=") is None
    assert detached.parse_poll(f"{detached.POLL_MARK} GONE=1").gone


def test_a_run_folder_is_one_safe_segment():
    from libera_build import detached

    assert detached.run_folder("windows-x86_64 payload all") == (
        '"$HOME/.lb/runs/windows-x86_64-payload-all"'
    )
    # One segment, however the command is spelled: no slash survives.
    assert detached.run_folder("../../x; rm -rf") == '"$HOME/.lb/runs/..-..-x-rm--rf"'
