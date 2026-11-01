"""The prebuilt launcher, run: does it start the interpreter the plist names?

The executable in the package is a binary built once (build/macos/launcher.sh)
and committed, and it is the one part of Libera.app no Python test reads. So
this writes a bundle around the interpreter running the suite and asks it for
the version, the way Finder would start it, minus Finder. Run directly, it
waits half a second for an open-documents event that does not come, then
passes its arguments on.
"""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version

import pytest

from libera.launcher import macos

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="a macOS bundle")


def test_the_bundle_runs_libera(tmp_path):
    app = tmp_path / "Libera.app"
    macos.write_bundle(app, python=sys.executable, library=macos.find_python_library())
    result = subprocess.run(
        [app / "Contents" / "MacOS" / "Libera", "-V"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.stdout.startswith(f"libera {version('libera')}"), result.stderr


def test_a_missing_library_is_said_and_not_crashed_on(tmp_path):
    app = tmp_path / "Libera.app"
    macos.write_bundle(app, python=sys.executable, library=str(tmp_path / "gone"))
    result = subprocess.run(
        [app / "Contents" / "MacOS" / "Libera", "-V"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert "--launcher-install" in result.stderr
