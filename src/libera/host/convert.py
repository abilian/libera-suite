"""x2t: the converter, and everything that decides what it is asked for.

The editor works on Editor.bin plus a log of changes; every document that goes
in or comes out passes through here. Saving is not the editor's job -- it
streams its changes as you type, and this turns them back into a file.
"""

from __future__ import annotations

import dataclasses
import functools
import logging
import os
import pathlib
import re
import shutil
import subprocess

from libera.host import apps, hooks
from libera.host.desktop import open_externally
from libera.host.session import H, NotReadyError, current_path, set_modified

logger = logging.getLogger(__name__)


@functools.cache
def font_dir(index: pathlib.Path) -> pathlib.Path:
    """The directory of real TTFs, read back from the index built against it.

    An installed payload unpacks them into fonts-src; a dev payload points
    straight at the core-fonts checkout. Neither can be assumed, and the index
    is the one thing that always knows.

    x2t needs the directory as well as the index: given the wrong one,
    GetFontInfoByParams returns NULL and CPdfWriter::GetFontPath dereferences
    it, which is a segfault rather than an error.
    """
    m = re.search(
        r'"(/(?:[^"]+))/[^/"]+\.(?:ttf|otf|ttc)"', index.read_text(encoding="utf-8")
    )
    if not m:
        msg = f"no font paths in {index}; the payload was never generated"
        raise NotReadyError(msg)
    return pathlib.Path(m.group(1))


def x2t_output(run: subprocess.CompletedProcess) -> str:
    """Whichever stream x2t chose. It is not consistent about which."""
    return run.stdout.strip() or run.stderr.strip()


def x2t(*args: str) -> subprocess.CompletedProcess:
    """Run x2t out of the payload.

    APPLICATION_NAME is what core writes into the <Application> field of saved
    documents; it defaults to ONLYOFFICE, and it is not sdkjs's COMPANY_NAME.
    """
    env = dict(os.environ)
    env.setdefault("APPLICATION_NAME", "Libera Suite")
    env["DYLD_LIBRARY_PATH"] = str(H.payload / "bin")
    env["LD_LIBRARY_PATH"] = str(H.payload / "bin")
    logger.debug("x2t %s", " ".join(args))
    return subprocess.run(
        [str(H.x2t), *args], capture_output=True, text=True, check=False, env=env
    )


# allfontsgen --output-web XORs the first 32 bytes of every font with this key,
# so a plain web server cannot hand out usable font files. The *web* loader
# (Externals.js LoadFontArrayBuffer) undoes it; the *desktop* loader
# (Local/common.js) does not, because ascdesktop://fonts/ serves the untouched
# file from disk. We serve the web copies, so we undo it here.
ODTTF_KEY = bytes([
    0xA0,
    0x66,
    0xD6,
    0x20,
    0x14,
    0x96,
    0x47,
    0xFA,
    0x95,
    0x69,
    0xB8,
    0x50,
    0xB0,
    0x41,
    0x49,
    0x48,
])


def convert_to_editor_bin(src: pathlib.Path) -> bool:
    """Convert a document into the session's Editor.bin, via x2t.

    The three-argument form is right here: it writes the raw DOCY stream the
    editor expects. Do not "fix" it into a job file with m_nFormatTo=4097 --
    that is a zipped .docy container, checkStreamSignature() then fails, and
    openDocument() falls through to a branch calling a method that does not
    exist. The raw-stream format id is CANVAS_WORD (8193) if a job file is ever
    needed.
    """
    shutil.rmtree(H.doc, ignore_errors=True)
    H.doc.mkdir(parents=True)
    run = x2t(
        str(src),
        str(H.editor_bin),
        str(H.sdkjs_common / "font_selection.bin"),
    )
    ok = run.returncode == 0 and H.editor_bin.is_file()
    if not ok:
        logger.error("open failed rc=%s\n%s", run.returncode, x2t_output(run))
    return ok


def deobfuscate(data: bytes) -> bytes:
    n = min(32, len(data))
    head = bytes(b ^ ODTTF_KEY[i % 16] for i, b in enumerate(data[:n]))
    return head + data[n:]


def export(staged: pathlib.Path, fmt: int) -> bool:
    """Merge Editor.bin and the change log into one file of format `fmt`.

    The contract is desktop-sdk's fileconverter.h: convert from Editor.bin, set
    m_bFromChanges when changes/changes0.json exists, and hand x2t the font
    index it opened with.
    """
    change_log = H.doc / "changes" / "changes0.json"
    from_changes = change_log.is_file() and change_log.stat().st_size > 0
    job = H.work / "save.xml"
    job.write_text(
        '<?xml version="1.0" encoding="utf-8"?><TaskQueueDataConvert>'
        f"<m_sFileFrom>{H.editor_bin}</m_sFileFrom>"
        f"<m_sFileTo>{staged}</m_sFileTo>"
        f"<m_nFormatTo>{fmt}</m_nFormatTo>"
        f"<m_bFromChanges>{str(from_changes).lower()}</m_bFromChanges>"
        "<m_bDontSaveAdditional>true</m_bDontSaveAdditional>"
        f"<m_sAllFontsPath>{H.all_fonts}</m_sAllFontsPath>"
        f"<m_sFontDir>{font_dir(H.all_fonts)}</m_sFontDir>"
        "<m_nCsvTxtEncoding>46</m_nCsvTxtEncoding><m_nCsvDelimiter>4</m_nCsvDelimiter>"
        "</TaskQueueDataConvert>",
        encoding="utf-8",
    )
    run = x2t(str(job))
    if run.returncode != 0 or not staged.is_file():
        logger.error(
            "export failed rc=%s fromChanges=%s\n%s",
            run.returncode,
            from_changes,
            x2t_output(run),
        )
        return False
    return True


