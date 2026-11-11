"""`lb components`: the two component packages, from a build's artifacts."""

from __future__ import annotations

import io
import json
import re
import tarfile
from typing import TYPE_CHECKING

import pytest
import tomllib
from libera_build import components, versions
from libera_build.repo import REPO
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path


def test_the_release_has_one_version_and_libera_pins_it():
    """One version, in six places: libera's own, the payload's, each
    component's, and the pins. 0.7.0 went out pinning components 0.7.1."""
    repo = REPO
    want = versions.payload_version(repo)
    assert versions.app_version(repo) == want
    for project in (components.CORE, components.WEB):
        doc = tomllib.loads((repo / project / "pyproject.toml").read_text())
        assert doc["project"]["version"] == want, project
    pins = tomllib.loads((repo / "pyproject.toml").read_text())["project"]
    assert f"libera-core=={want}" in pins["dependencies"]
    assert f"libera-web=={want}" in pins["dependencies"]
    # libera-web's build runs the core's x2t, so it pins the core too.
    web = tomllib.loads((repo / components.WEB / "pyproject.toml").read_text())
    assert f"libera-core=={want}" in web["build-system"]["requires"]


def test_bump_writes_the_version_everywhere_or_nowhere(tmp_path):
    for path, _ in versions.PLACES:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
    for path in {path for path, _ in versions.PLACES} | {"pyproject.toml"}:
        (tmp_path / path).write_text((REPO / path).read_text())
    before = versions.payload_version(REPO)

    versions.bump(tmp_path, "9.9.9")

    assert versions.app_version(tmp_path) == "9.9.9"
    assert versions.payload_version(tmp_path) == "9.9.9"
    for path, pattern in versions.PLACES:
        text = (tmp_path / path).read_text()
        assert pattern.format("9.9.9") in text, path
        assert pattern.format(before) not in text, path

    # A place that no longer says the old version stops it before any write.
    web = tmp_path / "components/web/pyproject.toml"
    web.write_text(web.read_text().replace('"libera-core==9.9.9"', '"libera-core"'))
    with pytest.raises(RefusedError, match=re.escape("libera-core==9.9.9")):
        versions.bump(tmp_path, "9.9.10")
    assert versions.app_version(tmp_path) == "9.9.9"


def test_bump_refuses_what_is_not_a_version(tmp_path):
    with pytest.raises(RefusedError, match="not a version"):
        versions.bump(tmp_path, "latest")


def make_tarball(path: Path, files: dict[str, bytes], links: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755
            tar.addfile(info, io.BytesIO(data))
        for name, target in links.items():
            info = tarfile.TarInfo(name)
            info.type, info.linkname = tarfile.SYMTYPE, target
            tar.addfile(info)


@pytest.fixture(name="dist")
def a_dist(tmp_path):
    """The artifacts of a macOS build, its links as the real core has them."""
    dist = tmp_path / "dist"
    dist.mkdir()
    make_tarball(
        dist / "core-macos-arm64.tar.gz",
        {
            "bin/x2t": b"x2t",
            "bin/libicuuc.74.2.dylib": b"icu",
            "bin/f.framework/Versions/1/f": b"framework",
        },
        {
            "bin/libicuuc.74.dylib": "libicuuc.74.2.dylib",
            "bin/libicuuc.dylib": "libicuuc.74.2.dylib",
            "bin/f.framework/Versions/Current": "1",
            "bin/f.framework/f": "Versions/Current/f",
        },
    )
    make_tarball(dist / "editors.tar.gz", {"sdkjs/word/sdk-all.js": b"js"}, {})
    make_tarball(dist / "fonts-core.tar.gz", {"fonts-src/a.ttf": b"font"}, {})
    (dist / "manifest.json").write_text(
        json.dumps({
            "payload_version": "0.7",
            "built": "2026-10-27T06:00:00Z",
            "font_set": "core",
            "artifacts": [],
            "source": {"libera_commit": "abc"},
        })
    )
    return dist


def test_a_core_has_no_links_and_its_versioned_names_hold_the_files(dist, tmp_path):
    """A wheel holds no symlinks. The binaries load libicuuc.74.dylib and the
    framework's Versions/1, never the unversioned names."""
    core = tmp_path / "libera_core"

    components.unpack_core(core, dist, "macos-arm64")

    links = [p for p in core.rglob("*") if p.is_symlink()]
    assert links == []
    assert (core / "bin" / "libicuuc.74.dylib").read_bytes() == b"icu"
    assert not (core / "bin" / "libicuuc.dylib").exists()
    assert (core / "bin" / "f.framework" / "Versions" / "1" / "f").is_file()


def test_a_core_with_no_converter_is_refused(dist, tmp_path):
    make_tarball(dist / "core-macos-arm64.tar.gz", {"bin/README": b""}, {})

    with pytest.raises(RefusedError, match="no x2t"):
        components.unpack_core(tmp_path / "libera_core", dist, "macos-arm64")


def test_the_editors_say_what_they_are_built_from(dist, tmp_path):
    """What --payload-status says, the source among it, which the AGPL wants
    said: an installed payload has it from the installer, the components
    from the build."""
    web = tmp_path / "libera_web"

    components.unpack_web(web, dist, {})

    assert (web / "sdkjs" / "word" / "sdk-all.js").is_file()
    assert (web / "fonts-src" / "a.ttf").is_file()
    record = json.loads((web / "payload.json").read_text())
    assert record["payload_version"] == "0.7"
    assert record["source"] == {"libera_commit": "abc"}
    assert "platform" not in record, "libera-web is every platform's"


def refuse_to_build(*args, **kwargs):
    msg = "the refusal comes before any build"
    raise AssertionError(msg)


@pytest.fixture(name="no_build")
def nothing_runs(monkeypatch):
    monkeypatch.setattr(components, "run_here", refuse_to_build)
    monkeypatch.setattr(components, "source_problems", refuse_to_build)


@pytest.mark.usefixtures("no_build")
def test_a_platform_with_no_wheel_tag_is_refused_before_the_build(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        components.locate, "get_current_platform", lambda: "macos-x86_64"
    )
    with pytest.raises(RefusedError, match="not on macos-x86_64"):
        components.build_core(REPO, tmp_path)


@pytest.mark.usefixtures("no_build")
def test_a_build_folder_on_a_missing_volume_asks_for_build_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        components.locate, "get_current_platform", lambda: "macos-arm64"
    )
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "no-volume" / "euro-office-build"))
    with pytest.raises(RefusedError, match="set BUILD_ROOT"):
        components.build_core(REPO, tmp_path)


class RanError(Exception):
    pass


def test_a_build_here_checks_the_toolchain_before_it_fetches(monkeypatch, tmp_path):
    def capture(argv, *args, **kwargs):
        raise RanError(argv[-1])

    monkeypatch.setattr(
        components.locate, "get_current_platform", lambda: "macos-arm64"
    )
    monkeypatch.setattr(components, "source_problems", lambda *_, **__: ["unfetched"])
    monkeypatch.setattr(components, "run_here", capture)
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path))
    with pytest.raises(RanError) as ran:
        components.build_core(REPO, tmp_path)
    steps = str(ran.value).splitlines()
    assert steps[1:3] == [
        "build/engine/toolchain.sh check",
        "build/engine/build.sh fetch core libxml2",
    ]
