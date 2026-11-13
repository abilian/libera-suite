"""`stage`: what it gathers, and when its stamp still holds for `publish`."""

from __future__ import annotations

import json
import zipfile
from typing import TYPE_CHECKING

import pytest
from libera_build import released_gui
from libera_build.artifacts import run_pypi
from libera_build.inventory import Builder
from libera_build.origin import staged as origin
from libera_build.release.context import Context
from libera_build.release.phases import publishing, staging
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

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


def test_the_mac_installs_with_install_sh_from_the_staged_origin(tmp_path):
    """The install page's command, LIBERA_ORIGIN aside, in a home of its own;
    then a window, and Libera.app taken out of LaunchServices again."""
    script = publishing.origin_install_script(
        "9.9.9", tmp_path / "my zone", tmp_path, "macos-arm64"
    )
    assert f"served=$(cd '{tmp_path}/my zone' &&" in script
    assert 'curl -fsSL "$LIBERA_ORIGIN/install.sh" | sh -s --' in script
    assert 'PIP_FIND_LINKS="$LIBERA_ORIGIN/pypi/"' in script
    assert 'export HOME="$T/home"' in script
    assert "WINDOW=" in script
    assert script.rstrip().endswith("--launcher-remove > /dev/null 2>&1")
    assert "LIBERA_VERSION" not in script
    assert "five-minutes.sh" in script
    assert "macos-arm64-$ext.png" in script
    rc = publishing.origin_install_script("9.9.9rc1", tmp_path, tmp_path, "m")
    assert "export LIBERA_VERSION=9.9.9rc1" in rc


