"""The Recent list, which outlives any one session.

The editor asks for it through LocalFileRecents and takes the answer through
window.onupdaterecents. Records carry a format id, and Words silently drops
anything outside FILE_DOCUMENT..FILE_PRESENTATION -- so the id has to be right
or the list stays empty with no error.
"""

from __future__ import annotations

import json
import logging
import pathlib

from libera.host import apps
from libera.host.session import H, contains

logger = logging.getLogger(__name__)

# What the editor will accept in its Recent list: for Words, a format id above
# FILE_DOCUMENT and no higher than FILE_PRESENTATION (see matchFileFormat in
# web-apps' Desktop.js). Anything else is silently dropped from the list.
RECENT_LIMIT = 20


def _format_of(document: pathlib.Path) -> int:
    """The id the editor matches this entry against.

    Whichever editor opens the file decides, not the one asking: the list is
    shared and a spreadsheet has to keep its spreadsheet id.
    """
    app = apps.for_document(document)
    return app.by_ext.get(document.suffix.lstrip(".").lower(), app.formats[0][1])


def remember_recent(document: pathlib.Path) -> None:
    """Put a document at the top of the Recent list."""
    # Nothing of ours: the untitled scratch documents and the session state
    # both live under the recents file. Offering those back would be offering
    # the user our own plumbing.
    if contains(H.recents.parent, document):
        return
    entries = [e for e in read_recents() if e["path"] != str(document)]
    entries.insert(
        0,
        {
            "path": str(document),
            "type": _format_of(document),
        },
    )
    H.recents.parent.mkdir(parents=True, exist_ok=True)
    H.recents.write_text(json.dumps(entries[:RECENT_LIMIT], indent=1), encoding="utf-8")


def _is_entry(entry: object) -> bool:
    """A record this module wrote, rather than whatever else the file holds.

    The file outlives the version that wrote it, so a different shape is an
    ordinary state to be in. json.loads accepts every one of them, and
    `e["path"]` is where it finally fails -- which took the whole /__host__/
    request down with it, closing the connection with no response at all. The
    start window then said "Could not load your recent documents: Failed to
    fetch", so an old file on disk read as a network fault.
    """
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("path"), str)
        and isinstance(entry.get("type"), int)
    )


def read_recents() -> list[dict]:
    """The remembered documents that still exist."""
    if not H.recents.is_file():
        return []
    try:
        entries = json.loads(H.recents.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        # An empty Recent list is the right behaviour -- a corrupt file must
        # not stop a menu opening -- but doing it silently means nobody ever
        # finds out the list has stopped working.
        logger.warning("cannot read the recent list at %s: %s", H.recents, e)
        return []
    if not isinstance(entries, list):
        logger.warning("the recent list at %s is not a list", H.recents)
        return []
    usable = [e for e in entries if _is_entry(e)]
    if len(usable) != len(entries):
        logger.warning(
            "ignoring %d entries in %s that this version did not write",
            len(entries) - len(usable),
            H.recents,
        )
    return [e for e in usable if pathlib.Path(e["path"]).is_file()]


def get_recents() -> tuple[bytes, str]:
    """Serve the Recent list in the shape Desktop.js parses.

    id is the path: it comes straight back to us on open, and a path we can
    check against the list is safer than an index into a list that moves.
    """
    body = [
        {"id": e["path"], "path": e["path"], "type": e["type"]} for e in read_recents()
    ]
    return json.dumps(body).encode(), "application/json"
