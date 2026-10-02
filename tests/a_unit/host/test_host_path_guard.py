"""The `is_inside` guard in the host's session module.

It answers "may the host serve this file", so it has to keep `..` out while
still working when the served directory is a symlink, which it is whenever a
payload is linked into a build tree. An earlier version compared an unresolved
root against resolved parents and 404'd every font.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from libera.host import session

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def is_inside():
    return session.is_inside


def test_serves_a_file_in_the_directory(is_inside, tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    root.mkdir()
    (root / "000").write_bytes(b"font")
    assert is_inside(root, root / "000")


def test_serves_through_a_symlinked_root(is_inside, tmp_path: Path) -> None:
    real = tmp_path / "payload" / "fonts"
    real.mkdir(parents=True)
    (real / "000").write_bytes(b"font")
    link = tmp_path / "vendor-fonts"
    link.symlink_to(real)
    assert is_inside(link, link / "000")


def test_rejects_traversal_out_of_the_directory(is_inside, tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    root.mkdir()
    (tmp_path / "secret").write_bytes(b"nope")
    assert not is_inside(root, root / ".." / "secret")


def test_rejects_traversal_out_of_a_symlinked_root(is_inside, tmp_path: Path) -> None:
    real = tmp_path / "payload" / "fonts"
    real.mkdir(parents=True)
    (tmp_path / "payload" / "secret").write_bytes(b"nope")
    link = tmp_path / "vendor-fonts"
    link.symlink_to(real)
    assert not is_inside(link, link / ".." / "secret")


def test_rejects_a_directory(is_inside, tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    (root / "sub").mkdir(parents=True)
    assert not is_inside(root, root / "sub")
