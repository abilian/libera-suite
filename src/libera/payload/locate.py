"""Finding an installed payload, and saying what one is.

The bottom of the package: everything here answers "where is it, and is it
the right one"; nothing here writes anything.

`install` and `generate` reach these through the module -- `locate.get_data_dir()`
rather than a bare `get_data_dir` -- for the same reason `host/hooks.py` is read
that way: a test that replaces `get_data_dir` replaces it for every caller.
"""

from __future__ import annotations

import functools
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TypeVar

import tomllib

T = TypeVar("T")

# The one definition, beside this module so the wheel and the frozen Windows
# tree include it; the build reads the same file.
PAYLOAD_VERSION: str = tomllib.loads(
    resources
    .files("libera.payload")
    .joinpath("payload.version")
    .read_text(encoding="utf-8")
)["version"]

# The payload's executables are x2t.exe and tools\allfontsgen.exe on Windows.
EXE = ".exe" if os.name == "nt" else ""

# A console program started from a windowed one gets a console window of its
# own on Windows, which flashes up for every conversion: creationflags for
# subprocess, CREATE_NO_WINDOW's value, spelt out so that this module -- which
# runs nothing -- need not import subprocess for one constant.
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def make_tool_env(bin_dir: Path) -> dict[str, str]:
    """The environment to run one of the payload's binaries in.

    They link the libraries beside them in `bin`, and nothing in the binary
    says where those are: Linux and macOS read the two library-path variables,
    and Windows reads PATH. Windows looks beside the executable first, which
    covers x2t, but tools\\allfontsgen.exe sits one level below its DLLs and
    Windows never searches a parent.

    APPLICATION_NAME is what core writes into the <Application> field of saved
    documents; it defaults to ONLYOFFICE and is unrelated to sdkjs's
    COMPANY_NAME.
    """
    env = dict(os.environ)
    env.setdefault("APPLICATION_NAME", "Libera Suite")
    env["DYLD_LIBRARY_PATH"] = str(bin_dir)
    env["LD_LIBRARY_PATH"] = str(bin_dir)
    if os.name == "nt":
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    return env


class PayloadError(RuntimeError):
    """Something is wrong with the payload, said in terms a user can act on."""


class NoPayloadError(PayloadError):
    """There is no payload anywhere `resolve` looks: the one case to offer an install.

    A class of its own so the caller can tell it from the others by type.
    It used to search the message for "no editor payload found", which any
    rewording of the message would have broken without a sound.
    """


@dataclass(frozen=True)
class Layout:
    """Where each part of a payload is: the one place that says. It was
    spelled out in four modules.

    Two roots. `root` holds the editors, their fonts and blanks, which the
    server serves; `core` holds `bin/`, the converter. They are one folder in
    a build tree and in a payload downloaded by 0.6 and earlier, and two
    packages when the components are installed as such: libera_web and
    libera_core.
    """

    root: Path
    core: Path

    @classmethod
    def of(cls, root: Path) -> Layout:
        """The layout of the payload whose editors are at `root`: its own
        `bin/`, unless it is the installed libera_web, whose core is the
        installed libera_core."""
        if root != find_component("libera_web"):
            return cls(root, root)
        core = find_component("libera_core")
        if core is None:
            msg = f"libera-web is installed, in {root}, but not libera-core"
            raise PayloadError(msg)
        return cls(root, core)

    @property
    def bin(self) -> Path:
        return self.core / "bin"

    @property
    def x2t(self) -> Path:
        return self.bin / f"x2t{EXE}"

    @property
    def allfontsgen(self) -> Path:
        return self.bin / "tools" / f"allfontsgen{EXE}"

    @property
    def doctrenderer_config(self) -> Path:
        """Beside x2t, which is where x2t looks for it."""
        return self.bin / "DoctRenderer.config"

    @property
    def sdkjs(self) -> Path:
        return self.root / "sdkjs"

    @property
    def sdkjs_common(self) -> Path:
        return self.sdkjs / "common"

    @property
    def fonts_src(self) -> Path:
        """The fonts as shipped, which allfontsgen reads. Their index is not
        here but in the state folder: see payload/fonts.py."""
        return self.root / "fonts-src"

    @property
    def web_apps(self) -> Path:
        return self.root / "web-apps"

    @property
    def blanks(self) -> Path:
        """The empty documents File > New starts from, one per editor."""
        return self.root / "empty"

    @property
    def record(self) -> Path:
        return self.root / "payload.json"


