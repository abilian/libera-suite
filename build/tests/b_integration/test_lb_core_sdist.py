"""libera-core's sdist builds the core away from this repository, so it must
carry everything its build hook imports and runs."""

from __future__ import annotations

import subprocess
import sys
import tarfile

from libera_build.repo import REPO

HOOK_IMPORTS = """
import sys
sys.path[:0] = sys.argv[1:]
from libera_build import components, repo
print(repo.REPO)
"""


def test_the_core_sdist_holds_what_its_hook_needs(tmp_path):
    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(tmp_path), "components/core"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    (sdist,) = tmp_path.glob("libera_core-*.tar.gz")
    with tarfile.open(sdist) as tar:
        assert not [n for n in tar.getnames() if "__pycache__" in n]
        tar.extractall(tmp_path, filter="data")
    root = sdist.with_name(sdist.name.removesuffix(".tar.gz"))

    # What the hook does with the sdist's root: the tooling it puts on the
    # path, and the repository that tooling then finds, which must be the sdist.
    found = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            HOOK_IMPORTS,
            str(root / "build" / "src"),
            str(root / "src"),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert found.stdout.strip() == str(root.resolve())
    for script in ("build.sh", "common.sh", "dist.sh"):
        assert (root / "build" / "engine" / script).is_file()
    assert (root / "build" / "upstream" / "pins.toml").is_file()
    assert sorted((root / "build" / "upstream" / "patches" / "core").iterdir())