@dataclasses.dataclass(frozen=True)
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


def plan_save(body: dict, app: apps.App, open_file: pathlib.Path | None) -> Destination:
    """What the editor's save request means, before anything touches the disk.

    All of the deciding and none of the doing, so the rules -- plain Save
    overwrites what is open, Save As asks, Print has no destination at all --
    can be read in one place and tested without a session, a dialog or x2t.

    Print arrives as a PDF save with isPrint set, which is why it is not simply
    "the user chose PDF".
    """
    ext, fmt = app.formats.get(body.get("fileType") or 0, app.formats[0])
    printing = bool(body.get("isPrint"))
    # Plain Save overwrites the document that is open -- but only if the format
    # still matches it. Asking for .odt from an open .docx is a Save As whether
    # or not the editor said so.
    keeps_open_file = open_file is not None and open_file.suffix == f".{ext}"
    return Destination(
        ext=ext,
        fmt=fmt,
        target=None if printing or not keeps_open_file else open_file,
        printing=printing,
        asks_where=not printing and "saveas=true" in body.get("params", ""),
    )


def save_document(body: dict) -> dict:
    """Export the document where plan_save says it goes.

    Separate from the request so that closing a window can save without one:
    the editor is not involved, because everything needed is already on disk --
    Editor.bin plus the change log the editor has been streaming as you type.

    Error codes go back through DesktopOfflineAppDocumentEndSave: 0 saved,
    1 not saved but say nothing (the user cancelled), 2 save failed.
    """
    app = H.editor
    if not app.editable:
        # A viewer has nothing to write and x2t has no id to write it with.
        logger.warning("save refused: %s is a viewer", app.title)
        return {"error": 1}

    open_file = current_path()
    plan = plan_save(body, app, open_file)
    ext, fmt, target, printing = plan.ext, plan.fmt, plan.target, plan.printing

    if plan.asks_where and hooks.SAVE_PATH_CHOOSER:
        suggested = open_file.name if open_file else f"document.{ext}"
        chosen = hooks.SAVE_PATH_CHOOSER(suggested)
        if not chosen:
            logger.info("save cancelled")
            return {"error": 1}
        target = pathlib.Path(chosen)
        ext = target.suffix.lstrip(".").lower() or ext
        fmt = app.by_ext.get(ext, fmt)
        H.current.write_text(str(target), encoding="utf-8")

    H.out.mkdir(exist_ok=True)
    # Convert into the session directory and copy out afterwards, so a failure
    # never leaves a half-written file where the user's document should be.
    stem = (open_file.stem if open_file else "document") if printing else "saved"
    staged = H.out / f"{stem}.{ext}"
    ok = export(staged, fmt)
    if ok and target and target != staged:
        shutil.copyfile(staged, target)
    final = target or staged
    logger.log(
        logging.INFO if ok else logging.ERROR,
        "save -> %s%s",
        final,
        "" if ok else " FAILED",
    )
    if ok and printing:
        open_externally(staged)
    if ok and not printing:
        # The file now matches the editor, so there is nothing to recover.
        set_modified(False)
    return {"error": 0 if ok else 2, "path": str(final)}


def save_changes(raw: str, index: int | None, count: int) -> None:
    """Append to the change log the way the C++ host does.

    The file is a bare comma-separated list of quoted changes, with a
    trailing comma and no brackets -- readers turn that final comma into
    "]" and prepend "[". Three things are load-bearing, and getting any of
    them wrong loses edits silently:

    * append, never rewrite: the editor sends a final flush with count 0,
      and rewriting there throws away everything typed;
    * a count of 0 writes nothing at all;
    * an index below what we already hold means undo, so truncate back to
      that change (two quote characters per change).
    """
    f = H.doc / "changes" / "changes0.json"
    if not count and not f.is_file():
        return
    f.parent.mkdir(exist_ok=True)
    text = f.read_text(encoding="utf-8") if f.is_file() else ""

    if index is not None and index * 2 < text.count('"'):
        seen = 0
        for i, ch in enumerate(text):
            if ch == '"':
                if seen == index * 2:
                    text = text[:i]
                    break
                seen += 1

    if count:
        text += '"' + raw + '",'
    f.write_text(text, encoding="utf-8")
    # Every keystroke arrives here, so this is debug or it is noise.
    logger.debug(
        "changes: +%s bytes (index=%s count=%s) -> log %s bytes",
        len(raw),
        index,
        count,
        len(text),
    )