@dataclass(frozen=True)
class Payload(Layout):
    """A usable payload, and how we came to be using it."""

    # "LIBERA_PAYLOAD", "config", "bundled", "components" or "installed"
    origin: str

    @classmethod
    def found(cls, root: Path, origin: str) -> Payload:
        layout = Layout.of(root)
        return cls(layout.root, layout.core, origin)

    def read_record(self) -> dict:
        """payload.json, or nothing for a build tree. The components' names
        no platform, since libera-web is every platform's: theirs is this
        machine's, which pip chose libera-core for."""
        f = self.record
        record = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
        if self.origin == "components":
            record.setdefault("platform", get_current_platform())
        return record


def get_xdg_data_home() -> Path:
    """`$XDG_DATA_HOME`, or the default the base-directory spec names.

    It lives here, although `launcher` calls it too, because it is one answer
    to one question. The two callers ask it about different things: this
    module puts the payload under it; `launcher` puts the desktop entry and
    the icon in the `applications/` and `icons/` trees the desktop reads.
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) if xdg else Path.home() / ".local" / "share"


def get_state_dir() -> Path:
    """Everything Libera Suite keeps between runs, per platform convention."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Libera Suite"
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(local) / "Libera Suite"
    return get_xdg_data_home() / "libera"


def make_state_dir_private() -> None:
    """Make the state directory this account's alone, creating it if need be.

    It holds a copy of every open document (each session's Editor.bin, its
    edits and its images), the Recent list, and instance.json, whose token is
    the key to the server. Created with the umask, it was 755, or 775 under
    Ubuntu's: readable by every account wherever the home directory lets
    others through, as one made before Ubuntu 21.04 still does. Tightened on
    every launch, so a directory an earlier version made is fixed too; what is
    below it cannot be reached past it. On Windows the mode means nothing: the
    directory is under the user's own profile.
    """
    state = get_state_dir()
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    state.chmod(0o700)


def get_data_dir() -> Path:
    """Where an installed payload lives."""
    return get_state_dir() / "payload"


def get_installed_dir() -> Path:
    """Where `--payload-install` puts this application's payload, and where
    `resolve` looks for it. Three callers used to spell it for themselves."""
    return get_data_dir() / PAYLOAD_VERSION


def get_sessions_dir() -> Path:
    """Where per-window state lives, and beside it the Recent list.

    One function because three callers were computing it and one of them spelt
    it `session`. `libera --serve` therefore kept its state -- and wrote its
    recent documents -- in a directory the application never reads, so a
    document opened through the harness never appeared in the start window and
    `--diagnose` could not see its unsaved edits either.

    The Recent list is `Session.recents`, one hop up from a session directory. So
    two commands share a Recent list exactly when their session directories
    share a parent, which is what this is for.
    """
    return get_state_dir() / "sessions"


def get_named_config() -> Path | None:
    """The configuration named for this run, by `libera --config` (which sets
    LIBERA_CONFIG) or LIBERA_CONFIG itself, in place of the usual file: a
    development setup beside the user's own, which it must not touch."""
    named = os.environ.get("LIBERA_CONFIG")
    return Path(named).expanduser() if named else None


def get_config_file() -> Path:
    named = get_named_config()
    if named is not None:
        return named
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if sys.platform == "darwin" and not xdg:
        return get_state_dir() / "config.toml"
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "libera" / "config.toml"


def read_config_string(key: str) -> str | None:
    """One string from config.toml, or None when the file or the key is absent."""
    return _read_config(key, str, "a string")


def read_config_bool(key: str) -> bool | None:
    """true or false from config.toml, or None when the file or the key is absent."""
    return _read_config(key, bool, "true or false")


def _read_config(key: str, kind: type[T], expected: str) -> T | None:
    """A PayloadError like any other answer from here, so that every command --
    --diagnose, the bug-report one, included -- says which file is wrong,
    with no traceback.
    """
    f = get_config_file()
    if not f.is_file():
        if f == get_named_config():
            # Named and not there is a typo, not "nothing configured".
            msg = f"LIBERA_CONFIG names {f}, which is not a file"
            raise PayloadError(msg)
        return None
    try:
        value = tomllib.loads(f.read_text(encoding="utf-8")).get(key)
    except tomllib.TOMLDecodeError as e:
        msg = f"{f} is not valid TOML: {e}"
        raise PayloadError(msg) from e
    if value is not None and not isinstance(value, kind):
        msg = f"{key} in {f} is not {expected}: {value!r}"
        raise PayloadError(msg)
    return value


