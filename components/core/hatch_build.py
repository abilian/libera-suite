"""libera-core's files, made with its wheel: x2t, allfontsgen and their
libraries, for the platform it is built on, and the platform's tag, which
hatchling cannot know.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import override

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class Core(BuildHookInterface):
    @override
    def initialize(self, version: str, build_data: dict) -> None:
        self.staged: Path | None = None
        if version == "editable":
            return
        build_data["pure_python"] = False
        # An sdist carries the repository's build files at their own paths.
        repo = Path(self.root)
        if not (repo / "build").is_dir():
            repo = repo.parents[1]
        sys.path[:0] = [str(repo / "build" / "src"), str(repo / "src")]
        from libera_build import components

        self.staged = Path(tempfile.mkdtemp(prefix="libera-core-"))
        package = self.staged / "libera_core"
        package.mkdir()
        platform = components.build_core(repo, package)
        build_data["tag"] = "py3-none-" + components.TAGS[platform]
        build_data["force_include"][str(package / "bin")] = "libera_core/bin"

    @override
    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        if self.staged:
            shutil.rmtree(self.staged, ignore_errors=True)
