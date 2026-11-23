"""The components' cache key: what they are built from, and nothing else.

A cache that reads "whatever was there" passed a bundle once that nobody had
built. This one is found by the inputs' blobs at the commit: a change to one
is a new key, a version bump is not, and an uncommitted change is no key.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from libera_build import components, versions

if TYPE_CHECKING:
    from pathlib import Path


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def commit(repo: Path) -> None:
    git(repo, "add", "-f", "-A", ".")
    git(repo, "commit", "-q", "-m", "change")


def tree(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    files = {
        "build/upstream/pins.toml": "core = 'abc'\n",
        "build/install/install.sh": "echo install\n",
        "src/libera/payload/payload.version": 'version = "1.0"\n',
        "components/core/pyproject.toml": 'version = "1.0"\n',
        "components/web/pyproject.toml": (
            '[project]\nversion = "1.0"\n[build-system]\nrequires = ["libera-core==1.0"]\n'
        ),
        "pyproject.toml": (
            '[project]\nversion = "1.0"\n'
            'dependencies = ["libera-core==1.0", "libera-web==1.0"]\n'
        ),
    }
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(text)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.org")
    git(repo, "config", "user.name", "t")
    commit(repo)
    return repo


def test_a_bump_keeps_the_key_and_an_input_changes_it(tmp_path):
    repo = tree(tmp_path)
    first = components.cache_key(repo)
    assert first

    versions.bump(repo, "1.1")
    commit(repo)
    assert components.cache_key(repo) == first

    (repo / "build/install/install.sh").write_text("echo other\n")
    commit(repo)
    assert components.cache_key(repo) == first

    (repo / "build/upstream/pins.toml").write_text("core = 'a later pin'\n")
    commit(repo)
    assert components.cache_key(repo) != first


def test_an_uncommitted_input_is_no_key(tmp_path):
    repo = tree(tmp_path)
    (repo / "build/upstream/pins.toml").write_text("core = 'a later pin'\n")
    assert components.cache_key(repo) is None
