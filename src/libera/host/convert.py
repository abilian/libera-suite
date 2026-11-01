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
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from libera.host import desktop
from libera.host.changelog import ChangeLog
from libera.payload import generate, locate

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


# x2t's exits for a document that needs its password: none was given, or the
# wrong one (CONVERT_DRM and CONVERT_PASSWORD in core's errors.h).
NO_PASSWORD, WRONG_PASSWORD = 90, 91


class PasswordNeededError(ConversionError):
    """The document is protected, and x2t was given no password or the wrong
    one: `code` is its exit, NO_PASSWORD or WRONG_PASSWORD, which the editor's
    own password dialog takes (`asc_initAdvancedOptions`)."""

    def __init__(self, name: str, code: int) -> None:
        super().__init__(f"{name} needs its password (exit status {code})")
        self.code = code


class UnsupportedEncryptionError(ConversionError):
    """The document is protected with an encryption x2t cannot read."""


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

# How much memory one conversion may hold, in RAM or out of it. A 6 KB document
# of nested entities took x2t to 3.9 GB, and a 3 MB archive whose part unpacks
# to 3 GB to 3.1 GB (notes/plans/converter-hardening.md): the laptop swaps
# before the timeout ends it. Whatever x2t falls for next, it costs a refused document.
# The largest legitimate conversion measured, a 200,000-row spreadsheet with a
# formula on each row exported to .ods, held 2.0 GB (2026-10-29, macOS); this
# is a quarter above it.
X2T_MEMORY = 2560 << 20
# How often it is looked at: a spike faster than this overshoots that long.
X2T_WATCH = 0.2


def run_x2t(session: Session, *args: str) -> subprocess.CompletedProcess:
    """Run x2t out of the payload, in the environment `locate.make_tool_env`
    gives, with its code cache in the state folder."""
    logger.debug("x2t %s", " ".join(args))
    env = locate.make_tool_env(session.layout.bin)
    env["DOCTRENDERER_CACHE_DIR"] = str(generate.make_code_cache_dir(session.layout))
    with _X2T_SLOTS:
        return run_watched([str(session.layout.x2t), *args], env)


def run_watched(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    """`argv` to the end, unless it holds more than X2T_MEMORY or runs past
    X2T_TIMEOUT: then it is stopped, and the conversion fails saying which."""
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        creationflags=locate.NO_WINDOW,
    )
    deadline = time.monotonic() + X2T_TIMEOUT
    while True:
        try:
            # Retrying after a timeout loses no output (the subprocess docs).
            out, err = proc.communicate(timeout=X2T_WATCH)
        except subprocess.TimeoutExpired:
            held = desktop.memory_bytes(proc.pid)
            if held > X2T_MEMORY:
                msg = f"x2t held {held >> 20} MB, more than {X2T_MEMORY >> 20} MB"
            elif time.monotonic() > deadline:
                msg = f"x2t did not finish in {X2T_TIMEOUT} s"
            else:
                continue
            proc.kill()
            proc.communicate()
            raise ConversionError(msg) from None
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)


# x2t's own ids, from sdkjs's c_oAscEncodings and c_oAscCsvDelimiter.
WINDOWS_1252, UTF_8, UTF_16LE = 44, 46, 48
DELIMITERS = {"\t": 1, ";": 2, ",": 4}
CSV_SUFFIXES = {".csv", ".tsv"}
# Plain text, which x2t writes in the encoding it is told to.
TEXT_SUFFIXES = {*CSV_SUFFIXES, ".txt", ".md"}
# The raw DOCY, XLSY and PPTY streams the editor opens, by editor, and how
# each stream begins. Diagrams has its own, which the host never names.
CANVAS_WORD, CANVAS_SPREADSHEET, CANVAS_PRESENTATION = 8193, 8194, 8195
CANVASES = {
    "word": CANVAS_WORD,
    "cell": CANVAS_SPREADSHEET,
    "slide": CANVAS_PRESENTATION,
}
SIGNATURES = {"word": b"DOCY", "cell": b"XLSY", "slide": b"PPTY"}


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


# The most a package may say it unpacks to. x2t unpacks a whole .docx, .xlsx or
# .odt to the temporary folder and reads a whole part into memory, with no
# budget: a 4 MB file wrote 4 GB, and a 3 MB one held 3.1 GB
# (notes/plans/converter-hardening.md). The largest legitimate package
# measured says 72 MB: the 200,000-row spreadsheet behind X2T_MEMORY. The
# sizes are the package's own word, and that is enough: x2t's unzip reads a
# part no further than its declared size, so a package that understates them
# unpacks no further either (tests/b_integration/cli/test_hostile_input.py).
PACKAGE_LIMIT = 1 << 30