def _read_configured_dir() -> Path | None:
    value = read_config_string("payload_dir")
    return Path(value).expanduser() if value else None


def get_current_platform() -> str:
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


def find_bundled_dir() -> Path | None:
    """A payload shipped inside the application, under the same prefix.

    Every channel that can ship 120 MB should ship it: a Flatpak, and later a
    `.dmg` and the cask. Only PyPI cannot, which makes it the one channel where
    fetching on first run earns its complexity. A bundle that downloads its own
    editors on first launch has to ask a question in a window, reach the
    network from a sandbox, and fail in front of somebody who has just
    double-clicked. The Flatpak did all three, one of them silently.

    **Searched, not counted.** The Flatpak installs the wheel with
    `--prefix=/app` and runs it under the *runtime's* interpreter, so
    `sys.prefix` is `/usr` and says nothing about where the application went.
    Walking up from this file looking for the directory answers the question
    that actually matters -- is there a payload shipped alongside this
    installation -- and it is right for any prefix layout, which is what the
    `.dmg` will want. Counting parents would break the first time the package
    moved; see notes/lessons-learned/data-and-paths.md.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "share" / "libera" / "payload"
        if is_complete(candidate):
            return candidate
    return None


@functools.cache
def find_component(package: str) -> Path | None:
    """The folder of an installed component package, without importing it:
    there is nothing in it to run."""
    spec = importlib.util.find_spec(package)
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin).parent


def find_components() -> Payload | None:
    """The components installed as packages, as `pip install libera` brings
    them from 0.7 on: libera-web and libera-core, in exactly this host's
    version, which its own requirements pin."""
    web = find_component("libera_web")
    if web is None:
        return None
    for name in ("libera-web", "libera-core"):
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = None
        if version != PAYLOAD_VERSION:
            there = f"{name} {version} is installed" if version else f"no {name}"
            msg = (
                f"{there}, and this version of Libera Suite needs"
                f" {PAYLOAD_VERSION}\n"
                f"  install it:   pip install {name}=={PAYLOAD_VERSION}"
            )
            raise PayloadError(msg)
    found = Payload.found(web, "components")
    if not is_complete(web):
        msg = f"the components installed in {web.parent} are incomplete"
        raise PayloadError(msg)
    return found


def is_complete(root: Path) -> bool:
    """Everything the host needs, including what install generates.

    The fonts' index is not in it: the host builds that in the state folder
    when it is missing (payload/fonts.py)."""
    layout = Layout.of(root)
    needed = [
        layout.x2t,
        layout.doctrenderer_config,
        layout.sdkjs,
        layout.web_apps,
        layout.blanks / "new.docx",
        layout.fonts_src,
    ]
    return all(p.exists() for p in needed)


def resolve() -> Payload:
    """Find the payload. Never downloads: see notes/05-packaging.md."""
    env = os.environ.get("LIBERA_PAYLOAD")
    if env:
        # Taken exactly as given -- this is the development path, pointing at a
        # local build. No version check; a half-built tree still fails here,
        # before it can fail mysteriously later.
        root = Path(env).expanduser()
        if not is_complete(root):
            msg = (
                f"LIBERA_PAYLOAD={root} is not a complete payload"
                " (run build/engine/payload.sh?)"
            )
            raise PayloadError(msg)
        return Payload.found(root, "LIBERA_PAYLOAD")

    configured = _read_configured_dir()
    if configured:
        if not is_complete(configured):
            msg = (
                f"payload_dir={configured} in {get_config_file()} "
                "is not a complete payload"
            )
            raise PayloadError(msg)
        return Payload.found(configured, "config")

    # Before the installed one: a bundled payload shipped with this exact
    # application and is guaranteed to match it, where an installed one is
    # whatever some earlier run put there. Both are the same PAYLOAD_VERSION or
    # neither is used at all, so this only decides which of two equals wins --
    # and the one that cannot be half-upgraded should.
    bundled = find_bundled_dir()
    if bundled is not None:
        return Payload.found(bundled, "bundled")

    # Before the downloaded one, which an earlier version may have left: these
    # came with this host, pinned to its version.
    components = find_components()
    if components is not None:
        return components

    installed = get_installed_dir()
    if is_complete(installed):
        return Payload.found(installed, "installed")

    msg = (
        f"Libera Suite's components are not installed"
        f" (this version needs {PAYLOAD_VERSION}).\n"
        f"  install it:   libera --payload-install\n"
        f"  or point at a local build:   export LIBERA_PAYLOAD=/path/to/out/payload"
    )
    raise NoPayloadError(msg)
