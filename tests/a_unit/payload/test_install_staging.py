"""The install stages beside its destination, and refuses before downloading.

Both came from one real failure on an arm64 machine whose /tmp is a separate,
small filesystem. Staging in /tmp made `shutil.move` fall back to `copytree`,
which needs the payload's size twice, is not atomic, and -- when it ran out of
room a hundred megabytes in -- left a half-populated payload where the working
one had been.
"""

from __future__ import annotations

import shutil

import pytest

from libera.payload import PayloadError, installer


def test_room_check_refuses_when_the_disk_is_too_small(tmp_path, monkeypatch):
    """A number the manifest already knows, checked before the first byte."""
    artifacts = [{"size": 68_000_000}, {"size": 45_000_000}]
    monkeypatch.setattr(
        shutil, "disk_usage", lambda _p: shutil._ntuple_diskusage(0, 0, 50_000_000)
    )
    with pytest.raises(PayloadError) as e:
        installer._check_room(tmp_path, artifacts)
    # Both numbers, and the unpacked estimate: a refusal that says only "not
    # enough room" leaves the reader to guess how much to free.
    message = str(e.value)
    assert "not enough room" in message
    assert "226 MB" in message, "says what it needs"
    assert "50 MB" in message, "says what is there"
    assert "170 MB" in message, "says what the payload unpacks to"


def test_room_check_passes_with_headroom(tmp_path, monkeypatch):
    artifacts = [{"size": 10_000_000}]
    monkeypatch.setattr(
        shutil, "disk_usage", lambda _p: shutil._ntuple_diskusage(0, 0, 999_000_000)
    )
    installer._check_room(tmp_path, artifacts)  # no exception


def test_staging_happens_on_the_destination_filesystem():
    """The staging directory is created with dir=dest.parent.

    Asserted on the source because the alternative is a test that needs two
    filesystems. The defect was one keyword argument absent, and its absence is
    what this reads.
    """
    import inspect

    source = inspect.getsource(installer.install)
    assert "dir=dest.parent" in source
    assert "staged.rename(dest)" in source, "the move must be a same-filesystem rename"
