"""The build container, the Flatpak and the window check: their rules."""

from __future__ import annotations

from pathlib import Path

from libera_build import buildbox, flatpak, inventory, released_gui, tidy
from libera_build.buildbox import BoxOptions
from libera_build.containers import linux_platform
from libera_build.inventory import Builder


def test_an_image_on_another_base_is_stale():
    assert buildbox.stale(buildbox.base()) is None
    assert "ubuntu:24.04" in buildbox.stale("ubuntu:24.04@sha256:x")
    assert "too old to say" in buildbox.stale("")


def test_the_compiler_follows_the_architecture():
    assert "CLANG_VERSION=13" in buildbox.build_args("arm64")
    assert "CLANG_VERSION=14" in buildbox.build_args("amd64")


def env_and_mounts(options: BoxOptions) -> tuple[dict, list[str]]:
    run = buildbox.run_spec(options, "img", "true")
    return dict(run.env), [m.target for m in run.mounts]


def test_the_build_container_gets_its_tree_temporaries_and_tar(tmp_path):
    env, mounts = env_and_mounts(
        BoxOptions(build_dir=tmp_path, mirror=tmp_path / "none")
    )
    assert mounts == ["/repo", "/build"]
    assert env["TMPDIR"] == "/build/tmp"
    assert env["TAR_OPTIONS"] == "--no-same-owner"
    assert "V8_BUILD_JOBS" not in env


def test_a_mirror_is_mounted_read_only_only_when_there(tmp_path):
    (tmp_path / "core-fonts").mkdir()
    run = buildbox.run_spec(
        BoxOptions(build_dir=tmp_path, mirror=tmp_path), "img", "true"
    )
    mirror = next(m for m in run.mounts if m.target == "/mirror")
    assert mirror.read_only
    assert run.env["CORE_FONTS"] == "/mirror/core-fonts"


def test_jobs_memory_and_a_volume_reach_the_container(tmp_path):
    options = BoxOptions(
        volume="vol", memory="12g", v8_jobs="4", core_jobs="8", mirror=tmp_path / "none"
    )
    run = buildbox.run_spec(options, "img", "true")
    assert run.extra[1:3] == ("-m", "12g")
    assert run.env["V8_BUILD_JOBS"] == "4"
    assert run.env["CORE_BUILD_JOBS"] == "8"
    assert next(m for m in run.mounts if m.target == "/build").source == "vol"


def test_every_step_probes_that_the_tree_is_writable_first():
    script = buildbox.guarded("build/engine/smoke.sh")
    assert script.index("touch /build/.writable") < script.index(
        "build/engine/smoke.sh"
    )


def test_a_wheel_set_must_be_pure_python():
    names = ["libera-0.4.0-py3-none-any.whl", "bottle-0.13-py2.py3-none-any.whl"]
    assert flatpak.impure_wheels(names) == []
    assert flatpak.impure_wheels(["x-1.0-cp313-cp313-linux_x86_64.whl"]) == [
        "x-1.0-cp313-cp313-linux_x86_64.whl"
    ]


def test_diagnose_must_say_a_window_and_a_bundled_payload():
    # The lines --diagnose prints about a payload, as --payload-status does.
    good = (
        "window     ok\n"
        "payload:   /app/share/libera/payload\n"
        "found via: bundled\n"
        "version:   0.4\n"
    )
    assert flatpak.diagnose_problems(good) == []
    assert (
        len(
            flatpak.diagnose_problems(
                "window     NOT AVAILABLE\npayload:   /p\nfound via: installed\n"
            )
        )
        == 2
    )


def test_only_this_architectures_core_is_bundled():
    assert flatpak.staged_names("arm64", ["fonts-core.tar.gz"]) == [
        "manifest.json",
        "core-linux-arm64.tar.gz",
        "editors.tar.gz",
        "fonts-core.tar.gz",
    ]
    assert "fonts-core.tar.gz" in flatpak.staged_names("amd64", [])
    assert linux_platform("amd64") == "linux-x86_64"


def test_the_window_is_checked_on_remote_linux_builders_only():
    builders = [
        Builder("macos-arm64", "local", None, True, "~/r"),
        Builder("linux-x86_64", "fedora.zt", None, False, "~/r"),
        Builder("linux-arm64", "local", None, False, "~/r"),
        Builder("windows-x86_64", "builder-windows", "C:/b/out/dist", False, "~/r"),
    ]
    assert [b.target for b in inventory.linux_remotes(builders)] == ["fedora.zt"]


def test_a_window_passes_on_the_verdict_line_and_nothing_else():
    assert released_gui.passed("==> PASS\n__LIBERA__=ok\n")
    assert not released_gui.passed("FAIL: no window\n__LIBERA__=no window after 90s")
    # The word turns up elsewhere: a document's path, the app's own log.
    assert not released_gui.passed("    document: /home/PASS/a.docx\n       | PASS\n")


def test_tidy_finds_only_what_is_there(tmp_path):
    root = tmp_path / "repo"
    (root / "build" / "out").mkdir(parents=True)
    (root / "build" / "flatpak").mkdir()
    (root / "build" / "flatpak" / "libera-1-amd64.flatpak").write_text("x")
    found = tidy.found(root, tmp_path / "no-build-root")
    assert [p.relative_to(root) for p in found] == [
        Path("build/out"),
        Path("build/flatpak/libera-1-amd64.flatpak"),
    ]
