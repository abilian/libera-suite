"""The rules of a release, each on its own: order, narrowing, refusals."""

from __future__ import annotations

import pytest
from libera_build import cli
from libera_build.inventory import Builder
from libera_build.release import plan, run
from libera_build.release.phases import builders, components
from libera_build.report import RefusedError

ARM = Builder("linux-arm64", "arm", "~/r")


def test_phases_run_in_their_order_whatever_order_they_are_asked_in():
    assert plan.choose_phases("check", ["stage", "wheel"], narrowed=False) == [
        "wheel",
        "stage",
    ]


def test_no_phase_means_all_of_the_verbs_or_those_that_narrow():
    assert plan.choose_phases("check", [], narrowed=False) == list(plan.CHECK)
    assert plan.choose_phases("check", [], narrowed=True) == list(plan.PER_BUILDER)
    assert plan.choose_phases("publish", [], narrowed=False) == list(plan.PUBLISH)


def test_only_refuses_the_phases_that_span_every_builder():
    with pytest.raises(RefusedError) as e:
        plan.choose_phases("check", ["components", "wheel"], narrowed=True)
    assert "not wheel" in str(e.value)


def test_a_check_never_publishes():
    """The one irreversible phase is reached only by its own verb."""
    assert "publish" not in plan.CHECK
    with pytest.raises(RefusedError, match="a phase of `lb release publish`"):
        plan.choose_phases("check", ["publish"], narrowed=False)
    with pytest.raises(RefusedError, match="a phase of `lb release check`"):
        plan.choose_phases("publish", ["stage"], narrowed=False)


def test_an_unknown_phase_is_refused():
    with pytest.raises(RefusedError, match="no such phase"):
        plan.choose_phases("check", ["biuld"], narrowed=False)


def test_uploading_wants_a_token():
    assert plan.token_problems(["publish"], have_token=False)
    assert not plan.token_problems(["publish"], have_token=True)
    assert not plan.token_problems(["bundles"], have_token=False)


def test_publishing_wants_the_signing_key():
    assert plan.signing_problems(["publish"], have_key=False)
    assert not plan.signing_problems(["publish"], have_key=True)
    assert not plan.signing_problems(["wheel"], have_key=False)


def test_a_dirty_tree_stops_only_what_stamps_the_manifest():
    assert not plan.dirty_problems(["bundles"], dirty=3, allow_dirty=False)
    assert plan.dirty_problems(["publish"], dirty=3, allow_dirty=False)
    assert not plan.dirty_problems(["publish"], dirty=3, allow_dirty=True)
    assert not plan.dirty_problems(["publish"], dirty=0, allow_dirty=False)


def test_uploading_wants_the_commit_somewhere_else_too():
    (problem,) = plan.unpushed_problems(["publish"], on_a_remote=False, head="a" * 40)
    assert "aaaaaaaaa" in problem
    assert "push it first" in problem
    assert not plan.unpushed_problems(["publish"], on_a_remote=True, head="a" * 40)
    assert not plan.unpushed_problems(["bundles"], on_a_remote=False, head="a" * 40)


def test_a_builder_of_the_wrong_architecture_or_dirty_is_refused():
    assert not plan.builder_problems(ARM, {"ARCH": "aarch64", "DIRTY": "0"})
    (wrong,) = plan.builder_problems(ARM, {"ARCH": "x86_64", "DIRTY": "0"})
    assert "wants arm64" in wrong
    (dirty,) = plan.builder_problems(ARM, {"ARCH": "aarch64", "DIRTY": "2"})
    assert "2 uncommitted" in dirty


def test_an_update_is_believed_only_at_the_commit_sent():
    good = {"M": "ok", "HEAD": "c" * 40, "DIRTY": "0"}
    assert not plan.update_problems(ARM, good, sent="c" * 40, mark="M")
    assert plan.update_problems(ARM, {**good, "M": ""}, sent="c" * 40, mark="M")
    assert plan.update_problems(ARM, {**good, "DIRTY": "1"}, sent="c" * 40, mark="M")
    assert plan.update_problems(
        ARM, {**good, "HEAD": "d" * 40}, sent="c" * 40, mark="M"
    )


def test_a_build_is_believed_only_when_it_says_ok():
    assert plan.build_problem("p", "ok", "1m00s") is None
    assert "without saying how" in plan.build_problem("p", "", "1m00s")
    assert "lb x failed (2)" in plan.build_problem("p", "lb x failed (2)", "0m01s")


WINDOWS = Builder("windows-x86_64", "win", "~/r")
MAC = Builder("macos-x86_64", "mac", "~/r")


def test_each_platform_bundles_what_its_users_download():
    flatpak = builders.bundle_of(ARM, "0.4.0")
    assert flatpak == builders.Bundle(
        "app build flatpak --arch arm64",
        ("build/out/libera-0.4.0-arm64.flatpak",),
    )
    installer = builders.bundle_of(WINDOWS, "0.4.0")
    setup = "build/out/bundles/Libera-Suite-Setup-0.4.0.exe"
    assert installer == builders.Bundle("app build windows", (setup, f"{setup}.sha256"))
    assert builders.bundle_of(MAC, "0.4.0") is None


def test_every_file_is_made_before_the_stage():
    order = list(plan.PHASES)
    makers = ("components", "bundles", "wheel")
    assert all(order.index(m) < order.index("stage") for m in makers)
    assert "components" in plan.PER_BUILDER


WANTED = [
    "libera_core-0.7-py3-none-macosx_14_0_arm64.whl",
    "libera_core-0.7.tar.gz",
    "libera_web-0.7-py3-none-any.whl",
    "libera-0.7.0b1-py3-none-any.whl",
]
PINS = ["libera-core==0.7", "libera-web==0.7", "pywebview>=5"]


def test_a_release_with_every_file_and_the_right_pins_may_go_up():
    assert (
        plan.upload_problems(
            set(WANTED), wanted=WANTED, payload_version="0.7", requires=PINS
        )
        == []
    )


def test_libera_alone_does_not_go_up():
    """0.7.0b1 went up as libera alone, and nothing could install it."""
    found = plan.upload_problems(
        {WANTED[-1]}, wanted=WANTED, payload_version="0.7", requires=PINS
    )

    assert len(found) == 3
    assert all("is not here" in f for f in found)


def test_a_libera_that_pins_another_payload_does_not_go_up():
    found = plan.upload_problems(
        set(WANTED),
        wanted=WANTED,
        payload_version="0.7",
        requires=["libera-core==0.7.dev1", "libera-web==0.7"],
    )

    (problem,) = found
    assert "libera-core==0.7.dev1" in problem


def test_every_phase_has_an_action_and_every_action_a_phase():
    # Two tables kept in step by hand: one missing a key is a KeyError found
    # after the hours of building, not before.
    assert list(run.ACTIONS) == list(plan.PHASES)


def test_every_lb_command_a_release_runs_is_one_lb_has():
    """The phases name `lb` commands as strings, which the tests' stand-in
    builders run without parsing: `components wheels` outlived its rename by
    weeks, found only by a real run."""
    commands = [f"{components.COMMAND} --out build/out/pypi/9.9"]
    for b in (ARM, WINDOWS):
        bundle = builders.bundle_of(b, "9.9.9")
        assert bundle is not None
        commands.append(bundle.command)
    for command in commands:
        cli.plan(command.split())
