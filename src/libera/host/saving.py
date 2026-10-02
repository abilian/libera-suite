"""Saving: what a save request means, and carrying it out.

The editor never writes a document. A save converts Editor.bin and the change
log it has streamed into a real file, through x2t, wherever the request says
it goes -- which is the part that has been wrong before, so it is decided in
one place, plan_save, before anything touches the disk.
"""

from __future__ import annotations

import logging
import pathlib
import shutil
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from libera.host import apps, convert, desktop, hooks
from libera.host.session import is_inside

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)


class SaveOutcome(IntEnum):
    """What DesktopOfflineAppDocumentEndSave is told, as `error`."""

    SAVED = 0
    # Not saved, and nothing to say: the user cancelled, or it is a viewer.
    DECLINED = 1
    FAILED = 2


@dataclass(frozen=True)
class Destination:
    """Where a save is going, and in what format.

    `target` is None when nothing is to be copied out of the session -- a
    print, whose file is a means to an end.
    """

    ext: str
    fmt: int
    target: pathlib.Path | None
    printing: bool
    asks_where: bool


def plan_save(
    body: dict,
    app: apps.App,
    open_file: pathlib.Path | None,
    *,
    untitled: bool = False,
) -> Destination:
    """What the editor's save request means, before anything touches the disk.

    All of the deciding and none of the doing, so the rules -- plain Save
    overwrites what is open, Save As asks, Print has no destination at all --
    can be read in one place and tested without a session, a dialog or x2t.

    Print arrives as a PDF save with isPrint set, which is why it is not simply
    "the user chose PDF".

    `untitled` is a document File > New made: a copy of a blank in our own
    state directory. It is a real file, so plain Save would overwrite it, and
    did -- "saving" a new document where nobody could find it, and out of the
    Recent list, which refuses that directory. Its first save asks where.
    """
    requested = body.get("fileType") or 0
    own = open_file.suffix.lstrip(".").lower() if open_file else ""
    # 0 is what the editor sends for a plain Save, and it means the format the
    # document already has. Read as the editor's first format, it saved an
    # .odt, .ods or .csv as a .docx or .xlsx into the session, said it had
    # saved, and left the file itself as it was.
    if requested == 0 and own in app.ids_by_ext:
        ext, fmt = own, app.ids_by_ext[own]
    else:
        ext, fmt = app.formats.get(requested, app.formats[0])
    printing = bool(body.get("isPrint"))
    # Plain Save overwrites the document that is open -- but only if the format
    # still matches it. Asking for .odt from an open .docx is a Save As whether
    # or not the editor said so.
    keeps_open_file = open_file is not None and own == ext
    # A plain Save of a format x2t cannot write (.doc, .xls) has nowhere to go
    # but a new file, so it asks where, as Save As does.
    cannot_keep = requested == 0 and open_file is not None and not keeps_open_file
    return Destination(
        ext=ext,
        fmt=fmt,
        target=None if printing or untitled or not keeps_open_file else open_file,
        printing=printing,
        asks_where=not printing
        and ("saveas=true" in body.get("params", "") or cannot_keep or untitled),
    )


def save_document(session: Session, body: dict, *, may_ask: bool = True) -> dict:
    """Export the document where plan_save says it goes.

    Separate from the request so that closing a window can save without one:
    the editor is not involved, because everything needed is already on disk --
    Editor.bin plus the change log the editor has been streaming as you type.

    The error code, a `SaveOutcome`, goes back through
    DesktopOfflineAppDocumentEndSave.

    `may_ask` is False on the GUI thread, where the save panel would wait for
    itself: a save that needs to ask where fails there instead.
    """
    app = session.editor
    if not app.editable:
        # A viewer has nothing to write and x2t has no id to write it with.
        logger.warning("save refused: %s is a viewer", app.title)
        return {"error": SaveOutcome.DECLINED}

    open_file = session.read_current_document()
    untitled = open_file is not None and is_inside(session.scratch, open_file)
    plan = plan_save(body, app, open_file, untitled=untitled)
    ext, fmt, target, printing = plan.ext, plan.fmt, plan.target, plan.printing

    if plan.asks_where and not may_ask:
        logger.error("save refused: .%s needs asking where, and cannot ask here", ext)
        return {"error": SaveOutcome.FAILED}
    # With nobody to ask -- `--serve`, the harness -- it goes into the session.
    if plan.asks_where and hooks.shell.windowed:
        suggested = f"{open_file.stem if open_file else 'document'}.{ext}"
        # In the document's own folder, as Save As is in every desktop editor;
        # it started wherever the last save went. Not for an untitled document,
        # whose folder is our state directory: there the toolkit chooses.
        start_in = open_file.parent if open_file is not None and not untitled else None
        chosen = hooks.shell.choose_save_path(suggested, app.save_formats, start_in)
        if not chosen:
            logger.info("save cancelled")
            return {"error": SaveOutcome.DECLINED}
        target = pathlib.Path(chosen)
        ext = target.suffix.lstrip(".").lower() or ext
        fmt = app.ids_by_ext.get(ext, fmt)

    session.out_dir.mkdir(exist_ok=True)
    # Convert into the session directory and copy out afterwards, so a failure
    # never leaves a half-written file where the user's document should be.
    stem = (open_file.stem if open_file else "document") if printing else "saved"
    staged = session.out_dir / f"{stem}.{ext}"
    ok = convert.export(session, staged, fmt, open_file)
    if ok and target and target != staged:
        shutil.copyfile(staged, target)
        # Save As moves the session onto the new file -- once there is one.
        # Moved before the export, a failed Save As left the session pointing
        # at a file never written, and the next plain Save went there.
        session.write_current_document(target)
    final = target or staged
    logger.log(
        logging.INFO if ok else logging.ERROR,
        "save -> %s%s",
        final,
        "" if ok else " FAILED",
    )
    if ok and printing:
        # A PDF nothing opens is a print that did not happen.
        ok = desktop.open_externally(staged)
    if ok and not printing:
        # The file now matches the editor, so there is nothing to recover.
        session.mark_modified(False)
    return {
        "error": SaveOutcome.SAVED if ok else SaveOutcome.FAILED,
        "path": str(final),
    }
