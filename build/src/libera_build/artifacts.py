"""What a build produces, by name, and how small is too small to be one.

A size floor because this project keeps meeting the same failure: the artifact
exists, so every check that only stats it passes, and it is a file rather than
a build.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from libera_build import repo

if TYPE_CHECKING:
    from pathlib import Path

# A core tarball is tens of megabytes.
MIN_CORE_BYTES = 10 * 1024 * 1024

# A bundle carries the application, the payload and the wheels; the amd64 one
# measured 81 MB. The same argument as MIN_CORE_BYTES, one order down.
MIN_BUNDLE_BYTES = 20 * 1024 * 1024


def core_name(platform: str) -> str:
    """core-<platform>.tar.gz, under the *payload* version's directory."""
    return f"core-{platform}.tar.gz"


def bundle_name(app_version: str, arch: str) -> str:
    """The Flatpak bundle, named for the *application* version."""
    return f"libera-{app_version}-{arch}.flatpak"


def installer_name(app_version: str) -> str:
    """The Windows installer, named for the *application* version too."""
    return f"Libera-Suite-Setup-{app_version}.exe"


def size_problem(platform: str, name: str, size: int, minimum: int) -> str | None:
    if size < minimum:
        return f"{platform}: {name} is {size} bytes, which is not an artifact."
    return None


# Where a builder leaves, under its checkout, what goes to PyPI beside
# `libera`, and where the Windows installer is made.
PYPI_DIR = "build/out/pypi"
BUNDLES_DIR = "build/out/bundles"

RELEASE_DIR = "build/out/release"


def run_dir(root: Path) -> Path:
    """build/out/release/<commit>/: everything a release run gathers here, from
    this machine and the builders, and stages. Named by the commit, so a run
    can read nothing another commit made: a libera-core wheel or a bundle left
    by an earlier run of the same version used to stage as this one's."""
    return root / RELEASE_DIR / repo.head(root)


def run_pypi(root: Path) -> Path:
    """Every file of the release that goes to PyPI: the components and libera."""
    return run_dir(root) / "pypi"


def run_bundles(root: Path) -> Path:
    """The Flatpak bundles and the Windows installer, brought from the builders."""
    return run_dir(root) / "bundles"


def app_wheel_name(app_version: str) -> str:
    """libera's own wheel."""
    return f"libera-{app_version}-py3-none-any.whl"


def core_wheel_name(payload_version: str, tag: str) -> str:
    """libera-core's wheel for one platform, by its platform tag."""
    return f"libera_core-{payload_version}-py3-none-{tag}.whl"


def core_sdist_name(payload_version: str) -> str:
    """libera-core's source, which pip builds where PyPI has no wheel."""
    return f"libera_core-{payload_version}.tar.gz"


def web_wheel_name(payload_version: str) -> str:
    """libera-web's wheel, the same on every platform."""
    return f"libera_web-{payload_version}-py3-none-any.whl"
