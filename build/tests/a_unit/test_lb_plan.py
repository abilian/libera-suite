"""The rules of a release, each on its own: order, narrowing, refusals."""

from __future__ import annotations

from dataclasses import replace

import pytest
from libera_build.inventory import Builder
from libera_build.release import plan
from libera_build.release.phases import builders
from libera_build.report import RefusedError

from libera.manifest import Manifest

ARM = Builder("linux-arm64", "arm", None, False, "~/r")


def test_phases_run_in_their_order_whatever_order_they_are_asked_in():
    assert plan.choose_phases(["push", "collect"], narrowed=False) == [
        "collect",
        "push",
    ]


def test_no_phase_means_all_of_them_or_those_that_narrow():
    assert plan.choose_phases([], narrowed=False) == list(plan.PHASES)
    assert plan.choose_phases([], narrowed=True) == list(plan.PER_BUILDER)


def test_only_refuses_the_phases_that_span_every_builder():
    with pytest.raises(RefusedError) as e:
        plan.choose_phases(["build", "collect"], narrowed=True)
    assert "not collect" in str(e.value)


def test_an_unknown_phase_is_refused():
    with pytest.raises(RefusedError):
        plan.choose_phases(["biuld"], narrowed=False)


def test_uploading_wants_a_token():
    assert plan.token_problems(["push"], have_token=False)
    assert not plan.token_problems(["push"], have_token=True)
    assert not plan.token_problems(["build"], have_token=False)


def test_a_dirty_tree_stops_only_what_stamps_the_manifest():
    assert not plan.dirty_problems(["build"], dirty=3, allow_dirty=False)
    assert plan.dirty_problems(["collect"], dirty=3, allow_dirty=False)
    assert not plan.dirty_problems(["collect"], dirty=3, allow_dirty=True)
    assert not plan.dirty_problems(["collect"], dirty=0, allow_dirty=False)


def test_uploading_wants_the_commit_somewhere_else_too():
    (problem,) = plan.unpushed_problems(["push"], on_a_remote=False, head="a" * 40)
    assert "aaaaaaaaa" in problem
    assert "push it first" in problem
    assert not plan.unpushed_problems(["push"], on_a_remote=True, head="a" * 40)
    assert not plan.unpushed_problems(["build"], on_a_remote=False, head="a" * 40)


MANIFEST = Manifest("0.4", (), source={"libera_commit": "h" * 40})


@pytest.mark.parametrize(
    ("phases", "manifest", "says"),
    [
        (["publish"], MANIFEST, "publish without check"),
        (["check", "publish"], None, "needs src/libera/manifest.json"),
        (
            ["check", "publish"],
            replace(MANIFEST, payload_version="0.3"),
            "for payload 0.3",
        ),
        (
            ["check", "publish"],
            replace(MANIFEST, source={"libera_commit": "o" * 40}),
            "collected at ooooooooo",
        ),
    ],
)
def test_publish_refuses_a_manifest_that_is_not_this_release(phases, manifest, says):
    found = plan.publish_problems(
        phases, manifest=manifest, payload_version="0.4", head="h" * 40
    )
    assert any(says in p for p in found), found


def test_publish_accepts_this_release_and_a_collect_in_the_same_run():
    assert not plan.publish_problems(
        ["check", "publish"], manifest=MANIFEST, payload_version="0.4", head="h" * 40
    )
    assert not plan.publish_problems(
        ["collect", "check", "publish"], manifest=None, payload_version="0.4", head="h"
    )


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


WINDOWS = Builder("windows-x86_64", "win", "C:/b/out/dist", False, "~/r")
MAC = Builder("macos-x86_64", "mac", None, False, "~/r")


def test_each_platform_builds_its_core_its_own_way():
    assert builders.build_command(ARM) == "payload container --arch arm64"
    assert builders.build_command(WINDOWS) == "payload all"
    assert builders.build_command(MAC) == "payload all"


def test_each_platform_bundles_what_its_users_download():
    flatpak = builders.bundle_of(ARM, "0.4.0", "~/d/0.4")
    assert flatpak == builders.Bundle(
        "app flatpak --dist ~/d/0.4 --arch arm64",
        ("build/out/libera-0.4.0-arm64.flatpak",),
    )
    installer = builders.bundle_of(WINDOWS, "0.4.0", "C:/b/out/dist/0.4")
    setup = "build/out/bundles/Libera-Suite-Setup-0.4.0.exe"
    assert installer == builders.Bundle("app windows", (setup, f"{setup}.sha256"))
    assert builders.bundle_of(MAC, "0.4.0", "~/d/0.4") is None
