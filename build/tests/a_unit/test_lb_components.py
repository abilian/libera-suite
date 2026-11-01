"""`lb components`: the two component packages, from a build's artifacts."""

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


def test_an_unpacked_payload_is_one_folder_the_host_takes(dist, tmp_path):
    """For LIBERA_PAYLOAD and the Windows installer: its own core, and a
    configuration that names the editors beside it."""
    dest = tmp_path / "payload"
    (dest / "stale").mkdir(parents=True)

    components.unpack(dest, dist, "macos-arm64")

    config = (dest / "bin" / "DoctRenderer.config").read_text()
    assert "<sdkjs>./../sdkjs</sdkjs>" in config
    assert (dest / "sdkjs" / "word" / "sdk-all.js").is_file()
    assert not (dest / "stale").exists()
    assert not any(p.is_symlink() for p in dest.rglob("*"))
    record = json.loads((dest / "payload.json").read_text())
    assert record["platform"] == "macos-arm64"
