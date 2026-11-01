"""Old payloads go once nobody has used them for weeks, and no sooner.

The folder is shared by every channel that installs a payload, so a version
this copy does not name may be another copy's: use decides, not the name.
"""

from __future__ import annotations

import os
import time

from libera.payload import locate, prune

NOW = time.time()
DAYS = prune.DAY


def make_version(folder, name, *, used_days_ago=None, installed_days_ago=None):
    root = folder / name
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "x2t").write_bytes(b"x" * 1000)
    for file, days in (
        (prune.MARKER, used_days_ago),
        ("payload.json", installed_days_ago),
    ):
        if days is not None:
            (root / file).touch()
            os.utime(root / file, (NOW - days * DAYS,) * 2)
    return root


def test_a_version_unused_for_four_weeks_goes_and_the_rest_stay(tmp_path):
    make_version(tmp_path, "0.1", used_days_ago=40)
    make_version(tmp_path, "0.4", used_days_ago=3)
    make_version(tmp_path, "0.5", used_days_ago=100)  # this copy's own
    (tmp_path / ".libera-staging-abc").mkdir()
    (tmp_path / "notes").mkdir()

    removed = prune.remove_unused(tmp_path, keep="0.5", now=NOW)

    assert removed == ["0.1 (0 MB)"]
    left = sorted(p.name for p in tmp_path.iterdir())
    assert left == [".libera-staging-abc", "0.4", "0.5", "notes"]


def test_a_version_no_launch_marked_counts_from_its_install(tmp_path):
    """Copies older than 0.5 mark nothing."""
    make_version(tmp_path, "0.2", installed_days_ago=30)
    make_version(tmp_path, "0.3", installed_days_ago=10)

    prune.remove_unused(tmp_path, keep="0.5", now=NOW)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["0.3"]


def test_a_removal_left_halfway_is_finished(tmp_path):
    (tmp_path / f"{prune.REMOVING}0.1-1234abcd" / "bin").mkdir(parents=True)

    prune.remove_unused(tmp_path, keep="0.5", now=NOW)

    assert list(tmp_path.iterdir()) == []


def test_a_launch_marks_an_installed_payload_and_no_other(tmp_path, monkeypatch):
    monkeypatch.setattr(locate, "get_data_dir", lambda: tmp_path / "payload")
    installed = make_version(tmp_path / "payload", "0.5")
    elsewhere = make_version(tmp_path, "build")

    prune.note_use(installed)
    prune.note_use(elsewhere)

    assert (installed / prune.MARKER).is_file()
    assert not (elsewhere / prune.MARKER).exists()
