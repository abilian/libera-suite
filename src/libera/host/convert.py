"""x2t: the converter, and everything that decides what it is asked for.

The editor works on Editor.bin plus a log of changes; every document that goes
in or comes out passes through here, for the session it belongs to. Saving is
not the editor's job -- it streams its changes as you type, and `export` turns
them back into a file where `saving` says it goes.
"""

from __future__ import annotations

import csv
import functools
import logging
import pathlib
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from libera.host.session import NotReadyError
from libera.payload import locate

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)


@functools.cache
def read_font_dir(index: pathlib.Path) -> pathlib.Path:
    """The directory of real TTFs, read back from the index built against it.

    An installed payload unpacks them into fonts-src; a dev payload points
    straight at the core-fonts checkout. Neither can be assumed, and the index
    is the one thing that always knows.

    x2t needs the directory as well as the index: given the wrong one,
    GetFontInfoByParams returns NULL and CPdfWriter::GetFontPath dereferences
    it, which is a segfault rather than an error.

    The drive letter is optional because allfontsgen writes Windows paths as
    `C:/...`, forward slashes and all.
    """
    m = re.search(
        r'"((?:[A-Za-z]:)?/[^"]+)/[^/"]+\.(?:ttf|otf|ttc)"',
        index.read_text(encoding="utf-8"),
    )
    if not m:
        msg = f"no font paths in {index}; the payload was never generated"
        raise NotReadyError(msg)
    return pathlib.Path(m.group(1))


def choose_x2t_output(run: subprocess.CompletedProcess) -> str:
    """Whichever stream x2t chose. It is not consistent about which."""
    return run.stdout.strip() or run.stderr.strip()


def run_x2t(session: Session, *args: str) -> subprocess.CompletedProcess:
    """Run x2t out of the payload, in the environment `locate.make_tool_env` gives."""
    logger.debug("x2t %s", " ".join(args))
    return subprocess.run(
        [str(session.x2t), *args],
        capture_output=True,
        text=True,
        check=False,
        env=locate.make_tool_env(session.payload / "bin"),
        creationflags=locate.NO_WINDOW,
    )


# x2t's own ids, from sdkjs's c_oAscEncodings and c_oAscCsvDelimiter.
WINDOWS_1252, UTF_8, UTF_16LE = 44, 46, 48
DELIMITERS = {"\t": 1, ";": 2, ",": 4}
CSV_SUFFIXES = {".csv", ".tsv"}
# Plain text, which x2t writes in the encoding it is told to.
TEXT_SUFFIXES = {*CSV_SUFFIXES, ".txt", ".md"}
# The raw DOCY and XLSY streams the editor opens.
CANVAS_WORD, CANVAS_SPREADSHEET = 8193, 8194
BOM = b"\xef\xbb\xbf"


def is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def write_job(session: Session, name: str, **fields: object) -> pathlib.Path:
    """Write an x2t job file into the session, one element per field."""
    body = "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in fields.items())
    path = session.work / name
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


# x2t's CSV reader drops the text it has read each time it passes this many
# characters, and never looks at the first character after the cut.
X2T_CSV_BLOCK = 500_000
# The characters whose meaning is lost when x2t skips one; and the delimiter.
_LOST_WHEN_SKIPPED = frozenset('"\r\n')
_ASTRAL = re.compile(r"[\U00010000-\U0010ffff]")


def find_misread_rows(path: pathlib.Path) -> list[int]:
    """The rows x2t reads wrongly in this CSV, numbered as the sheet shows them.

    Its reader keeps memory down by dropping the text it has read once it
    passes 500,000 characters, and sets its index to 0 just before the loop
    adds one: the first character after each cut is never looked at. A
    letter there is harmless. A quote, a delimiter or a newline is not: a
    quoted cell splits in two, two cells or two rows merge -- silently, and a
    save writes it. Patch 0029 in build/patches/core fixes x2t, for payload
    0.4; until then, this says where.
    """
    return _walk_like_x2t(*_text_as_x2t_reads_it(path))


def _text_as_x2t_reads_it(path: pathlib.Path) -> tuple[str, str]:
    """The copy write_csv_open_job hands x2t, as x2t indexes it, and the delimiter.

    The byte-order mark and a `sep=` line removed first, as x2t does; and on
    Windows, where x2t's wchar_t is UTF-16, a character outside the BMP counts
    twice, so the cuts land where x2t's do.
    """
    text, _, delimiter = read_csv(path)
    text = text.removeprefix("\ufeff")
    if text.startswith("sep=") and len(text) > len("sep=,\r\n"):
        delimiter, cut = text[4], len("sep=,")
        for _ in range(2):  # x2t takes up to two line-break characters after it
            if text[cut] not in "\r\n":
                break
            cut += 1
        text = text[cut:]
    if sys.platform == "win32":
        text = _ASTRAL.sub("\ue000\ue000", text)
    return text, delimiter