# What LibreOffice 26 encrypts an OpenDocument file with by default, as its
# manifest names them. x2t reads AES-CBC with PBKDF2 only: given either of
# these, it exits 0 having written nothing, whatever the password
# (notes/plans/release-0.8.md, measured 2026-10-30).
UNREADABLE_ENCRYPTION = (b"aes256-gcm", b"argon2id")


MANIFEST = "META-INF/manifest.xml"


def _check_size(src: pathlib.Path, package: zipfile.ZipFile) -> None:
    total = sum(member.file_size for member in package.infolist())
    if total > PACKAGE_LIMIT:
        msg = (
            f"{src.name} unpacks to {total >> 20} MB,"
            f" more than {PACKAGE_LIMIT >> 20} MB"
        )
        raise ConversionError(msg)


def check_package(src: pathlib.Path) -> None:
    """Refuse a package before x2t starts on it: one that says it unpacks to
    more than PACKAGE_LIMIT, or an OpenDocument file encrypted in a way x2t
    cannot read, which would ask for a password it then cannot use. Anything
    that is not a ZIP package is x2t's."""
    if not zipfile.is_zipfile(src):
        return
    try:
        with zipfile.ZipFile(src) as package:
            # Before reading any part of it, the manifest included.
            _check_size(src, package)
            manifest = package.read(MANIFEST) if MANIFEST in package.namelist() else b""
    except zipfile.BadZipFile:
        # Damaged past what Python reads: x2t, which reads more, decides.
        return
    if any(name in manifest for name in UNREADABLE_ENCRYPTION):
        msg = f"{src.name} is encrypted with AES-GCM or Argon2, which x2t cannot read"
        raise UnsupportedEncryptionError(msg)


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
    check_package(src)
    staged = session.work / "doc.new"
    shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir(parents=True)
    editor_bin = staged / session.editor_bin.name
    suffix = src.suffix.lower()
    if not session.editor.converted:
        # The editor reads the file itself: the bridge hands it over as it is.
        shutil.copyfile(src, editor_bin)
        shutil.rmtree(session.doc, ignore_errors=True)
        staged.rename(session.doc)
        return
    # A protected document's password goes in the job, never on the command
    # line, where any process listing shows it; the job is deleted after.
    secret = {"m_sPassword": session.password} if session.password else {}
    try:
        if suffix in CSV_SUFFIXES:
            run = run_x2t(session, str(write_csv_open_job(session, src, editor_bin)))
        elif suffix in {".md", ".mht", ".fb2", ".epub", ".doc"}:
            # Refused without an encoding, like a CSV: rc 88. None had ever
            # opened, though Words has listed all five since the start, .doc
            # (Word 97-2003) included. An EPUB was probed first, as an archive:
            # nothing it names outside itself is read or written
            # (notes/plans/converter-hardening.md).
            job = write_job(
                session,
                "open.xml",
                session.work,
                m_sFileFrom=src,
                m_sFileTo=editor_bin,
                m_nFormatTo=CANVAS_WORD,
                m_sFontDir=session.font_dir,
                m_nCsvTxtEncoding=UTF_8,
                **secret,
            )
            run = run_x2t(session, str(job))
        elif suffix in {".xlsb", ".fods", ".fodp"} or secret:
            # The three-argument form picks the kind of document itself, and
            # picked wrong for these, exit 0 each time: an .xlsb as an empty
            # presentation (PPTY), so no .xlsb ever opened, Excel's included; a
            # flat ODF spreadsheet or presentation as a text document (DOCY),
            # which then saved as nothing but PDF. The job names the editor's own.
            # It has no place for a password either.
            job = write_job(
                session,
                "open.xml",
                session.work,
                m_sFileFrom=src,
                m_sFileTo=editor_bin,
                m_nFormatTo=CANVASES[session.editor.doctype],
                m_sFontDir=session.font_dir,
                **secret,
            )
            run = run_x2t(session, str(job))
        else:
            run = run_x2t(
                session,
                str(src),
                str(editor_bin),
                str(session.font_dir / "font_selection.bin"),
            )
    finally:
        # On every way out, x2t stopped for its memory or its time included.
        if secret:
            (session.work / "open.xml").unlink(missing_ok=True)
    if run.returncode in {NO_PASSWORD, WRONG_PASSWORD}:
        logger.info("%s asks for its password (rc=%s)", src.name, run.returncode)
        shutil.rmtree(staged, ignore_errors=True)
        raise PasswordNeededError(src.name, run.returncode)
    if run.returncode != 0 or not editor_bin.is_file():
        logger.error("open failed rc=%s\n%s", run.returncode, choose_x2t_output(run))
        shutil.rmtree(staged, ignore_errors=True)
        msg = f"x2t could not convert {src.name} (exit status {run.returncode})"
        raise ConversionError(msg)
    # Another kind of document than the editor's is a wrong guess (above),
    # however it exits: the editor would open it as nothing, or as garbage.
    expected = SIGNATURES.get(session.editor.doctype)
    with editor_bin.open("rb") as stream:
        found = stream.read(4)
    if expected is not None and found != expected:
        shutil.rmtree(staged, ignore_errors=True)
        msg = f"x2t read {src.name} as another kind of document"
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


