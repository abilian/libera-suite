"""libera-web's files, built with its wheel from the pinned sources: the
editors, their fonts, dictionaries and blanks.

The build needs a core, whose x2t turns the slide themes into what the editor
loads, so libera-core is among this project's build requirements and its x2t
is the one used. `lb components wheels` builds from a copy it has filled
already, and says so in LIBERA_PREBUILT.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import override

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class Editors(BuildHookInterface):
    @override
    def initialize(self, version: str, build_data: dict) -> None:
        self.staged: Path | None = None
        if version == "editable" or os.environ.get("LIBERA_PREBUILT"):
            return
        repo = Path(self.root).parents[1]
        sys.path[:0] = [str(repo / "build" / "src"), str(repo / "src")]
        from libera_build import components

        core = importlib.util.find_spec("libera_core")
        if core is None or core.origin is None:
            msg = "libera-core is not in the build environment"
            raise RuntimeError(msg)
        self.staged = Path(tempfile.mkdtemp(prefix="libera-web-"))
        components.build_web(repo, self.staged, Path(core.origin).parent / "bin")
        build_data["force_include"][str(self.staged)] = "libera_web"

    @override
    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        if self.staged:
            shutil.rmtree(self.staged, ignore_errors=True)
