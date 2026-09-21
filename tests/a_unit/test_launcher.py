"""An icon that does nothing when clicked is worse than no icon.

That is the failure this module exists to avoid and the one a screenshot
cannot show: a desktop file whose `Exec=` names a command the session's PATH
does not have. The template says `libera`, which is right only inside the
Flatpak, so the rewrite to an absolute path is the part worth pinning down.
"""

from __future__ import annotations

import configparser
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from libera import launcher


@pytest.fixture
def data_home(tmp_path, monkeypatch) -> Path:
    """A throwaway $XDG_DATA_HOME, so nothing here touches the real one."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    return tmp_path


def entry(data_home: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(launcher.entry_path(), encoding="utf-8")
    return parser


def test_it_writes_where_freedesktop_looks(data_home):
    written = launcher.install()
    assert launcher.entry_path() == (
        data_home / "applications" / "eu.liberasuite.Libera.desktop"
    )
    assert launcher.icon_path() == (
        data_home
        / "icons"
        / "hicolor"
        / "scalable"
        / "apps"
        / "eu.liberasuite.Libera.svg"
    )
    assert set(written) == {launcher.entry_path(), launcher.icon_path()}
    assert all(p.is_file() for p in written)
    assert launcher.is_installed()


def test_the_icon_is_a_copy_and_not_a_link(data_home):
    """An upgrade replaces site-packages; a link into it dangles."""
    launcher.install()
    assert not launcher.icon_path().is_symlink()
    assert launcher.icon_path().read_bytes().startswith(b"<")


def test_exec_is_absolute_and_still_takes_files(data_home):
    launcher.install()
    command = entry(data_home)["Desktop Entry"]["Exec"]
    assert command.endswith(" %F"), command
    # Strip the quoting _quote may have added before looking at the path.
    program = command[: -len(" %F")].split(" -m ")[0].strip('"')
    assert Path(program).is_absolute(), command
    assert Path(program).exists(), command


def test_a_path_with_a_space_is_quoted(data_home, monkeypatch, tmp_path):
    odd = tmp_path / "my apps" / "libera"
    odd.parent.mkdir()
    odd.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(odd)])
    launcher.install()
    command = entry(data_home)["Desktop Entry"]["Exec"]
    assert command == f'"{odd}" %F'


def test_nothing_but_exec_is_rewritten(data_home):
    """The template carries the MimeType list, and that is most of its value."""
    launcher.install()
    section = entry(data_home)["Desktop Entry"]
    assert section["Name"] == "Libera Suite"
    assert section["Icon"] == "eu.liberasuite.Libera"
    assert section["Terminal"] == "false"
    types = [t for t in section["MimeType"].split(";") if t]
    assert len(types) > 10
    assert "application/vnd.oasis.opendocument.text" in types


def test_remove_takes_both_and_says_so_once(data_home):
    launcher.install()
    gone = launcher.remove()
    assert set(gone) == {launcher.entry_path(), launcher.icon_path()}
    assert not launcher.is_installed()
    assert launcher.remove() == []


def test_the_flatpak_is_told_not_to(data_home, monkeypatch):
    """It ships its own entry, so writing a second one would shadow it.

    sys.platform is patched because the Mac is where this suite runs and the
    platform check comes first: without it this asserts on the macOS answer
    and proves nothing about the branch it is named for.
    """
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("FLATPAK_ID", "eu.liberasuite.Libera")
    assert "Flatpak" in (launcher.why() or "")


def test_an_ordinary_linux_install_is_told_yes(data_home, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert launcher.why() is None


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="the Linux answer is yes")
def test_it_declines_where_there_is_no_launcher():
    assert launcher.why() is not None


@pytest.mark.skipif(
    shutil.which("desktop-file-validate") is None,
    reason="desktop-file-utils is in the Linux test image and nowhere else",
)
def test_freedesktop_accepts_the_entry(data_home):
    """A faulty desktop file is ignored in silence.

    Nothing reports it: the application simply never appears in the launcher,
    and `Exec` pointing at nothing looks the same from outside as a key
    spelled wrong. So the validator's own words are the assertion, and the
    exit code is only what decides whether to read them.
    """
    launcher.install()
    result = subprocess.run(
        ["desktop-file-validate", str(launcher.entry_path())],
        capture_output=True,
        text=True,
        check=False,
    )
    said = (result.stdout + result.stderr).strip()
    assert "error" not in said.lower(), said
    assert result.returncode == 0, said