# What x2t encrypts when given a password (measured 2026-10-30 and 31: every
# OOXML and OpenDocument format the editors write); the rest it writes in
# clear. PDF too, which File > Protect does not offer (server/document.py).
ENCRYPTABLE = frozenset({
    *(".docx", ".docm", ".dotx", ".dotm"),
    *(".xlsx", ".xlsm", ".xltx", ".xltm"),
    *(".pptx", ".pptm", ".ppsx", ".ppsm", ".potx", ".potm"),
    *(".odt", ".ott", ".ods", ".ots", ".odp", ".otp"),
})
# What keeps a protected document's password when saved: those, and a PDF,
# which x2t encrypts too. Text, CSV, TSV, RTF, HTML, Markdown, EPUB and FB2
# have no encryption, and are written in clear.
KEEPS_PASSWORD = ENCRYPTABLE | {".pdf"}


def _passwords(session: Session) -> dict[str, str]:
    """A protected document's password for x2t, to save it under.

    Given none, x2t writes the document unprotected, exit 0, and nothing says
    so. Given one, it encrypts every OOXML and OpenDocument format and PDF,
    and writes the formats that have no encryption, text and CSV among them,
    as they are (measured 2026-10-30): so it goes to every save, and x2t
    decides. A PDF, which x2t opens itself, needs the one it opens with too
    (`Session.opened_with`): given the same twice, x2t appends the changes,
    encrypted as the rest is; given two that differ, it rewrites the whole
    PDF under the new one (`rewrites`), and an empty one removes it.

    The job file holding it is in the export's own directory, which mkdtemp
    makes readable by its owner alone, and which goes when the export does.
    """
    saving = {"m_sSavePassword": session.password} if session.password else {}
    if session.editor.converted or not session.opened_with:
        return saving
    return {"m_sPassword": session.opened_with, **saving}


# Every permission a PDF's /P grants (ISO 32000-2, table 22): print,
# modify, copy, annotate, fill in, extract, assemble, print well.
ALL_PERMITTED = 0b1111_0011_1100
ENCRYPT_REF = re.compile(rb"/Encrypt\s+(\d+)\s+(\d+)\s+R")
# What a PDF may leave in clear: its metadata, or what an Identity crypt
# filter names. x2t's reader decrypts every stream of an encrypted PDF, these
# included, and a change of password writes them out as garbage.
LEFT_IN_CLEAR = re.compile(rb"/EncryptMetadata\s+false|/Identity(?![-\w])")
CRYPT_FILTER = re.compile(rb"/Crypt\b")


def may_change_password(pdf: pathlib.Path) -> bool:
    """Whether File > Protect may give this PDF a password, or change or
    remove its own: x2t then rewrites the whole file.

    Not over a signature, which the rewrite breaks. Nor where the PDF's
    encryption restricts what it permits, printing or copying say: the
    rewrite gives the new password the owner's rights and permits everything
    (measured 2026-10-31), so whoever had the password to open it alone would
    lift its author's restrictions. Nor where it leaves something in clear
    (`LEFT_IN_CLEAR`). An encryption dictionary this cannot read counts as
    restricting.
    """
    # ponytail: read whole, once a window loads; a scan by chunks when a PDF
    # of hundreds of MB makes that slow.
    data = pdf.read_bytes()
    if b"/ByteRange" in data:
        return False
    refs = ENCRYPT_REF.findall(data)
    if not refs:
        return b"/Encrypt" not in data
    # The last: an incremental update may re-encrypt. Never in an object
    # stream (ISO 32000-2, 7.5.7), so in clear.
    num, gen = refs[-1]
    found = re.findall(
        rb"(?<!\d)" + num + rb"\s+" + gen + rb"\s+obj\b(.*?)endobj", data, re.DOTALL
    )
    if not found or LEFT_IN_CLEAR.search(found[-1]) or CRYPT_FILTER.search(data):
        return False
    permits = re.search(rb"/P\s*(-?\d+)", found[-1])
    return (
        permits is not None and int(permits.group(1)) & ALL_PERMITTED == ALL_PERMITTED
    )


