"""The change log: every edit since the document was opened.

The editor never writes a document. It streams its edits here as you type,
and a save merges this log with Editor.bin through x2t. It is also what a
crash leaves behind to recover from.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChangeLog:
    """One session's change log, in the format the C++ host writes.

    The file is a bare comma-separated list of quoted changes, with a trailing
    comma and no brackets -- readers turn that final comma into "]" and
    prepend "[".
    """

    path: Path

    def __bool__(self) -> bool:
        """Whether it holds an edit. The editor flushes with nothing in it."""
        return self.path.is_file() and self.path.stat().st_size > 0

    def record(self, raw: str, index: int | None, count: int) -> None:
        """Take what the editor sent. Three things are load-bearing, and
        getting any of them wrong loses edits silently:

        * append, never rewrite: the editor sends a final flush with count 0,
          and rewriting there throws away everything typed;
        * a count of 0 writes nothing at all;
        * an index below what we already hold means undo, so cut back to that
          change.

        In place, and never rewritten whole. Rewriting it on every keystroke
        -- which this did -- emptied it first and filled it second, so a
        crash in between took every unsaved edit with it. An append that dies
        loses the one change it was adding.
        """
        if not count and not self.path.is_file():
            return
        self.path.parent.mkdir(exist_ok=True)
        if index is not None and self.path.is_file():
            self._rewind(index)
        if count:
            with self.path.open("a", encoding="utf-8") as log_file:
                log_file.write('"' + raw + '",')
        # Every keystroke arrives here, so this is debug or it is noise.
        logger.debug(
            "changes: +%s bytes (index=%s count=%s) -> log %s bytes",
            len(raw),
            index,
            count,
            self.path.stat().st_size if self.path.is_file() else 0,
        )

    def _rewind(self, index: int) -> None:
        """Cut back to the first `index` changes, which is what undo asks.

        Two quote characters per change, so the cut falls on quote 2 * index.
        A log holding no more changes than that is left as it is.
        """
        data = self.path.read_bytes()
        at = -1
        for _ in range(2 * index + 1):
            at = data.find(b'"', at + 1)
            if at == -1:
                return
        os.truncate(self.path, at)