def release_tree(root):
    """A 9.9.9 with every file stage gathers for no builder: the components,
    and libera's wheel and sdist."""
    (root / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    (root / "build" / "install").mkdir(parents=True)
    for script in ("install.sh", "install.ps1"):
        (root / "build" / "install" / script).write_text(script)
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
FIVE = "FIVE_DOCX=ok\nFIVE_XLSX=ok\nFIVE_PPTX=ok\n"


@pytest.mark.parametrize(
    ("platform", "said", "passes"),
    [
        ("linux-x86_64", GOOD, True),
        ("linux-x86_64", GOOD.replace("CONVERTED=1", "CONVERTED=0"), False),
        ("linux-x86_64", GOOD.replace("INSTALLED=9.9.9", "INSTALLED=9.9.8"), False),
        ("linux-x86_64", "uv: no solution\nINSTALLED=none\n", False),
        # The Mac opens a window too, and an empty canvas is a few kilobytes.
        ("macos-arm64", GOOD + "WINDOW=4000\n" + FIVE, False),
        ("macos-arm64", GOOD + "WINDOW=90000\n" + FIVE, True),
        ("macos-arm64", GOOD + FIVE, False),
        # And it spends five minutes in each editor.
        ("macos-arm64", GOOD + "WINDOW=90000\n", False),
        (
            "macos-arm64",
            GOOD + "WINDOW=90000\n" + FIVE.replace("XLSX=ok", "XLSX=the window died"),
            False,
        ),
    ],
)
def test_a_platform_passes_the_stage_only_installed_converted_and_drawn(
    tmp_path, monkeypatch, platform, said, passes
):
    monkeypatch.setattr(staging.repo, "head", lambda _root: HEAD)
    staging.folder(tmp_path).mkdir(parents=True)
    wheel_path = staging.folder(tmp_path) / "libera-9.9.9-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as wheel:
        wheel.writestr(
            "libera-9.9.9.dist-info/METADATA",
            "Requires-Dist: libera-core==9.9.9\nRequires-Dist: libera-web==9.9.9\n",
        )
    b = Builder(platform, "x", "~/r")
    found = staging.installs(Answering(said), b, tmp_path, "9.9.9")
    assert (found == []) is passes, found


class Recording(Answering):
    """A builder that answers every script with `said`, and keeps what it was
    sent and asked."""

    def __init__(self, said: str) -> None:
        super().__init__(said)
        self.sent: list[str] = []
        self.scripts: list[str] = []

    def send(self, local, _there):
        self.sent.append(local.name)
        return 0, ""

    def capture(self, script):
        self.scripts.append(script)
        return self.said


def restamp(stage: Path, *names: str) -> None:
    """`names` added to the staged files, and the stage stamped again."""
    dest = staging.folder(stage)
    for name in names:
        (dest / name).write_bytes(name.encode())
    files = {
        f.name: staging.hash_file(f) for f in dest.iterdir() if f.suffix != ".json"
    }
    (dest / staging.STAMP).write_text(json.dumps({"commit": HEAD, "files": files}))


@pytest.mark.parametrize(
    ("said", "problem"),
    [
        ("    fedora:45     ok\n\nPASS\n", None),
        ("    fedora:45     FAIL: GLIBC_2.38 not found\nTraceback\n", "did not pass"),
        # A checkout from before matrix ran as a module: it said nothing.
        ("", "said nothing there"),
    ],
)
def test_distros_runs_the_matrix_on_each_linux_builder(
    stage, monkeypatch, capsys, said, problem
):
    """There, natively and with the builder's own engine; this Mac's docker
    was a daemon over ssh, which cannot mount the stage."""
    restamp(
        stage,
        "libera_core-9.9.9-py3-none-manylinux_2_34_x86_64.whl",
        "libera_core-9.9.9-py3-none-manylinux_2_34_aarch64.whl",
        "libera_web-9.9.9-py3-none-any.whl",
    )
    zone = staging.origin_folder(stage)
    (zone / "pypi").mkdir(parents=True)
    (zone / "install.sh").write_text("install")
    for f in staging.folder(stage).glob("*.whl"):
        (zone / "pypi" / f.name).write_bytes(f.read_bytes())
    hosts = {"x": Recording(said), "y": Recording(said)}
    monkeypatch.setattr(staging.matrix, "run", lambda *_: pytest.fail("ran here"))
    builders = [
        Builder("macos-arm64", "local", "~/r"),
        Builder("linux-x86_64", "x", "~/r"),
        Builder("linux-arm64", "y", "~/r"),
    ]
    ctx = Context(
        root=stage,
        builders=builders,
        phases=["distros"],
        host_for=lambda b: hosts[b.target],
    )
    if problem is None:
        staging.distros(ctx)
    else:
        with pytest.raises(RefusedError, match="did not pass every distribution"):
            staging.distros(ctx)
        assert f"linux-x86_64: the matrix {problem}" in capsys.readouterr().out
    assert hosts["x"].sent == [
        "install.sh",
        "libera-9.9.9-py3-none-any.whl",
        "libera_core-9.9.9-py3-none-manylinux_2_34_x86_64.whl",
        "libera_web-9.9.9-py3-none-any.whl",
    ]
    assert hosts["y"].sent[2].endswith("_aarch64.whl")
    assert (
        'libera_build.matrix "$HOME/libera-stage/9.9.9/origin" x86_64'
        in hosts["x"].scripts[-1]
    )


def test_distros_refuses_a_stage_that_was_never_stamped(stage, monkeypatch):
    (staging.folder(stage) / staging.STAMP).unlink()
    monkeypatch.setattr(staging.matrix, "run", lambda *_: pytest.fail("ran"))
    ctx = Context(
        root=stage, builders=[Builder("linux-x86_64", "x", "~/r")], phases=["distros"]
    )
    with pytest.raises(RefusedError, match="no distribution was tried"):
        staging.distros(ctx)


def test_the_staged_origin_is_laid_out_as_the_cdn_zone(tmp_path):
    root = tmp_path / "repo"
    (root / "build" / "install").mkdir(parents=True)
    for script in ("install.sh", "install.ps1"):
        (root / "build" / "install" / script).write_text(script)
    stage = tmp_path / "staged"
    stage.mkdir()
    for name in (*STAGED, "Libera-Suite-Setup-9.9.9.exe"):
        (stage / name).write_bytes(name.encode())
    zone = origin.lay_out(sorted(stage.iterdir()), tmp_path / "zone", "9.9.9", root)
    files = sorted(
        p.relative_to(zone).as_posix() for p in zone.rglob("*") if p.is_file()
    )
    assert files == [
        "bundles/Libera-Suite-Setup-9.9.9.exe",
        "bundles/latest",
        "bundles/latest-windows",
        "bundles/libera-9.9.9-amd64.flatpak",
        "install.ps1",
        "install.sh",
        "pypi/libera-9.9.9-py3-none-any.whl",
        "pypi/libera-9.9.9.tar.gz",
        "pypi/libera_core-9.9.9-py3-none-macosx_11_0_arm64.whl",
        "pypi/libera_core-9.9.9.tar.gz",
        "pypi/libera_web-9.9.9-py3-none-any.whl",
    ]
    assert (zone / "bundles" / "latest").read_text() == "9.9.9\n"
    # Links: the stage is the files publish uploads, and these are those.
    assert (zone / "bundles/libera-9.9.9-amd64.flatpak").samefile(
        stage / "libera-9.9.9-amd64.flatpak"
    )


@pytest.mark.parametrize(
    ("platform", "sent"),
    [
        (
            "linux-x86_64",
            ["install.sh", "bundles/latest", "bundles/libera-9.9.9-amd64.flatpak"],
        ),
        (
            "windows-x86_64",
            [
                "install.ps1",
                "bundles/latest-windows",
                "bundles/Libera-Suite-Setup-9.9.9.exe",
                "bundles/Libera-Suite-Setup-9.9.9.exe.sha256",
            ],
        ),
    ],
)
def test_each_machine_is_sent_its_part_of_the_origin_and_serves_it(
    tmp_path, platform, sent
):
    for path in sent:
        (tmp_path / "zone" / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "zone" / path).write_text(path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    host = Shipping("uname: Linux\n__LIBERA__=ok\n")
    options = released_gui.ReleasedGuiOptions(
        origin=tmp_path / "zone", root=tmp_path, host_for=lambda _: host
    )
    released_gui.on_host(host, platform, options)
    assert [t for _, t in host.sent if t.startswith("libera-stage/")] == [
        f"libera-stage/9.9.9/origin/{path}" for path in sent
    ]
    run = host.scripts[-1]
    assert run.index("export LIBERA_ORIGIN=") < run.index("released-gui")
    assert 'cd "$HOME/libera-stage/9.9.9/origin"' in run


class Shipping(Answering):
    """A builder that keeps where each file was sent and what it was asked."""

    def __init__(self, said: str) -> None:
        super().__init__(said)
        self.sent: list[tuple[str, str]] = []
        self.scripts: list[str] = []

    def send(self, local, there):
        self.sent.append((local.name, there))
        return 0, ""

    def capture(self, script):
        self.scripts.append(script)
        return "reachable\n" + self.said

    @staticmethod
    def fetch(_there, _local):
        return 1, "no screenshot here"