def _walk_like_x2t(text: str, delimiter: str) -> list[int]:
    """CSVReader's loop, skips included, recording each skip that loses meaning.

    The skips have to be reproduced, not only noticed: a quote x2t never saw
    leaves the rest of the cell unquoted, which moves every later boundary,
    and with it the next cut.
    """
    lost = _LOST_WHEN_SKIPPED | {delimiter}
    misread: list[int] = []
    n = len(text)
    base = index = cell = 0  # x2t's buffer start, its nIndex and its nStartCell
    row = 1
    quoted = False
    while base + index < n:
        at = base + index
        char = text[at]
        if char == '"':
            if not quoted and cell == index and at + 1 < n:
                quoted, cell = True, index + 1
            elif quoted and at + 1 < n and text[at + 1] == '"':
                index += 1  # a doubled quote, inside a quoted cell
            elif quoted:
                quoted = False
        elif not quoted and (char == delimiter or char in "\r\n"):
            if char == "\r" and at + 1 < n and text[at + 1] == "\n":
                index, at = index + 1, at + 1
            row += char != delimiter
            if index + 1 > X2T_CSV_BLOCK:
                base, index, cell = at + 1, 1, 0
                if base < n and text[base] in lost:
                    misread.append(row)
                continue
            cell = index + 1
        index += 1
    return misread


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
        m_sFontDir=session.sdkjs_common,
        m_nCsvTxtEncoding=UTF_16LE,
        m_nCsvDelimiter=DELIMITERS[delimiter],
    )


def prepare_txt(session: Session, src: pathlib.Path) -> pathlib.Path:
    """A .txt as x2t reads it to the end.

    Given UTF-8 without a byte-order mark, its reader stops at the first
    character outside the BMP, an emoji say, and a save then writes back only
    what came before it. With the mark it reads the whole file.
    """
    data = src.read_bytes()
    if data.startswith(BOM) or not is_utf8(data):
        return src
    copy = session.work / "open.txt"
    copy.write_bytes(BOM + data)
    return copy


def convert_to_editor_bin(session: Session, src: pathlib.Path) -> bool:
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
            m_sFontDir=session.sdkjs_common,
            m_nCsvTxtEncoding=UTF_8,
        )
        run = run_x2t(session, str(markdown))
    else:
        run = run_x2t(
            session,
            str(prepare_txt(session, src) if suffix == ".txt" else src),
            str(editor_bin),
            str(session.sdkjs_common / "font_selection.bin"),
        )
    if run.returncode != 0 or not editor_bin.is_file():
        logger.error("open failed rc=%s\n%s", run.returncode, choose_x2t_output(run))
        shutil.rmtree(staged, ignore_errors=True)
        return False
    shutil.rmtree(session.doc, ignore_errors=True)
    staged.rename(session.doc)
    return True


def export(
    session: Session, staged: pathlib.Path, fmt: int, like: pathlib.Path | None
) -> bool:
    """Merge Editor.bin and the change log into one file of format `fmt`.

    The contract is desktop-sdk's fileconverter.h: convert from Editor.bin, set
    m_bFromChanges when changes/changes0.json exists, and hand x2t the font
    index it opened with. A CSV is written the way `like`, the file that is
    open, was.
    """
    from_changes = bool(session.change_log)
    options = read_csv_options(staged, like)
    save = write_job(
        session,
        "save.xml",
        m_sFileFrom=session.editor_bin,
        m_sFileTo=staged,
        m_nFormatTo=fmt,
        m_bFromChanges=str(from_changes).lower(),
        m_bDontSaveAdditional="true",
        m_sAllFontsPath=session.all_fonts,
        m_sFontDir=read_font_dir(session.all_fonts),
        **options,
    )
    run = run_x2t(session, str(save))
    if run.returncode != 0 or not staged.is_file():
        logger.error(
            "export failed rc=%s fromChanges=%s\n%s",
            run.returncode,
            from_changes,
            choose_x2t_output(run),
        )
        return False
    # x2t converts text to UTF-8 through a buffer sized one unit per character,
    # and a character outside the BMP, an emoji say, needs two. The conversion
    # fails, x2t falls back to one byte per character, Latin-1 in effect, and
    # exits 0. Only the bytes can tell, and a file that came out like that must
    # not replace the document.
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
        return False
    return True
