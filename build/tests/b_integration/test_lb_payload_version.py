"""Every reader of payload.version reads the same version.

The host reads it with tomllib, `lb` read it by splitting lines on `=`, and
each build script had a sed of its own: a trailing comment went into one
reader's version, and a CRLF checkout's carriage return into another's.
"""

from __future__ import annotations

import subprocess

import pytest
from libera_build import versions
from libera_build.repo import MANIFEST, PAYLOAD_VERSION, PINS, REPO
from libera_build.report import RefusedError

from libera import manifest

VARIANTS = {
    "plain": b'version = "0.4.1"\n',
    "commented": b'# why\nversion = "0.4.1"  # pinned\n',
    "crlf": b'# why\r\nversion = "0.4.1"\r\n',
}


@pytest.mark.parametrize("text", VARIANTS.values(), ids=list(VARIANTS))
def test_the_build_scripts_and_lb_read_the_same_version(tmp_path, text):
    (tmp_path / PAYLOAD_VERSION).parent.mkdir(parents=True)
    (tmp_path / PAYLOAD_VERSION).write_bytes(text)

    shell = subprocess.run(
        [
            "sh",
            "-c",
            '. "$0/build/engine/common.sh"; payload_version "$1"',
            REPO,
            tmp_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert shell == "0.4.1\n"
    assert versions.payload_version(tmp_path) == "0.4.1"


def checkout_with_dist(tmp_path, *, built_for: str):
    """A checkout wanting payload 0.5, holding the last release's manifest, and
    artifacts built for `built_for`."""
    root = tmp_path / "root"
    (root / PAYLOAD_VERSION).parent.mkdir(parents=True)
    (root / PAYLOAD_VERSION).write_text('version = "0.5"\n')
    (root / MANIFEST).write_text('{"payload_version": "0.4.1"}')
    (root / PINS).parent.mkdir(parents=True)
    (root / PINS).write_text('[repos]\ncore = "abc"\n')
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "editors.tar.gz").write_bytes(b"this builder's editors")
    stamped = manifest.stamp(
        dist, payload_version=built_for, font_set="core", repo=root
    )
    (dist / "manifest.json").write_text(stamped.to_json())
    return root, dist


def test_the_bundled_manifest_is_the_one_beside_the_artifacts(tmp_path):
    """Not the last release's, which the installer would read first and refuse."""
    root, dist = checkout_with_dist(tmp_path, built_for="0.5")
    versions.stamp_bundled_manifest(root, dist)
    assert (root / MANIFEST).read_bytes() == (dist / "manifest.json").read_bytes()


def test_artifacts_for_another_payload_are_not_stamped(tmp_path):
    root, dist = checkout_with_dist(tmp_path, built_for="0.4.1")
    with pytest.raises(RefusedError, match=r"this tree wants 0\.5"):
        versions.stamp_bundled_manifest(root, dist)
    assert "0.4.1" in (root / MANIFEST).read_text()
