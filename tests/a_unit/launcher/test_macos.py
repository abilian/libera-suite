"""Libera.app as `libera --launcher-install` writes it.

What Finder reads is the plist, so that is what is checked; whether the
executable actually starts the interpreter the plist names is the integration
test's question.
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

import pytest

from libera.launcher import macos


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """A throwaway home, and no LaunchServices: nothing here registers."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(macos, "_register", lambda *_: None)
    return tmp_path


def read_plist() -> dict:
    with (macos.get_entry_path() / "Contents" / "Info.plist").open("rb") as f:
        return plistlib.load(f)


@pytest.mark.skipif(sys.platform == "win32", reason="no executable bit on Windows")
def test_it_writes_a_bundle_in_the_users_applications(home):
    assert macos.install() == [home / "Applications" / "Libera.app"]
    contents = home / "Applications" / "Libera.app" / "Contents"
    executable = contents / "MacOS" / "Libera"
    assert executable.read_bytes()[:4] == bytes.fromhex("cafebabe"), "not universal"
    assert executable.stat().st_mode & 0o111
    assert (contents / "Resources" / "Libera.icns").read_bytes()[:4] == b"icns"
    assert macos.is_installed()


def test_the_plist_names_this_interpreter(home):
    """Unresolved: a virtualenv's python is a link, and where the link is
    decides which packages the interpreter finds."""
    macos.install()
    plist = read_plist()
    assert plist["LiberaPython"] == sys.executable
    assert plist["CFBundleExecutable"] == "Libera"
    assert "LSMinimumSystemVersion" not in plist


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="a macOS interpreter's library: Debian's python3 links it statically",
)
def test_the_plist_names_a_library_that_is_there(home):
    macos.install()
    assert Path(read_plist()["LiberaPythonLibrary"]).is_file()


def test_it_offers_to_open_every_kind_and_owns_none(home):
    """Alternate, PDF above all: offered in Open With, never taking PDF from
    the system's viewer, which the owner chose (notes/plans/release-0.7.md)."""
    macos.install()
    kinds = {t["CFBundleTypeName"]: t for t in read_plist()["CFBundleDocumentTypes"]}
    assert set(kinds) == {
        "Word Document",
        "Spreadsheet",
        "Presentation",
        "PDF Document",
    }
    assert {t["LSHandlerRank"] for t in kinds.values()} == {"Alternate"}
    assert kinds["PDF Document"]["LSItemContentTypes"] == ["com.adobe.pdf"]
    assert (
        "org.openxmlformats.spreadsheetml.sheet"
        in (kinds["Spreadsheet"]["LSItemContentTypes"])
    )


def test_a_second_install_replaces_the_first(home):
    macos.install()
    stale = macos.get_entry_path() / "Contents" / "Resources" / "stale"
    stale.write_text("", encoding="utf-8")
    macos.install()
    assert not stale.exists()


def test_remove_takes_it_and_says_so_once(home):
    macos.install()
    assert macos.remove() == [macos.get_entry_path()]
    assert not macos.get_entry_path().exists()
    assert macos.remove() == []


@pytest.mark.parametrize(
    ("given", "kept"),
    [
        (
            "/opt/homebrew/Cellar/libera/0.6.0/libexec/bin/python",
            "/opt/homebrew/opt/libera/libexec/bin/python",
        ),
        (
            "/opt/homebrew/Cellar/python@3.13/3.13.16/Frameworks/Python.framework",
            "/opt/homebrew/opt/python@3.13/Frameworks/Python.framework",
        ),
        (
            "/Users/x/.local/share/uv/tools/libera/bin/python3",
            "/Users/x/.local/share/uv/tools/libera/bin/python3",
        ),
    ],
)
def test_a_homebrew_path_goes_through_opt(given, kept):
    """`brew upgrade` deletes the Cellar directory the bundle would name."""
    assert macos._stable(given) == kept
