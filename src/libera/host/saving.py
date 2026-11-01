"""Saving: what a save request means, and doing the save.

The editor never writes a document. A save converts Editor.bin and the change
log it has streamed into a real file, through x2t, wherever the request says
it goes. That destination has been wrong before, so it is decided in one
place, plan_save, before anything touches the disk.
"""

from __future__ import annotations

import logging
import os
import pathlib
import secrets
import shutil
import tempfile
from dataclasses import dataclass, replace
from enum import IntEnum
from typing import TYPE_CHECKING

from libera.host import apps, convert, desktop, hooks, language, locking
from libera.host.session import is_inside

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)


class SaveOutcome(IntEnum):
    """What DesktopOfflineAppDocumentEndSave is told, as `error`."""

    SAVED = 0
    # Not saved, with nothing to say: the user cancelled, or it is a viewer.
    DECLINED = 1
    FAILED = 2


@dataclass(frozen=True)
class SaveRequest:
    """What the editor asked of a save: a format, 0 for the one the document
    has, and whether it is a Save As or a print.

    Read once from LocalFileSave's body, by `from_body`. The body itself used
    to reach the core as a dict, which a save on close had to fake.
    """

    file_type: int = 0
    save_as: bool = False
    printing: bool = False

    @classmethod
    def from_body(cls, body: dict) -> SaveRequest:
        """Raises TypeError for a format that is not an id."""
        file_type = body.get("fileType") or 0
        if isinstance(file_type, bool) or not isinstance(file_type, int):
            msg = f"fileType is not a format id: {file_type!r}"
            raise TypeError(msg)
        return cls(
            file_type=file_type,
            save_as="saveas=true" in str(body.get("params") or ""),
            printing=bool(body.get("isPrint")),
        )


# A plain Save: the format the document has, where it already is.
PLAIN_SAVE = SaveRequest()


@dataclass(frozen=True)
class Destination:
    """Where a save is going, and in what format.

    `target` is None when nothing is to be copied out of the session before
    asking: a print asks where its PDF goes, every time.
    """

    ext: str
    fmt: int
    target: pathlib.Path | None
    printing: bool
    asks_where: bool

    def to(self, chosen: pathlib.Path, app: apps.App) -> Destination:
        """Where the user chose, in the format its extension names. A print
        stays a PDF, whatever was typed."""
        if self.printing:
            return replace(self, target=chosen)
        ext = chosen.suffix.lstrip(".").lower() or self.ext
        return replace(
            self, target=chosen, ext=ext, fmt=app.ids_by_ext.get(ext, self.fmt)
        )


def plan_save(
    request: SaveRequest,
    app: apps.App,
    open_file: pathlib.Path | None,
    *,
    untitled: bool = False,
    locked: bool = False,
) -> Destination:
    """What the editor's save request means, before anything touches the disk.

    All of the deciding and none of the doing, so the rules -- plain Save
    overwrites what is open, Save As asks, Print has no destination at all --
    can be read in one place and tested without a session, a dialog or x2t.

    Print arrives as a PDF save with isPrint set, which is why it is not simply
    "the user chose PDF". It asks where the PDF goes, every time, starting in
    the document's folder: it went into the session's own directory, where
    no one could find it, and which is swept when the session ends.

    `untitled` is a document File > New made: a copy of a blank in our own
    state directory. It is a real file, so plain Save would overwrite it, and
    did -- "saving" a new document where no one could find it, and out of the
    Recent list, which refuses that directory. Its first save asks where.

    `locked` is a document someone else has open, by their lock file. Its file
    is theirs, so every save asks where, as the editor's locked mode promises:
    "you can make changes and save its local copy later".
    """
    requested = request.file_type
    own = open_file.suffix.lstrip(".").lower() if open_file else ""
    # 0 is what the editor sends for a plain Save, meaning the format the
    # document already has. Read as the editor's first format, it saved an
    # .odt, .ods or .csv as a .docx or .xlsx into the session, said it had
    # saved, and left the file itself as it was.
    if requested == 0 and own in app.ids_by_ext:
        ext, fmt = own, app.ids_by_ext[own]
    else:
        ext, fmt = app.formats.get(requested, app.formats[0])
    printing = request.printing
    # Plain Save overwrites the document that is open -- but only if the format
    # still matches it. Asking for .odt from an open .docx is a Save As whether
    # or not the editor said so.
    keeps_open_file = open_file is not None and own == ext
    # A plain Save of a format x2t cannot write (.doc, .xls) can only go to a
    # new file, so it asks where, as Save As does.
    cannot_keep = requested == 0 and open_file is not None and not keeps_open_file
    return Destination(
        ext=ext,
        fmt=fmt,
        target=None
        if printing or untitled or locked or not keeps_open_file
        else open_file,
        printing=printing,
        asks_where=printing or request.save_as or cannot_keep or untitled or locked,
    )


# What a print offers to save as: the PDF it is about to show, nothing else.
PRINT_FORMATS = (("PDF (.pdf)", "pdf"),)


