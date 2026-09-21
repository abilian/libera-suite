"""The desktop entry: what puts Libera Suite in a Linux launcher.

macOS gets `Libera.app` out of `build/macos-app.sh` -- a Dock icon, a name in
Open With, and a double-clicked document opening in the right editor. A
`pipx install` on Linux got a command and nothing else: nothing in the
activities overview, nothing offering to open a `.docx`, no mark anywhere. The
Flatpak has always shipped a desktop entry, so the gap was exactly the install
that `notes/09-release.md` calls Phase 1 and recommends first.

This writes the same two files the Flatpak installs, into the per-user
locations freedesktop names:

    $XDG_DATA_HOME/applications/eu.liberasuite.Libera.desktop
    $XDG_DATA_HOME/icons/hicolor/scalable/apps/eu.liberasuite.Libera.svg

Per-user and never system-wide: a `pipx` install is one account's, and writing
to /usr/share would need root for something that is not root's.

**`Exec=` is rewritten to an absolute path, and that is the whole reason this
is code rather than two `install` lines.** The committed entry says `libera`,
which is right inside the Flatpak, where `/app/bin` is on PATH before anything
runs. A desktop file launched from a session gets a minimal PATH that usually
does not include `~/.local/bin`, so shipping the template as-is would have
produced an icon that silently does nothing -- the same class of failure as a
launch with no terminal to print to.

Linux only. `why()` says so, rather than each caller testing the platform.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from libera.payload.locate import xdg_data_home

logger = logging.getLogger(__name__)

APP_ID = "eu.liberasuite.Libera"


def why() -> str | None:
    """None when a launcher entry makes sense here; otherwise what to say."""
    if not sys.platform.startswith("linux"):
        return "a desktop entry is a Linux thing; macOS has Libera.app"
    if os.environ.get("FLATPAK_ID"):
        return "the Flatpak installs its own desktop entry"
    return None


def entry_path() -> Path:
    return xdg_data_home() / "applications" / f"{APP_ID}.desktop"


def icon_path() -> Path:
    return xdg_data_home() / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"


def is_installed() -> bool:
    return entry_path().is_file()


def _quote(path: Path) -> str:
    """A path as an Exec= argument.

    The Desktop Entry spec reserves a list of characters and quotes them with
    double quotes and a backslash escape. Only the two that can plausibly be in
    a home directory are handled; anything stranger is left alone rather than
    half-escaped.
    """
    text = str(path)
    if any(c in text for c in ' "'):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _exec_line() -> str:
    """The command the desktop file should run, absolute.

    argv[0] first, because that is the copy the user just invoked and the one
    they mean. `which` second, for a run through `python -m libera`. The
    interpreter last, which is what a checkout with no console script has.
    """
    argv0 = Path(sys.argv[0])
    if argv0.name == "libera" and argv0.is_file():
        return f"{_quote(argv0.resolve())} %F"
    found = shutil.which("libera")
    if found:
        return f"{_quote(Path(found).resolve())} %F"
    return f"{_quote(Path(sys.executable).resolve())} -m libera %F"


def _entry_text() -> str:
    template = (resources.files("libera") / "launcher.desktop").read_text(
        encoding="utf-8"
    )
    out = []
    for line in template.splitlines():
        out.append(f"Exec={_exec_line()}" if line.startswith("Exec=") else line)
    return "\n".join(out) + "\n"


def _refresh(applications: Path) -> None:
    """Tell the desktop that the MIME associations changed.

    Only `update-desktop-database`, which is what builds the mimeinfo.cache the
    Open With menu reads. No `gtk-update-icon-cache`: it wants an index.theme
    in the directory it is pointed at, a per-user hicolor tree usually has
    none, and every desktop tested picks a new SVG up without a cache.

    Best-effort by design. A missing tool or a refusal costs the association
    until the next login, which is not worth failing an install over.
    """
    tool = shutil.which("update-desktop-database")
    if tool is None:
        logger.info("no update-desktop-database; associations apply at next login")
        return
    result = subprocess.run(
        [tool, str(applications)], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.info("update-desktop-database said: %s", result.stderr.strip())


def install() -> list[Path]:
    """Write the entry and the icon. Returns what was written."""
    entry, icon = entry_path(), icon_path()
    for path in (entry, icon):
        path.parent.mkdir(parents=True, exist_ok=True)

    entry.write_text(_entry_text(), encoding="utf-8")
    # Not a symlink into site-packages: an upgrade replaces that directory, and
    # a launcher pointing into the old one is a dangling icon.
    icon.write_bytes((resources.files("libera") / "icon.svg").read_bytes())

    _refresh(entry.parent)
    return [entry, icon]


def remove() -> list[Path]:
    """Take both away. Returns what was there."""
    gone = []
    for path in (entry_path(), icon_path()):
        if path.is_file():
            path.unlink()
            gone.append(path)
    if gone:
        _refresh(entry_path().parent)
    return gone
