"""Finding an installed payload, and saying what one is.

The bottom of the package: everything here answers "where is it, and is it
the right one", and nothing here writes anything.

`install` and `generate` reach these through the module -- `locate.data_dir()`
rather than a bare `data_dir` -- for the same reason `host/hooks.py` is read
that way: a test that replaces `data_dir` replaces it for every caller, not
only for the module that happened to import it first.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import tomllib

PAYLOAD_VERSION = "0.2"


class PayloadError(RuntimeError):
    """Something is wrong with the payload, said in terms a user can act on."""


@dataclass(frozen=True)
class Payload:
    """A usable payload directory, and how we came to be using it."""

    root: Path
    origin: str  # "LIBERA_PAYLOAD", "config", "bundled", or "installed"

    @property
    def bin(self) -> Path:
        return self.root / "bin"

    @property
    def x2t(self) -> Path:
        return self.bin / "x2t"

    def info(self) -> dict:
        f = self.root / "payload.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}


def xdg_data_home() -> Path:
    """`$XDG_DATA_HOME`, or the default the base-directory spec names.

    Here rather than beside its second caller because it is one answer to one
    question, and the two callers ask it about different things: this module
    puts the payload under it, and `launcher` puts the desktop entry and the
    icon in the `applications/` and `icons/` trees the desktop reads.
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) if xdg else Path.home() / ".local" / "share"


def state_dir() -> Path:
    """Everything Libera Suite keeps between runs, per platform convention."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Libera Suite"
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(local) / "Libera Suite"
    return xdg_data_home() / "libera"


def data_dir() -> Path:
    """Where an installed payload lives."""
    return state_dir() / "payload"


def sessions_dir() -> Path:
    """Where per-window state lives, and beside it the Recent list.

    One function because three callers were computing it and one of them spelt
    it `session`. `libera --serve` therefore kept its state -- and wrote its
    recent documents -- in a directory the application never reads, so a
    document opened through the harness never appeared in the start window and
    `--diagnose` could not see its unsaved edits either.

    The Recent list is `Host.recents`, one hop up from a session directory. So
    two commands share a Recent list exactly when their session directories
    share a parent, which is what this is for.
    """
    return state_dir() / "sessions"


def config_file() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if sys.platform == "darwin" and not xdg:
        return state_dir() / "config.toml"
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "libera" / "config.toml"


def _configured_dir() -> Path | None:
    f = config_file()
    if not f.is_file():
        return None
    value = tomllib.loads(f.read_text(encoding="utf-8")).get("payload_dir")
    return Path(value).expanduser() if value else None


def current_platform() -> str:
    system = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(
        platform.system()
    )
    machine = {
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86_64": "x86_64",
        "AMD64": "x86_64",
    }.get(platform.machine())
    if not system or not machine:
        msg = f"unsupported platform: {platform.system()} {platform.machine()}"
        raise PayloadError(msg)
    return f"{system}-{machine}"


def bundled_dir() -> Path | None:
    """A payload shipped inside the application, under the same prefix.

    Every channel that can carry 120 MB should carry it: a Flatpak, and later a
    `.dmg` and the cask. Only PyPI cannot, and that is the one channel where
    fetching on first run earns its complexity. A bundle that downloads its own
    editors on first launch has to ask a question in a window, reach the
    network from a sandbox, and fail in front of somebody who has just
    double-clicked -- all of which the Flatpak did, and one of which it did
    silently.

    **Searched, not counted.** The Flatpak installs the wheel with
    `--prefix=/app` and runs it under the *runtime's* interpreter, so
    `sys.prefix` is `/usr` and says nothing about where the application went.
    Walking up from this file looking for the directory answers the question
    that actually matters -- is there a payload shipped alongside this
    installation -- and it is right for any prefix layout, which is what the
    `.dmg` will want. Counting parents would break the first time the package
    moved; see notes/lessons-learned.md.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "share" / "libera" / "payload"
        if looks_complete(candidate):
            return candidate
    return None


def looks_complete(root: Path) -> bool:
    """Everything the host needs, including what install generates."""
    needed = [
        root / "bin" / "x2t",
        root / "bin" / "DoctRenderer.config",
        root / "sdkjs",
        root / "web-apps",
        root / "empty" / "new.docx",
        root / "AllFonts.js",
        root / "fonts",
    ]
    return all(p.exists() for p in needed)


def resolve() -> Payload:
    """Find the payload. Never downloads: see notes/05-packaging.md."""
    env = os.environ.get("LIBERA_PAYLOAD")
    if env:
        # Taken exactly as given -- this is the development path, pointing at a
        # local build. No version check, so a half-built tree fails loudly here
        # rather than mysteriously later.
        root = Path(env).expanduser()
        if not looks_complete(root):
            msg = (
                f"LIBERA_PAYLOAD={root} is not a complete payload"
                " (run build/payload.sh?)"
            )
            raise PayloadError(msg)
        return Payload(root, "LIBERA_PAYLOAD")

    configured = _configured_dir()
    if configured:
        if not looks_complete(configured):
            msg = (
                f"payload_dir={configured} in {config_file()} is not a complete payload"
            )
            raise PayloadError(msg)
        return Payload(configured, "config")

    # Before the installed one: a bundled payload shipped with this exact
    # application and is guaranteed to match it, where an installed one is
    # whatever some earlier run put there. Both are the same PAYLOAD_VERSION or
    # neither is used at all, so this only decides which of two equals wins --
    # and the one that cannot be half-upgraded should.
    bundled = bundled_dir()
    if bundled is not None:
        return Payload(bundled, "bundled")

    installed = data_dir() / PAYLOAD_VERSION
    if looks_complete(installed):
        return Payload(installed, "installed")

    msg = (
        f"no editor payload found (expected version {PAYLOAD_VERSION}).\n"
        f"  install it:   libera --payload-install\n"
        f"  or point at a local build:   export LIBERA_PAYLOAD=/path/to/out/payload"
    )
    raise PayloadError(msg)
