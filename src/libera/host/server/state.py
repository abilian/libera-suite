"""What the host has been asked for, and what it could not answer.

The bottom of the package: counters and sets that both the GET and the POST
side write, and that `build_report` reads back. The regression harness reads
that report instead of a log, which is why this is state rather than logging
-- an assertion needs a value.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libera.host.session import Session

SEEN: dict[str, int] = {}
ERRORS: list[dict] = []
MEDIA_SERVED: set[str] = set()
NOT_FOUND: set[str] = set()
ROUTES: dict[str, int] = {}
NOT_FOUND_CODE = 404


def reset() -> None:
    """Forget what the editor asked for: a new document is starting over."""
    MEDIA_SERVED.clear()
    SEEN.clear()
    ERRORS.clear()


def build_report(session: Session) -> bytes:
    return json.dumps(
        {
            "calls": SEEN,
            "errors": ERRORS,
            # Document media fails *silently* when the host gets it wrong: no
            # request, no console error, just a missing picture. Report what was
            # served so the check can compare it against what the document holds.
            "media_expected": sorted(p.name for p in session.media.glob("*"))
            if session.media.is_dir()
            else [],
            "media_served": sorted(MEDIA_SERVED),
            "not_found": sorted(NOT_FOUND),
            "routes": dict(ROUTES),
        },
        indent=2,
        sort_keys=True,
    ).encode()
