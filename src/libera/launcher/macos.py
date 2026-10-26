"""Libera.app in ~/Applications: what puts Libera Suite in Finder's Open With.

A `pip`, `pipx`, `uv tool` or Homebrew install gives a command, and Finder
knows nothing about commands: Open With, a double-clicked document and a Dock
tile named Libera all come from an application bundle, whose Info.plist
declares the document types. This writes one around the interpreter that is
running, the macOS half of `desktop`:

    ~/Applications/Libera.app/Contents/Info.plist
    ~/Applications/Libera.app/Contents/MacOS/Libera
    ~/Applications/Libera.app/Contents/Resources/Libera.icns

**Nothing is compiled here.** The executable and the icon ship prebuilt in the
package (`src/libera/macos/`, rebuilt by `build/macos/launcher.sh`); the
executable links no Python, and loads the library the plist names
(`build/macos/launcher.m`), so writing the plist is all an install has to do.
Nothing is signed either: files this process writes carry no quarantine, so
Gatekeeper never asks, and the linker's ad-hoc signature is all arm64 requires
of an executable.

`build/macos/macos-app.sh` writes its bundles with `write_bundle` too, so the
document types are declared in one place.
"""

from __future__ import annotations

import plistlib
import re
import shutil
import subprocess
import sys
import sysconfig
from importlib import resources
from importlib.metadata import version
from pathlib import Path

APP_ID = "eu.liberasuite.Libera"

LSREGISTER = (
    "/System/Library/Frameworks/CoreServices.framework/Frameworks"
    "/LaunchServices.framework/Support/lsregister"
)

# The macOS half of src/libera/launcher.desktop, and the two are meant to stay
# the same set: one entry per format host/apps.py routes to an editor and the
# system has a name for. This declared Words alone, so macOS never offered to
# open a .xlsx or a .pptx that Libera Suite opens perfectly well -- the Linux
# entry had claimed all three since it was written. Measured both ways against
# NSWorkspace.URLsForApplicationsToOpenURL_: before, .docx yes and .xlsx and
# .pptx no; after, all three.
#
# Every identifier here was read out of the system rather than remembered, by
# asking UTType.typeWithFilenameExtension_ for each extension in apps.py. Two
# of its answers are deliberately not used. "org.libreoffice.visio-document"
# for .vsdx comes from LibreOffice being installed on the machine that asked,
# not from macOS, so claiming it would be claiming another application's type;
# Visio is therefore the one format the .desktop declares and this does not.
# And "com.microsoft.word.doc" is left out with it: .doc opens and cannot be
# saved, so offering to edit one leads somewhere Save does not go.
#
# One entry per editor rather than per format, because Open With shows
# CFBundleTypeName and "Spreadsheet" is more use there than four entries each
# naming one extension. LSHandlerRank Alternate: we claim to handle these, not
# to own them -- taking .docx away from whatever the user already uses would be
# rude for something this early.
DOCUMENT_TYPES = {
    "Word Document": (
        "org.openxmlformats.wordprocessingml.document",
        "org.oasis-open.opendocument.text",
        "public.rtf",
        "public.plain-text",
    ),
    "Spreadsheet": (
        "org.openxmlformats.spreadsheetml.sheet",
        "org.oasis-open.opendocument.spreadsheet",
        "public.comma-separated-values-text",
        "public.tab-separated-values-text",
    ),
    "Presentation": (
        "org.openxmlformats.presentationml.presentation",
        "org.oasis-open.opendocument.presentation",
    ),
}


def explain_unsupported() -> str | None:
    return None


def get_entry_path() -> Path:
    return Path.home() / "Applications" / "Libera.app"


def is_installed() -> bool:
    return (get_entry_path() / "Contents" / "Info.plist").is_file()


