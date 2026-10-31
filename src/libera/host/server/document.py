"""The open document: handing it to the editor, keeping its edits, saving it,
closing its window, and its pictures.

Everything a window's editor asks about the one document it shows.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import pathlib
import shutil
import threading

from libera.host import convert, desktop, hooks, saving
from libera.host.convert import ConversionError
from libera.host.server import diagnostics
from libera.host.server.api import (
    NO_CONTENT,
    Refused,
    Request,
    Response,
    answer_json,
    endpoint,
)
from libera.host.session import is_inside

logger = logging.getLogger(__name__)


@endpoint("GET", "opened")
def serve_opened(r: Request) -> Response:
    """The converted document, Editor.bin, for the editor to open: once the
    conversion its window was opened beside has finished."""
    if r.session.converting is not None:
        r.session.converting.join()
    return _hand_over(r)


def _hand_over(r: Request) -> Response:
    """Editor.bin, or the question of the document's password, which the
    bridge has the editor ask with its own dialog."""
    asked = r.session.password_asked
    if asked is not None:
        return answer_json({"needPassword": asked.code})
    data = r.session.editor_bin.read_bytes()
    opened = {"b64": base64.b64encode(data).decode(), "len": len(data)}
    if r.session.password and r.session.editor.converted:
        # The editor's own is gone after a reload, and its next save, which
        # carries the editor's, would remove the document's protection.
        opened["password"] = r.session.password
    return answer_json(opened)


@endpoint("POST", "password")
def take_password(r: Request) -> Response:
    """The password typed into the editor's dialog: the document converted
    with it, or the question again, when it was wrong (opening.ask_password)."""
    asked = r.session.password_asked
    if asked is None:
        raise Refused(409, "no password was asked for")
    try:
        asked.answer(r.read_field("password", str))
    except ConversionError as e:
        raise Refused(500, str(e)) from e
    return _hand_over(r)


@endpoint("GET", "current")
def serve_current(r: Request) -> Response:
    """The path of the document this window has open."""
    p = r.session.read_current_document()
    reads_itself = not r.session.editor.converted
    # Whether File > Protect is offered: in a format x2t encrypts, so that a
    # password set is one the file gets, and for a PDF, one whose password x2t
    # may change. The editor reads it once, as it loads.
    if reads_itself:
        # Asked as the page loads, while the PDF may still be on its way in.
        if r.session.converting is not None:
            r.session.converting.join()
        protectable = r.session.editor_bin.is_file() and convert.may_change_password(
            r.session.editor_bin
        )
    else:
        protectable = p is None or p.suffix.lower() in convert.ENCRYPTABLE
    return answer_json({
        "path": str(p) if p else "",
        "protectable": protectable,
        "readsItself": reads_itself,
    })


@endpoint("POST", "opening-password")
def take_opening_password(r: Request) -> Response:
    """The password the PDF editor opened its PDF with, "" for none, once it
    is open: the PDF it reads is Editor.bin, which x2t opens with that to
    save it, a save on close included."""
    if r.session.editor.converted:
        raise Refused(409, "this editor opens no file itself")
    password = r.read_field("password", str)
    r.session.opened_with = r.session.password = password
    return NO_CONTENT


@endpoint("GET", "media", prefix=True)
def serve_media(r: Request) -> Response:
    """A picture of the document's, by the name the editor gave it.

    `r.path` is decoded already, by the server, as WSGI does for every path: a
    picture imported as "My Photo.png", asked for as My%20Photo.png, arrives as
    "My Photo.png", and an encoded ".." arrives as ".." for the containment
    check to refuse. Decoding again here would misread a name holding "%".
    """
    f = r.session.media / r.path
    if not is_inside(r.session.media, f):
        raise Refused(404)
    diagnostics.MEDIA_SERVED.add(f.name)
    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    return Response(body=f.read_bytes(), content_type=ctype)


@endpoint("POST", "changes")
def record_changes(r: Request) -> Response:
    raw = r.body.decode()
    idx = r.get_query("index")
    try:
        index = int(idx) if idx else None
        count = int(r.get_query("count", "0"))
    except ValueError as e:
        msg = "index and count are numbers"
        raise Refused(400, msg) from e
    # Not while a save, a close or a reload has x2t reading the log.
    with r.session.lock:
        r.session.change_log.record(raw, index, count)
    return NO_CONTENT


@endpoint("POST", "modified")
def record_modified(r: Request) -> Response:
    """The editor's dirty flag, on every change: kept for recovery, and shown
    on the window as macOS shows an edited document."""
    modified = r.read_field("modified", bool)
    r.session.mark_modified(modified)
    hooks.shell.show_edited(r.session, modified)
    return NO_CONTENT


@endpoint("POST", "save")
def save(r: Request) -> Response:
    """Serve LocalFileSave."""
    try:
        request = saving.SaveRequest.from_body(r.read_json())
    except TypeError as e:
        raise Refused(400, str(e)) from e
    outcome = saving.save_document(r.session, request)
    # Saved as text, the document has no password any more, and the editor
    # would give its own to the next Save As: the bridge takes it away.
    outcome["protected"] = bool(r.session.password)
    if (
        outcome["error"] == saving.SaveOutcome.SAVED
        and convert.rewrites(r.session)
        and hooks.shell.windowed
    ):
        # A PDF whose password File > Protect changed: its Editor.bin is still
        # the file as opened, under the old password, and recovered edits
        # would reopen on it and be saved under that, or under none. Folded
        # and reloaded as File > Reload does, once the editor has its answer;
        # the editor asks for the new password.
        threading.Thread(
            target=hooks.shell.reload, args=(r.session,), daemon=True
        ).start()
    return answer_json(outcome)


@endpoint("POST", "close")
def close_window(r: Request) -> Response:
    """The editor's own File > Close, for the window that asked."""
    hooks.shell.close_window(r.session)
    return NO_CONTENT


@endpoint("POST", "reveal")
def reveal(r: Request) -> Response:
    """File > Open File Location."""
    path = r.session.read_current_document()
    shown = desktop.reveal(path) if path else False
    note = "" if shown else " (nothing to show)"
    logger.info("reveal -> %s%s", path or "no current file", note)
    return NO_CONTENT


@endpoint("POST", "media-import")
def import_media(r: Request) -> Response:
    """Copy a picked file into the document's media folder, native-style.

    LocalFileGetImageUrl returns the *name* it was stored under, which the
    editor then resolves through the document URL, so the file has to
    actually be in media/ or the image resolves to nothing.

    Only a file the shell handed this page: GET media/<name> serves what is
    copied in, so a path of the page's choosing would let any script in our
    origin read any file the user can. The bridge reads a 403 as it reads
    a file that is not there: no name.
    """
    src = pathlib.Path(r.read_field("path", str))
    if src not in r.session.offered:
        logger.warning("media import refused, never offered: %s", src)
        raise Refused(403)
    if not src.is_file():
        return answer_json({"name": ""})
    r.session.media.mkdir(parents=True, exist_ok=True)
    name = src.name
    n = 1
    while (r.session.media / name).exists():
        name = f"{src.stem}-{n}{src.suffix}"
        n += 1
    shutil.copyfile(src, r.session.media / name)
    logger.info("media import: %s -> media/%s", src, name)
    return answer_json({"name": name})
