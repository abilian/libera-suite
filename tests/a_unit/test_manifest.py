"""The payload manifest's one definition: its format, selection, verification."""

from __future__ import annotations

import ast
import json
import pathlib
import sys
import tarfile

import pytest

from libera import manifest
from libera.manifest import Artifact, Manifest, ManifestError

CORE_MAC = Artifact("core-macos-arm64.tar.gz", "core", "macos-arm64", 3, "a" * 64)
CORE_ARM = Artifact("core-linux-arm64.tar.gz", "core", "linux-arm64", 3, "b" * 64)
EDITORS = Artifact("editors.tar.gz", "editors", None, 5, "c" * 64)
FULL = Manifest(
    "0.4",
    (CORE_ARM, CORE_MAC, EDITORS),
    built="2026-10-07T00:00:00Z",
    font_set="core",
    source={"libera_commit": "d" * 40, "libera_dirty": False},
)


def test_a_manifest_survives_its_file_with_its_keys_in_order():
    text = FULL.to_json()
    assert list(json.loads(text)) == [
        "payload_version",
        "built",
        "font_set",
        "artifacts",
        "source",
    ]
    assert list(json.loads(text)["artifacts"][0]) == [
        "name",
        "kind",
        "platform",
        "size",
        "sha256",
    ]
    assert Manifest.from_dict(json.loads(text)) == FULL


def test_the_optional_fields_may_be_absent():
    found = Manifest.from_dict({"payload_version": "0.4", "artifacts": []})
    assert (found.built, found.font_set, found.source) == (None, None, {})


def test_something_that_is_not_a_manifest_is_refused():
    with pytest.raises(ManifestError):
        Manifest.from_dict({"payload_version": "0.4"})
    with pytest.raises(ManifestError):
        Manifest.from_dict({"payload_version": "0.4", "artifacts": [{"name": "x"}]})


def test_a_machine_gets_its_own_core_and_the_shared_artifacts():
    assert FULL.select("linux-arm64") == [CORE_ARM, EDITORS]
    with pytest.raises(ManifestError, match="no core artifact for windows-x86_64"):
        FULL.select("windows-x86_64")


def test_provenance_is_read_from_the_source():
    assert FULL.commit == "d" * 40
    assert not FULL.dirty
    assert FULL.core_platforms == ["linux-arm64", "macos-arm64"]


def test_a_file_is_its_artifact_only_by_its_hash(tmp_path):
    f = tmp_path / "editors.tar.gz"
    f.write_bytes(b"bytes")
    good = manifest.describe(f)
    assert good.problem_with(f) is None
    f.write_bytes(b"other")
    assert "failed verification" in good.problem_with(f)


def test_the_platform_comes_from_the_name_not_the_machine(tmp_path):
    for name in ("core-linux-x86_64.tar.gz", "fonts-core.tar.gz"):
        (tmp_path / name).write_bytes(b"x")
    core = manifest.describe(tmp_path / "core-linux-x86_64.tar.gz")
    fonts = manifest.describe(tmp_path / "fonts-core.tar.gz")
    assert (core.kind, core.platform) == ("core", "linux-x86_64")
    assert (fonts.kind, fonts.platform) == ("fonts", None)


def test_pins_are_the_repos_table_only(tmp_path):
    pins = tmp_path / "pins.toml"
    pins.write_text(
        '[meta]\nx = "no"\n[repos]\n# a comment\ncore = "abc"  # pinned 2026\nsdkjs = "def"\n'
    )
    assert manifest.read_pins(pins) == {"core": "abc", "sdkjs": "def"}


def test_stamp_describes_every_tarball_in_the_directory(tmp_path):
    repo = tmp_path / "repo"
    (repo / "build" / "upstream").mkdir(parents=True)
    (repo / "build" / "upstream" / "pins.toml").write_text('[repos]\ncore = "abc"\n')
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in ("core-linux-arm64.tar.gz", "editors.tar.gz", "notes.txt"):
        with tarfile.open(dist / name, "w:gz"):
            pass
    found = manifest.stamp(
        dist, payload_version="0.4", font_set="core", repo=repo, now=0
    )
    assert [a.name for a in found.artifacts] == [
        "core-linux-arm64.tar.gz",
        "editors.tar.gz",
    ]
    assert found.built == "1970-01-01T00:00:00Z"
    assert found.source["pins"] == {"core": "abc"}
    # Not a checkout: no commit to name, which the manifest says rather than invents.
    assert found.source["libera_commit"] is None


def test_it_imports_nothing_the_build_containers_python_lacks():
    """dist.sh runs this in Ubuntu 22.04's Python 3.10, with nothing installed:
    the standard library only, and nothing in it newer than 3.10."""
    tree = ast.parse(pathlib.Path(manifest.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.discard("__future__")
    assert imported <= set(sys.stdlib_module_names), imported - set(
        sys.stdlib_module_names
    )
    assert not imported & {"tomllib"}, "tomllib is 3.11"
