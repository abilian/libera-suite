"""x2t: the converter, with everything that decides what it is asked for.

The editor works on Editor.bin plus a log of changes; every document that goes
in or comes out passes through here, for the session it belongs to. Saving is
not the editor's job -- it streams its changes as you type, and `export` turns
them back into a file where `saving` says it goes.
"""

from __future__ import annotations

import csv
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from libera.host.changelog import ChangeLog
from libera.payload import locate

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)


def choose_x2t_output(run: subprocess.CompletedProcess) -> str:
    """Whichever stream x2t chose. It is not consistent about which."""
    return run.stdout.strip() or run.stderr.strip()


class ConversionError(RuntimeError):
    """x2t did not write the document it was asked for.

    Raised, not returned: the callers that got a False turned it straight back
    into an exception, under a name that meant something else, and the exit
    status went no further than the log.
    """


# How many x2t may run at once. Each holds tens to hundreds of MB -- 71 MB
# converting a 3 MB docx, 117 MB a 2.9 MB xlsx (measured 2026-10-04) -- and a
# dozen documents opened together started a dozen. The rest wait their turn.
X2T_AT_ONCE = max(2, (os.cpu_count() or 4) // 2)
_X2T_SLOTS = threading.BoundedSemaphore(X2T_AT_ONCE)

# How long one conversion may take. A document that hangs x2t held its slot
# and its request thread for good: the save never answered, and after
# X2T_AT_ONCE of them no conversion ran at all.
# ponytail: one generous limit for every format; per-format limits if a
# legitimate conversion is ever measured near it.
X2T_TIMEOUT = 600


def run_x2t(session: Session, *args: str) -> subprocess.CompletedProcess:
    """Run x2t out of the payload, in the environment `locate.make_tool_env` gives."""
    logger.debug("x2t %s", " ".join(args))
    with _X2T_SLOTS:
        try:
            return subprocess.run(
                [str(session.layout.x2t), *args],
                capture_output=True,
                text=True,
                check=False,
                env=locate.make_tool_env(session.layout.bin),
                creationflags=locate.NO_WINDOW,
                timeout=X2T_TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            msg = f"x2t did not finish in {X2T_TIMEOUT} s"
            raise ConversionError(msg) from e


# x2t's own ids, from sdkjs's c_oAscEncodings and c_oAscCsvDelimiter.
WINDOWS_1252, UTF_8, UTF_16LE = 44, 46, 48
DELIMITERS = {"\t": 1, ";": 2, ",": 4}
CSV_SUFFIXES = {".csv", ".tsv"}
# Plain text, which x2t writes in the encoding it is told to.
TEXT_SUFFIXES = {*CSV_SUFFIXES, ".txt", ".md"}
# The raw DOCY and XLSY streams the editor opens.
CANVAS_WORD, CANVAS_SPREADSHEET = 8193, 8194


def is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def write_job(
    session: Session, name: str, into: pathlib.Path | None = None, **fields: object
) -> pathlib.Path:
    """Write an x2t job file, one element per field, into the session or `into`."""
    body = "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in fields.items())
    path = (into or session.work) / name
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        f"<TaskQueueDataConvert>{body}</TaskQueueDataConvert>",
        encoding="utf-8",
    )
    return path


def read_csv(path: pathlib.Path) -> tuple[str, int, str]:
    """A CSV's text, the x2t id of its encoding, and its delimiter."""
    data = path.read_bytes()
    try:
        text, encoding = data.decode("utf-8"), UTF_8
    except UnicodeDecodeError:
        # ponytail: UTF-8 or Windows-1252 only; the editor's CSV options
        # dialog, if a file in a third encoding turns up.
        text, encoding = data.decode("cp1252", errors="replace"), WINDOWS_1252
    if path.suffix.lower() == ".tsv":
        return text, encoding, "\t"
    try:
        sniffed = csv.Sniffer().sniff(text[:65536], delimiters="".join(DELIMITERS))
    except csv.Error:
        return text, encoding, ","  # one column: no delimiter to find
    return text, encoding, sniffed.delimiter


def read_csv_options(target: pathlib.Path, like: pathlib.Path | None) -> dict[str, int]:
    """How x2t should write `target` if it is a CSV: the way `like` was.

    A save reads the encoding and delimiter off the file that is open, so a
    semicolon file in Windows-1252 stays one. x2t writes whatever delimiter it
    is given, into a TSV as well, so a TSV gets tabs whatever it came from.
    """
    encoding, delimiter = UTF_8, ","
    if like is not None and like.suffix.lower() in CSV_SUFFIXES and like.is_file():
        _, encoding, found = read_csv(like)
        if like.suffix.lower() == target.suffix.lower():
            delimiter = found
    if target.suffix.lower() == ".tsv":
        delimiter = "\t"
    return {"m_nCsvTxtEncoding": encoding, "m_nCsvDelimiter": DELIMITERS[delimiter]}


def write_csv_open_job(
    session: Session, src: pathlib.Path, editor_bin: pathlib.Path
) -> pathlib.Path:
    """The job that opens a CSV, which the three-argument form cannot.

    x2t refuses a CSV without an encoding and a delimiter (rc 88,
    NEED_PARAMS). It gets the text in UTF-16 whatever the file is in, because
    its UTF-8 reader sizes the text by bytes and leaves NULs past the end,
    which it then reads as one more empty row, so each save grew the file by
    one. The UTF-16 reader measures what it converted.
    """
    text, _, delimiter = read_csv(src)
    copy = session.work / f"open{src.suffix.lower()}"
    copy.write_bytes(text.encode("utf-16-le"))
    return write_job(
        session,
        "open.xml",
        m_sFileFrom=copy,
        m_sFileTo=editor_bin,
        m_nFormatTo=CANVAS_SPREADSHEET,
        m_sFontDir=session.font_dir,
        m_nCsvTxtEncoding=UTF_16LE,
        m_nCsvDelimiter=DELIMITERS[delimiter],
    )


def convert_to_editor_bin(session: Session, src: pathlib.Path) -> None:
    """Convert a document into the session's Editor.bin. See `_convert_in`."""
    # It replaces the session's doc/ directory, change log included.
    with session.lock:
        _convert_in(session, src)


def _convert_in(session: Session, src: pathlib.Path) -> None:
    """Convert a document into the session's Editor.bin, via x2t.

    The three-argument form is right here: it writes the raw DOCY stream the
    editor expects. Do not "fix" it into a job file with m_nFormatTo=4097 --
    that is a zipped .docy container, checkStreamSignature() then fails, and
    openDocument() falls through to a branch calling a method that does not
    exist. The raw-stream format id is CANVAS_WORD (8193) if a job file is ever
    needed, as it is for a CSV and for Markdown.

    Into a directory beside the session's, which replaces it only once x2t has
    succeeded. Converting in place deleted the old Editor.bin and change log
    first, so a conversion that failed took the document it was replacing with
    it -- and a reload that could not reopen its own folded edits lost them.
    """
    staged = session.work / "doc.new"
    shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir(parents=True)
    editor_bin = staged / session.editor_bin.name
    suffix = src.suffix.lower()
    if suffix in CSV_SUFFIXES:
        run = run_x2t(session, str(write_csv_open_job(session, src, editor_bin)))
    elif suffix == ".md":
        # Refused without an encoding, like a CSV: rc 88. It had never opened.
        markdown = write_job(
            session,
            "open.xml",
            m_sFileFrom=src,
            m_sFileTo=editor_bin,
            m_nFormatTo=CANVAS_WORD,
            m_sFontDir=session.font_dir,
            m_nCsvTxtEncoding=UTF_8,
        )
        run = run_x2t(session, str(markdown))
    elif suffix == ".xlsb":
        # The three-argument form takes an .xlsb for a presentation and writes
        # an empty one (PPTY), exit 0: no .xlsb ever opened, Excel's included.
        xlsb = write_job(
            session,
            "open.xml",
            m_sFileFrom=src,
            m_sFileTo=editor_bin,
            m_nFormatTo=CANVAS_SPREADSHEET,
            m_sFontDir=session.font_dir,
        )
        run = run_x2t(session, str(xlsb))
    else:
        run = run_x2t(
            session,
            str(src),
            str(editor_bin),
            str(session.font_dir / "font_selection.bin"),
        )
    if run.returncode != 0 or not editor_bin.is_file():
        logger.error("open failed rc=%s\n%s", run.returncode, choose_x2t_output(run))
        shutil.rmtree(staged, ignore_errors=True)
        msg = f"x2t could not convert {src.name} (exit status {run.returncode})"
        raise ConversionError(msg)
    shutil.rmtree(session.doc, ignore_errors=True)
    staged.rename(session.doc)


def export(
    session: Session, staged: pathlib.Path, fmt: int, like: pathlib.Path | None
) -> None:
    """Write the document out as `fmt`, from the session's files as they stand.

    x2t reads the change log the editor is still appending to, so the log is
    read under the session's lock -- but only for as long as copying it takes.
    Held for the whole conversion, it made every edit the editor posted during
    a save wait for it. Since the editor waits for each answer, it froze for
    0.8 s on a 3 MB document, 3.6 s while other windows held the converter
    (measured 2026-10-04). Edits made during the conversion are in the live
    log, for the next save.
    """
    with session.lock:
        snapshot = _take_snapshot(session)
    try:
        _export(session, snapshot, staged, fmt, like)
    finally:
        shutil.rmtree(snapshot, ignore_errors=True)


def _take_snapshot(session: Session) -> pathlib.Path:
    """The session's doc/ as it is now, in a directory of its own.

    Editor.bin and the media are linked, not copied: neither is ever written
    in place -- a new Editor.bin arrives as a new doc/ -- so a link stays what
    it was. The change log is appended to, so it is copied.
    """
    snapshot = pathlib.Path(tempfile.mkdtemp(dir=session.work, prefix="export-"))
    doc = snapshot / "doc"
    shutil.copytree(
        session.doc,
        doc,
        copy_function=_link_or_copy,
        ignore=shutil.ignore_patterns("changes"),
    )
    changes = session.doc / "changes"
    if changes.is_dir():
        shutil.copytree(changes, doc / "changes")
    return snapshot


def _link_or_copy(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError:  # a file system without hard links
        shutil.copy2(src, dst)


def _export(
    session: Session,
    snapshot: pathlib.Path,
    staged: pathlib.Path,
    fmt: int,
    like: pathlib.Path | None,
) -> None:
    """Merge Editor.bin and the change log into one file of format `fmt`.

    The contract is desktop-sdk's fileconverter.h: convert from Editor.bin, set
    m_bFromChanges when changes/changes0.json exists, and hand x2t the font
    index it opened with. A CSV is written the way `like`, the file that is
    open, was.
    """
    doc = snapshot / "doc"
    from_changes = bool(ChangeLog(doc / "changes" / "changes0.json"))
    options = read_csv_options(staged, like)
    save = write_job(
        session,
        "save.xml",
        snapshot,
        m_sFileFrom=doc / "Editor.bin",
        m_sFileTo=staged,
        m_nFormatTo=fmt,
        m_bFromChanges=str(from_changes).lower(),
        m_bDontSaveAdditional="true",
        # The index of filesystem paths. Not the browser's, which holds none:
        # handed that one, x2t fails deep inside sdkjs with "Cannot read
        # property 'length' of null".
        m_sAllFontsPath=session.all_fonts,
        m_sFontDir=session.font_dir,
        **options,
    )
    # Whatever is there already would pass the check below for x2t's output.
    # File > Reload exports to the same name every time, so an export that
    # wrote nothing read the previous reload's file back in, in place of the
    # edits since.
    staged.unlink(missing_ok=True)
    run = run_x2t(session, str(save))
    # A file, and not an empty one: x2t's exit status has said 0 over nothing.
    if run.returncode != 0 or not staged.is_file() or staged.stat().st_size == 0:
        logger.error(
            "export failed rc=%s fromChanges=%s\n%s",
            run.returncode,
            from_changes,
            choose_x2t_output(run),
        )
        msg = f"x2t could not write {staged.name} (exit status {run.returncode})"
        raise ConversionError(msg)
    # x2t converts text to UTF-8 through a buffer sized one unit per character,
    # while a character outside the BMP, an emoji say, needs two. The conversion
    # fails, x2t falls back to one byte per character, Latin-1 in effect, and
    # exits 0. Only the bytes can tell. A file that came out like that must not
    # replace the document.
    if (
        staged.suffix.lower() in TEXT_SUFFIXES
        and options["m_nCsvTxtEncoding"] == UTF_8
        and not is_utf8(staged.read_bytes())
    ):
        logger.error(
            "export failed: x2t wrote %s in something other than UTF-8, which "
            "it does when the text holds a character outside the BMP",
            staged.name,
        )
        msg = f"x2t wrote {staged.name} in something other than UTF-8"
        raise ConversionError(msg)
