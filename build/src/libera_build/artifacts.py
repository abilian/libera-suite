"""What a build produces, by name, and how small is too small to be one.

A size floor because this project keeps meeting the same failure: the artifact
exists, so every check that only stats it passes, and it is a file rather than
a build.
"""

from __future__ import annotations

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


# Where the release keeps what goes to PyPI beside `libera`: on each builder
# under its checkout, and here, all of them together.
PYPI_DIR = "build/out/pypi"
# Where the Flatpak bundles and the Windows installer are brought, here.
BUNDLES_DIR = "build/out/bundles"


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
