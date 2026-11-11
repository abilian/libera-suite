"""The three verbs, as `lb release <verb>` and `ship`'s phases call them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera_build.origin import place, publish, status
from libera_build.repo import REPO
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class OriginOptions:
    verb: str
    dry_run: bool = False
    root: Path = REPO


def run(options: OriginOptions) -> int:
    root, dry = options.root, options.dry_run
    where = place.here(root)
    if options.verb == "status":
        status.status(root)
    elif options.verb == "extras":
        publish.extras(root, where, dry=dry)
    elif options.verb == "windows":
        publish.windows(root, where, dry=dry)
    else:
        msg = f"no such verb: {options.verb}"
        raise RefusedError(msg)
    return 0
