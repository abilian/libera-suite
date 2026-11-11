"""`stage`: what it gathers, and when its stamp still holds for `publish`."""

from __future__ import annotations

import json

import pytest
from libera_build.inventory import Builder
from libera_build.release.context import Context
from libera_build.release.phases import publishing, staging
from libera_build.report import RefusedError

HEAD = "c" * 40


@pytest.fixture
def stage(tmp_path, monkeypatch):
    """A staged 9.9.9, stamped at HEAD."""
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    monkeypatch.setattr(staging.repo, "head", lambda _root: HEAD)
    dest = staging.folder(tmp_path)
    dest.mkdir(parents=True)
    for name in ("libera-9.9.9-py3-none-any.whl", "libera-9.9.9-amd64.flatpak"):
        (dest / name).write_bytes(name.encode())
    files = {f.name: staging.digest(f) for f in dest.iterdir()}
    (dest / staging.STAMP).write_text(json.dumps({"commit": HEAD, "files": files}))
    return tmp_path


def test_a_stamp_holds_while_nothing_changed(stage):
    assert staging.stamp_problems(stage) == []
    names = [f.name for f in staging.staged(stage)]
    assert names == ["libera-9.9.9-amd64.flatpak", "libera-9.9.9-py3-none-any.whl"]


def test_the_bundles_signatures_made_by_publish_are_not_a_change(stage):
    (staging.folder(stage) / "libera-9.9.9-amd64.flatpak.asc").write_text("signed")
    assert staging.stamp_problems(stage) == []
    assert all(f.suffix != ".asc" for f in staging.staged(stage))


@pytest.mark.parametrize(
    ("change", "says"),
    [
        (lambda d: (d / "libera-9.9.9-py3-none-any.whl").write_bytes(b"x"), "changed"),
        (lambda d: (d / "libera-9.9.9.tar.gz").write_bytes(b"x"), "added after"),
        (lambda d: (d / "libera-9.9.9-amd64.flatpak").unlink(), "is gone"),
    ],
)
def test_publish_refuses_a_stage_that_moved(stage, change, says):
    change(staging.folder(stage))
    (problem,) = staging.stamp_problems(stage)
    assert says in problem
    with pytest.raises(RefusedError, match="the stage does not hold"):
        staging.staged(stage)


def test_publish_refuses_a_stage_from_another_commit(stage, monkeypatch):
    monkeypatch.setattr(staging.repo, "head", lambda _root: "d" * 40)
    (problem,) = staging.stamp_problems(stage)
    assert "staged at ccccccccc" in problem


def test_nothing_staged_says_to_stage(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    (problem,) = staging.stamp_problems(tmp_path)
    assert "run stage" in problem


def test_each_builder_stages_the_bundle_its_users_download(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    ctx = Context(
        root=tmp_path,
        builders=[
            Builder("macos-arm64", "local", None, True, "~/r"),
            Builder("linux-x86_64", "x", None, False, "~/r"),
            Builder("windows-x86_64", "w", "C:/b", False, "~/r"),
        ],
        phases=["stage"],
    )
    names = [f.name for f in staging.bundle_files(ctx)]
    assert names == [
        "libera-9.9.9-amd64.flatpak",
        "Libera-Suite-Setup-9.9.9.exe",
        "Libera-Suite-Setup-9.9.9.exe.sha256",
    ]


def test_a_staged_install_takes_libera_and_its_components_from_there_alone():
    script = publishing.install_script(
        "9.9.9", staged="libera-stage/9.9.9", deps=["pywebview>=6"]
    )
    assert '--index-url https://pypi.org/simple/ "pywebview>=6"' in script
    assert '--no-index --find-links "$dir"' in script
    assert '"libera==9.9.9"' in script
    assert "WINDOW=" not in script
    assert "WINDOW=" in publishing.install_script("9.9.9", staged="s", window=True)