def _stable(path: str) -> str:
    """A Homebrew path through `opt/`, which survives an upgrade.

    The interpreter of a Homebrew install is in `Cellar/libera/<version>/`,
    and its library in `Cellar/python@3.x/<version>/`; `brew upgrade` deletes
    both, and the bundle would point at nothing. `opt/<name>` is the link
    Homebrew keeps to whichever version is current.
    """
    return re.sub(r"/Cellar/([^/]+)/[^/]+/", r"/opt/\1/", path, count=1)


def find_python_library() -> str:
    """The library the running interpreter is, for the launcher to load.

    The framework's own binary for a framework build (Homebrew's,
    python.org's), libpythonX.Y.dylib otherwise (uv's). Asked of the
    interpreter, not of python3-config, whose -L names the prefix Homebrew was
    configured with, which need not be this one.
    """
    get = sysconfig.get_config_var
    if get("PYTHONFRAMEWORK"):
        return str(Path(sys.base_prefix) / get("PYTHONFRAMEWORK"))
    return str(Path(get("LIBDIR")) / get("LDLIBRARY"))


def write_bundle(
    app: Path, *, python: str, library: str, min_macos: str | None = None
) -> None:
    """A Libera.app at `app` that runs `python -m libera`.

    `python` and `library` are absolute, or relative to Contents for a bundle
    that carries its own interpreter. `min_macos` is LSMinimumSystemVersion,
    which only a bundle handed to another machine needs.
    """
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True, exist_ok=True)
    (contents / "Resources").mkdir(exist_ok=True)
    package = resources.files("libera") / "macos"
    # Copies, not links into site-packages: an upgrade replaces that directory.
    executable = contents / "MacOS" / "Libera"
    executable.write_bytes((package / "Libera").read_bytes())
    executable.chmod(0o755)
    (contents / "Resources" / "Libera.icns").write_bytes(
        (package / "Libera.icns").read_bytes()
    )
    libera = version("libera")
    plist = {
        "CFBundleName": "Libera",
        "CFBundleDisplayName": "Libera Suite",
        "CFBundleIdentifier": APP_ID,
        "CFBundleExecutable": "Libera",
        "CFBundleIconFile": "Libera.icns",
        "CFBundlePackageType": "APPL",
        # Without NSPrincipalClass, AppKit never finishes launching the
        # application and the open-document event is never delivered.
        "NSPrincipalClass": "NSApplication",
        "CFBundleShortVersionString": libera,
        "CFBundleVersion": libera,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": (
            "Copyright © 2026 Abilian SAS. Includes modified AGPL v3 components"
            " from Euro-Office, a fork of ONLYOFFICE by Ascensio System SIA."
        ),
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": name,
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": list(types),
            }
            for name, types in DOCUMENT_TYPES.items()
        ],
        "LiberaPython": python,
        "LiberaPythonLibrary": library,
    }
    if min_macos:
        plist["LSMinimumSystemVersion"] = min_macos
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(plist, f)


def _register(app: Path, *flags: str) -> None:
    """Tell LaunchServices now, rather than when Finder next looks.

    Best-effort, as `desktop._refresh` is: Finder finds a bundle in
    ~/Applications on its own, only later.
    """
    subprocess.run([LSREGISTER, *flags, str(app)], check=False, capture_output=True)


def install() -> list[Path]:
    """Write the bundle around this interpreter. Returns what was written.

    sys.executable unresolved: for a virtualenv it is the link in the
    environment's bin/, beside the pyvenv.cfg that is how the interpreter
    finds the environment's packages.
    """
    # ponytail: the plist names this interpreter's paths, so a bundle outlives
    # neither an uninstall nor a new Python under the same install; the
    # launcher says so in Console, and --launcher-install again mends it.
    app = get_entry_path()
    if app.exists():
        shutil.rmtree(app)
    write_bundle(
        app,
        python=_stable(sys.executable),
        library=_stable(find_python_library()),
    )
    _register(app, "-f")
    return [app]


def remove() -> list[Path]:
    """Take the bundle away. Returns what was there."""
    app = get_entry_path()
    if not is_installed():
        return []
    _register(app, "-u")
    shutil.rmtree(app)
    return [app]
