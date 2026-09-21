"""Opening a document into a session."""

from __future__ import annotations

import logging
import pathlib
import shutil

from libera.host import hooks
from libera.host.convert import convert_to_editor_bin
from libera.host.recents import remember_recent
from libera.host.session import H, NotReadyError, recoverable

logger = logging.getLogger(__name__)


def open_document(document: pathlib.Path) -> None:
    """Prepare the session for a document, converting it for the editor.

    Converting throws away the previous session, so this is the only moment at
    which edits that never reached the file can still be rescued.
    """
    stale = recoverable(document)
    if stale and hooks.RECOVERY_CHOOSER and hooks.RECOVERY_CHOOSER(document):
        if stale != H.work:
            # The edits are in another window's old session; adopt them.
            shutil.rmtree(H.doc, ignore_errors=True)
            shutil.move(str(stale / "doc"), str(H.doc))
            shutil.copyfile(stale / "unsaved.json", H.unsaved)
            shutil.rmtree(stale, ignore_errors=True)
        logger.info("recovered unsaved changes to %s", document)
        H.current.write_text(str(document), encoding="utf-8")
        remember_recent(document)
        return
    if not convert_to_editor_bin(document):
        msg = f"could not open {document}"
        raise NotReadyError(msg)
    H.current.write_text(str(document), encoding="utf-8")
    H.unsaved.unlink(missing_ok=True)
    remember_recent(document)