def rewrites(session: Session) -> bool:
    """Whether a save of this PDF changes its password: x2t then writes the
    whole file again, where it otherwise appends the changes."""
    return not session.editor.converted and session.opened_with != session.password


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

    A PDF whose password File > Protect changed is saved in two runs: the
    changes appended under the password it opens with, which `_check_pdf_save`
    can judge; then the password alone changed, which writes the whole file
    again. In one run, that rewrite hid a replay that had failed: x2t then
    rewrites the original under the new password, exit 0.
    """
    doc = snapshot / "doc"
    from_changes = bool(ChangeLog(doc / "changes" / "changes0.json"))
    options = read_csv_options(staged, like)
    source = doc / "Editor.bin"
    if not rewrites(session):
        _run_save(
            session,
            snapshot,
            (source, staged),
            from_changes,
            m_nFormatTo=fmt,
            **options,
            **_passwords(session),
        )
        if not session.editor.converted:
            _check_pdf_save(source, staged, from_changes=from_changes)
    else:
        appended = snapshot / "appended.pdf"
        same = session.opened_with
        kept = {"m_sPassword": same, "m_sSavePassword": same} if same else {}
        _run_save(
            session,
            snapshot,
            (source, appended),
            from_changes,
            m_nFormatTo=fmt,
            **options,
            **kept,
        )
        _check_pdf_save(source, appended, from_changes=from_changes)
        _run_save(
            session,
            snapshot,
            (appended, staged),
            False,
            m_nFormatTo=fmt,
            **options,
            **_passwords(session),
        )
        if staged.read_bytes() == appended.read_bytes():
            # What x2t writes when the password it was given does not open the
            # PDF: the file as it was, exit 0.
            logger.error("export failed: x2t kept %s's password", staged.name)
            msg = f"x2t did not change the password of {staged.name}"
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


def _run_save(
    session: Session,
    snapshot: pathlib.Path,
    files: tuple[pathlib.Path, pathlib.Path],
    from_changes: bool,
    **fields: str | int,
) -> None:
    """One run of x2t for a save, from the first of `files` (and the change
    log) to the second; `fields` are the rest of its job, the format and the
    passwords among them."""
    source, staged = files
    save = write_job(
        session,
        f"{staged.stem}.xml",
        snapshot,
        m_sFileFrom=source,
        m_sFileTo=staged,
        m_bFromChanges=str(from_changes).lower(),
        m_bDontSaveAdditional="true",
        # The index of filesystem paths. Not the browser's, which holds none:
        # handed that one, x2t fails deep inside sdkjs with "Cannot read
        # property 'length' of null".
        m_sAllFontsPath=session.all_fonts,
        m_sFontDir=session.font_dir,
        **fields,
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


def _check_pdf_save(
    source: pathlib.Path, staged: pathlib.Path, *, from_changes: bool
) -> None:
    """A PDF is saved by replaying the change log onto the original. When the
    replay fails, x2t writes the original and exits 0: with its script
    missing, before the changes reached the log, on a PDF certified against
    changes (notes/plans/release-0.7.md, item B). A save with changes that
    comes back as the original saved none of them. Every save measured, a
    page removed, added, rotated or moved included, appended the changes to
    the original's bytes; one that rewrote them may have lost what it did not
    rewrite, and a signature over them with it, so it fails too."""
    if not from_changes:
        return
    original, saved = source.read_bytes(), staged.read_bytes()
    if saved == original:
        logger.error("export failed: x2t wrote %s without the changes", staged.name)
        msg = f"x2t saved none of the changes to {staged.name}"
        # The likely reason, when there is one to name: both certified
        # PDFs tried were refused so, whatever their signature permitted.
        if b"/DocMDP" in original:
            msg += ", which carries a certification signature"
        raise ConversionError(msg)
    if not saved.startswith(original):
        logger.error("export failed: x2t rewrote %s", staged.name)
        msg = f"x2t rewrote {staged.name} instead of adding the changes to it"
        raise ConversionError(msg)
