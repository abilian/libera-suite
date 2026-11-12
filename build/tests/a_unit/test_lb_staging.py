"""`stage`: what it gathers, and when its stamp still holds for `publish`."""

from __future__ import annotations

import json
import zipfile

import pytest
from libera_build.artifacts import run_pypi
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
    files = {f.name: staging.hash_file(f) for f in dest.iterdir()}
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


def test_another_commit_finds_nothing_staged(stage, monkeypatch):
    """Each commit stages into a directory of its own, so a stage from the
    commit before is not this one's to publish."""
    monkeypatch.setattr(staging.repo, "head", lambda _root: "d" * 40)
    (problem,) = staging.stamp_problems(stage)
    assert "nothing is staged at ddddddddd: run stage" in problem


def test_each_builder_stages_the_bundle_its_users_download(tmp_path, monkeypatch):
    monkeypatch.setattr(staging.repo, "head", lambda _root: HEAD)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    ctx = Context(
        root=tmp_path,
        builders=[
            Builder("macos-arm64", "local", "~/r"),
            Builder("linux-x86_64", "x", "~/r"),
            Builder("windows-x86_64", "w", "~/r"),
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


def release_tree(root):
    """A 9.9.9 with every file stage gathers for no builder: the components,
    and libera's wheel and sdist."""
    (root / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    payload = root / "src" / "libera" / "payload"
    payload.mkdir(parents=True)
    (payload / "payload.version").write_text('version = "9.9.9"\n')
    pypi = run_pypi(root)
    pypi.mkdir(parents=True)
    for name in ("libera_core-9.9.9.tar.gz", "libera_web-9.9.9-py3-none-any.whl"):
        (pypi / name).write_bytes(name.encode())
    (pypi / "libera-9.9.9.tar.gz").write_bytes(b"sdist")
    with zipfile.ZipFile(pypi / "libera-9.9.9-py3-none-any.whl", "w") as wheel:
        wheel.writestr(
            "libera-9.9.9.dist-info/METADATA",
            "Requires-Dist: libera-core==9.9.9\nRequires-Dist: libera-web==9.9.9\n",
        )
    return Context(root=root, builders=[], phases=["stage"])


def test_stage_stamps_what_this_commit_gathered(tmp_path, monkeypatch):
    monkeypatch.setattr(staging.repo, "head", lambda _root: HEAD)
    ctx = release_tree(tmp_path)
    staging.run(ctx)
    assert staging.stamp_problems(tmp_path) == []
    assert "libera-9.9.9-py3-none-any.whl" in [f.name for f in staging.staged(tmp_path)]


def test_stage_refuses_what_another_commit_gathered(tmp_path, monkeypatch, capsys):
    """A run directory is a commit's: the files the commit before gathered
    are not this one's to stage."""
    monkeypatch.setattr(staging.repo, "head", lambda _root: HEAD)
    ctx = release_tree(tmp_path)
    monkeypatch.setattr(staging.repo, "head", lambda _root: "d" * 40)
    with pytest.raises(RefusedError, match="nothing was staged"):
        staging.run(ctx)
    assert "is not here: run the components phase" in capsys.readouterr().out
    assert not staging.folder(tmp_path).exists()


STAGED = (
    "libera-9.9.9-py3-none-any.whl",
    "libera-9.9.9.tar.gz",
    "libera-9.9.9-amd64.flatpak",
    "libera_core-9.9.9-py3-none-macosx_11_0_arm64.whl",
    "libera_core-9.9.9.tar.gz",
    "libera_web-9.9.9-py3-none-any.whl",
)


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    """A staged 9.9.9, and what publish did with it, in order: each `uv
    publish`'s files, and the CDN's `ready` and `extras`."""
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    for name in STAGED:
        (tmp_path / name).write_bytes(b"x")
    done = []

    def uv_publish(argv, *_args, **_kwargs):
        done.append([a.rsplit("/", 1)[-1] for a in argv if a.startswith("/")])

    monkeypatch.setattr(publishing, "run_here", uv_publish)
    monkeypatch.setattr(publishing.cdn, "ready", lambda *_a, **_k: done.append("ready"))
    monkeypatch.setattr(
        publishing.cdn, "extras", lambda *_a, **_k: done.append("extras")
    )
    monkeypatch.setattr(publishing.place, "here", lambda: None)
    return tmp_path, sorted(tmp_path / name for name in STAGED), done


def test_publish_sends_the_components_before_libera_and_the_cdn_last(uploads):
    root, staged, done = uploads
    publishing.publish(
        Context(root=root, builders=[], phases=[], yes=True), root, staged
    )
    assert done == [
        "ready",
        [
            "libera_core-9.9.9-py3-none-macosx_11_0_arm64.whl",
            "libera_core-9.9.9.tar.gz",
            "libera_web-9.9.9-py3-none-any.whl",
        ],
        ["libera-9.9.9-py3-none-any.whl", "libera-9.9.9.tar.gz"],
        "extras",
    ]


def test_publish_uploads_nothing_until_asked(uploads, monkeypatch):
    root, staged, done = uploads

    def no(_app):
        msg = "nothing was published."
        raise RefusedError(msg)

    monkeypatch.setattr(publishing, "confirm", no)
    with pytest.raises(RefusedError):
        publishing.publish(Context(root=root, builders=[], phases=[]), root, staged)
    assert done == ["ready"]


def test_publish_uploads_nothing_the_cdn_would_refuse(uploads, monkeypatch):
    root, staged, done = uploads

    def refused(*_a, **_k):
        msg = "names no installer"
        raise RefusedError(msg)

    monkeypatch.setattr(publishing.cdn, "ready", refused)
    with pytest.raises(RefusedError):
        publishing.publish(
            Context(root=root, builders=[], phases=[], yes=True), root, staged
        )
    assert done == []


class Answering:
    """A builder that takes every file and answers every script with `said`."""

    name = "builder"

    def __init__(self, said: str) -> None:
        self.said = said

    @staticmethod
    def send(_local, _there):
        return 0, ""

    def capture(self, _script):
        return self.said


GOOD = "INSTALLED=9.9.9\nCONVERTED=1\nVERSION=libera 9.9.9\n"


@pytest.mark.parametrize(
    ("platform", "said", "passes"),
    [
        ("linux-x86_64", GOOD, True),
        ("linux-x86_64", GOOD.replace("CONVERTED=1", "CONVERTED=0"), False),
        ("linux-x86_64", GOOD.replace("INSTALLED=9.9.9", "INSTALLED=9.9.8"), False),
        ("linux-x86_64", "uv: no solution\nINSTALLED=none\n", False),
        # The Mac opens a window too, and an empty canvas is a few kilobytes.
        ("macos-arm64", GOOD + "WINDOW=4000\n", False),
        ("macos-arm64", GOOD + "WINDOW=90000\n", True),
        ("macos-arm64", GOOD, False),
    ],
)
def test_a_platform_passes_the_stage_only_installed_converted_and_drawn(
    tmp_path, platform, said, passes
):
    with zipfile.ZipFile(tmp_path / "libera-9.9.9-py3-none-any.whl", "w") as wheel:
        wheel.writestr(
            "libera-9.9.9.dist-info/METADATA",
            "Requires-Dist: libera-core==9.9.9\nRequires-Dist: libera-web==9.9.9\n",
        )
    b = Builder(platform, "x", "~/r")
    found = staging.installs(Answering(said), b, tmp_path, "9.9.9", [])
    assert (found == []) is passes, found


def test_distros_tries_a_stamped_stage_on_each_linux_builders_arch(stage, monkeypatch):
    tried = []
    monkeypatch.setattr(staging.matrix, "run", lambda d, a: tried.append((d, a)))
    builders = [
        Builder("macos-arm64", "local", "~/r"),
        Builder("linux-x86_64", "x", "~/r"),
        Builder("linux-arm64", "y", "~/r"),
    ]
    staging.distros(Context(root=stage, builders=builders, phases=["distros"]))
    assert tried == [(staging.folder(stage), ("x86_64", "arm64"))]


def test_distros_refuses_a_stage_that_was_never_stamped(stage, monkeypatch):
    (staging.folder(stage) / staging.STAMP).unlink()
    monkeypatch.setattr(staging.matrix, "run", lambda *_: pytest.fail("ran"))
    ctx = Context(
        root=stage, builders=[Builder("linux-x86_64", "x", "~/r")], phases=["distros"]
    )
    with pytest.raises(RefusedError, match="no distribution was tried"):
        staging.distros(ctx)
