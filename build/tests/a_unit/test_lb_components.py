"""`lb components`: the two component packages, filled from a build's artifacts."""

from __future__ import annotations

import io
import json
import tarfile
from typing import TYPE_CHECKING

import pytest
import tomllib
from libera_build import components, versions
from libera_build.repo import REPO
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path


def test_the_components_are_the_payload_version_and_libera_pins_it():
    """One version, in four places: a component that is not the payload
    version is refused at start, and a pin that is not it cannot install."""
    repo = REPO
    want = versions.payload_version(repo)
    for project in (components.CORE, components.WEB):
        doc = tomllib.loads((repo / project / "pyproject.toml").read_text())
        assert doc["project"]["version"] == want, project
    pins = tomllib.loads((repo / "pyproject.toml").read_text())["project"]
    assert f"libera-core=={want}" in pins["dependencies"]
    assert f"libera-web=={want}" in pins["dependencies"]


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


@pytest.fixture(name="repo")
def a_repo(tmp_path):
    for project in (components.CORE, components.WEB):
        package = components.package_dir(tmp_path, project)
        package.mkdir(parents=True)
        (package / "__init__.py").write_text('"""A component."""\n')
    return tmp_path


def test_a_filled_core_has_no_links_and_its_versioned_names_hold_the_files(repo, dist):
    """A wheel holds no symlinks. The binaries load libicuuc.74.dylib and the
    framework's Versions/1, never the unversioned names."""
    stale = components.package_dir(repo, components.CORE) / "bin" / "old"
    stale.parent.mkdir()
    stale.write_bytes(b"from an earlier fill")

    components.fill(repo, dist, "macos-arm64")

    core = components.package_dir(repo, components.CORE)
    links = [p for p in core.rglob("*") if p.is_symlink()]
    assert links == []
    assert (core / "bin" / "libicuuc.74.dylib").read_bytes() == b"icu"
    assert not (core / "bin" / "libicuuc.dylib").exists()
    assert (core / "bin" / "f.framework" / "Versions" / "1" / "f").is_file()
    assert not stale.exists()
    assert (core / "__init__.py").is_file()


def test_a_filled_core_names_the_editors_where_they_were_put(repo, dist):
    components.fill(repo, dist, "macos-arm64")

    core = components.package_dir(repo, components.CORE)
    web = components.package_dir(repo, components.WEB)
    config = (core / "bin" / "DoctRenderer.config").read_text()
    sdkjs = (core / "bin" / config.split("<sdkjs>./")[1].split("<")[0]).resolve()
    assert sdkjs == (web / "sdkjs").resolve()
    assert (web / "sdkjs" / "word" / "sdk-all.js").is_file()
    assert (web / "fonts-src" / "a.ttf").is_file()


def test_a_wheels_core_names_the_editors_beside_it_in_site_packages(
    repo, dist, tmp_path
):
    package = components.stage(repo, components.CORE, tmp_path / "stage" / "core")
    components.fill_core(package, dist, "macos-arm64", package.parent / "libera_web")

    config = (package / "bin" / "DoctRenderer.config").read_text()
    assert "<sdkjs>./../../libera_web/sdkjs</sdkjs>" in config


def test_a_core_with_no_converter_is_refused(repo, dist):
    make_tarball(dist / "core-macos-arm64.tar.gz", {"bin/README": b""}, {})

    with pytest.raises(RefusedError, match="no x2t"):
        components.fill(repo, dist, "macos-arm64")


def test_a_platform_with_no_wheel_tag_is_refused(dist):
    (dist / "core-plan9-mips.tar.gz").write_bytes(b"")

    with pytest.raises(RefusedError, match="no wheel tag for plan9-mips"):
        components.platforms_in(dist)


def test_the_editors_say_what_they_are_built_from(repo, dist):
    """What --payload-status says, the source among it, which the AGPL wants
    said: an installed payload has it from the installer, the components
    from the build."""
    components.fill(repo, dist, "macos-arm64")

    web = components.package_dir(repo, components.WEB)
    record = json.loads((web / "payload.json").read_text())
    assert record["payload_version"] == "0.7"
    assert record["source"] == {"libera_commit": "abc"}
    assert "platform" not in record, "libera-web is every platform's"
