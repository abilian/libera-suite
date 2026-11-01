"""The core wheel's platform tag, which hatchling cannot know: the binaries
in it are whichever platform's `lb components wheels` put there, and it
names that platform's tag in LIBERA_CORE_TAG."""

from __future__ import annotations

import os
from typing import override

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class PlatformTag(BuildHookInterface):
    @override
    def initialize(self, version: str, build_data: dict) -> None:
        if version == "editable":
            # The workspace's own, from this machine's build: no tag to give.
            return
        build_data["pure_python"] = False
        build_data["tag"] = "py3-none-" + os.environ["LIBERA_CORE_TAG"]