def _ask_where(
    app: apps.App,
    open_file: pathlib.Path | None,
    ext: str,
    *,
    untitled: bool,
    printing: bool,
) -> pathlib.Path | None:
    """The file the user chose to save to, or None: cancelled, or a file
    someone else has open."""
    suggested = f"{open_file.stem if open_file else 'document'}.{ext}"
    # In the document's own folder, as Save As is in every desktop editor;
    # it started wherever the last save went. Not for an untitled document,
    # whose folder is our state directory: there the toolkit chooses.
    start_in = open_file.parent if open_file is not None and not untitled else None
    formats = tuple(
        (language.translate(label), ext)
        for label, ext in (PRINT_FORMATS if printing else app.save_formats)
    )
    chosen = hooks.shell.choose_save_path(suggested, formats, start_in)
    if not chosen:
        logger.info("save cancelled")
        return None
    target = pathlib.Path(chosen)
    if printing and target.suffix.lower() != ".pdf":
        # A PDF whatever was typed: the viewer is about to be handed it.
        target = target.with_name(f"{target.name}.pdf")
    holder = locking.read_owner(target)
    if holder is not None and not holder.is_us():
        # Overwriting a file someone has open loses their work, or ours.
        hooks.shell.tell(
            language.translate("“{name}” is open somewhere else", name=target.name),
            language.translate(
                "{holder} has had it open since {since}. "
                "Save under another name, or once they have closed it.",
                holder=holder.name,
                since=holder.since,
            ),
        )
        return None
    return target


def replace_document(staged: pathlib.Path, target: pathlib.Path) -> None:
    """Put `staged` at `target` in one step: the old document or the new one.

    Copied over in place, the document was emptied and then filled, so a crash
    or a full disk part way through left a truncated file where the good one
    had been. The copy goes beside it first, under a name of its own, and
    replaces it once whole, keeping the old document's permissions, tags and
    other attributes (desktop.replace_file).

    Through a symlink to the file it names, so the link stays a link. Created
    with the mode a new file gets: mkstemp's 0600 would have made every new
    document private.
    """
    target = target.resolve()
    aside = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
    try:
        with staged.open("rb") as src, aside.open("xb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        desktop.replace_file(aside, target)
    finally:
        aside.unlink(missing_ok=True)


def _put_in_place(
    session: Session,
    staged: pathlib.Path,
    target: pathlib.Path,
    open_file: pathlib.Path | None,
    *,
    printing: bool,
) -> None:
    """Copy the exported file where it was asked for, and follow it if it was
    a Save As."""
    replace_document(staged, target)
    # A print leaves the session on its document: only Save As moves it.
    if target != open_file and not printing:
        # Save As moves the session onto the new file, once there is one.
        # Moved before the export, a failed Save As left the session pointing
        # at a file never written, where the next plain Save then went. The
        # lock moves with it.
        locking.let_go(session)
        session.write_current_document(target)
        locking.hold(session, target)


def save_document(
    session: Session, request: SaveRequest, *, may_ask: bool = True
) -> dict:
    """Export the document where plan_save says it goes.

    Separate from the request so that closing a window can save without one:
    the editor is not involved, because everything needed is already on disk --
    Editor.bin plus the change log the editor has been streaming as you type.

    The error code, a `SaveOutcome`, goes back through
    DesktopOfflineAppDocumentEndSave, with the path of the file written.

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
    plan = plan_save(
        request, app, open_file, untitled=untitled, locked=session.locked_by is not None
    )
    if plan.asks_where and not may_ask:
        logger.error(
            "save refused: .%s needs asking where, and cannot ask here", plan.ext
        )
        return {"error": SaveOutcome.FAILED}
    # With no one to ask -- `--serve`, the harness -- it goes into the session.
    if plan.asks_where and hooks.shell.windowed:
        chosen = _ask_where(
            app, open_file, plan.ext, untitled=untitled, printing=plan.printing
        )
        if chosen is None:
            return {"error": SaveOutcome.DECLINED}
        plan = plan.to(chosen, app)

    final = _export(session, plan, open_file)
    if final is None:
        # convert has logged what x2t said; the editor is told the save failed.
        logger.error("save -> %s FAILED", plan.target or "the session")
        return {"error": SaveOutcome.FAILED}
    logger.info("save -> %s", final)
    if plan.printing:
        # A PDF nothing opens is a print that did not happen. The one the user
        # chose, which outlives the session; the staged copy, headless.
        opened = desktop.open_externally(final)
        return {
            "error": SaveOutcome.SAVED if opened else SaveOutcome.FAILED,
            "path": str(final),
        }
    # The file now matches the editor, so there is nothing to recover.
    session.mark_modified(False)
    return {"error": SaveOutcome.SAVED, "path": str(final)}


def _export(
    session: Session, plan: Destination, open_file: pathlib.Path | None
) -> pathlib.Path | None:
    """Export, then copy out where the plan says: the file the document went
    to, or None when x2t could not write it.

    Into a directory of this save's own first, so a failure never leaves a
    half-written file where the user's document should be. Of its own, because
    every save shared out/saved.<ext>: an export that wrote nothing found the
    last save's file there and passed, and a save on close during a Cmd-S
    wrote the same path.
    """
    session.out_dir.mkdir(exist_ok=True)
    stem = (open_file.stem if open_file else "document") if plan.printing else "saved"
    aside = pathlib.Path(tempfile.mkdtemp(dir=session.out_dir, prefix="save-"))
    staged = aside / f"{stem}.{plan.ext}"
    try:
        convert.export(session, staged, plan.fmt, open_file)
    except convert.ConversionError:
        shutil.rmtree(aside, ignore_errors=True)
        return None
    if plan.target is None:
        return staged
    _put_in_place(session, staged, plan.target, open_file, printing=plan.printing)
    shutil.rmtree(aside, ignore_errors=True)
    return plan.target
