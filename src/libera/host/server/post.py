"""Everything served by POST: the editor asking the host to do something.

Saving, opening, printing, importing media, going fullscreen, reporting a
fault. Above `state` and `get`, below `handler`.
"""

from __future__ import annotations

import base64
import json
import logging
import pathlib
import re
import shutil
from typing import TYPE_CHECKING

from libera.host import apps, desktop, hooks, instance, opening, saving
from libera.host.convert import convert_to_editor_bin
from libera.host.recents import read_recents
from libera.host.server import state
from libera.host.session import NotReadyError

if TYPE_CHECKING:
    from libera.host.server.handler import Handler
    from libera.host.session import Session

logger = logging.getLogger(__name__)


class BadRequestError(ValueError):
    """What the page sent is not what this endpoint reads: a 400."""


def read_json_body(h: Handler) -> dict:
    """The request's JSON object, or a 400.

    Read with `json.loads` at each endpoint, a body that was not an object --
    not JSON, a list, nothing at all -- raised wherever the endpoint first used
    it, and the request closed with no answer.
    """
    try:
        found = json.loads(h.read_body() or b"{}")
    except ValueError as e:
        msg = "the body is not JSON"
        raise BadRequestError(msg) from e
    if not isinstance(found, dict):
        msg = "the body is not a JSON object"
        raise BadRequestError(msg)
    return found


def receive_shot(h: Handler) -> None:
    """The editor's own canvas, captured in the page and posted here.

    Replaces Chromium's --screenshot, which only fires when
    --virtual-time-budget expires and takes the browser down with it.
    """
    if h.session.shot is None:
        h.send_error(404)
        return
    h.session.shot.write_bytes(base64.b64decode(h.read_body()))
    h.send_no_content()


def record_changes(h: Handler) -> None:
    raw = h.read_body().decode()
    q = h.parse_query()
    idx = q.get("index", [""])[0]
    try:
        index = int(idx) if idx else None
        count = int(q.get("count", ["0"])[0])
    except ValueError as e:
        msg = "index and count are numbers"
        raise BadRequestError(msg) from e
    h.session.change_log.record(raw, index, count)
    h.send_no_content()


def save(h: Handler) -> None:
    """Serve LocalFileSave."""
    result = saving.save_document(h.session, read_json_body(h))
    h.send_bytes(json.dumps(result).encode(), "application/json")


def show_open_dialog(h: Handler) -> None:
    """Serve OpenFilenameDialog. With nobody to ask, nothing is chosen."""
    name = h.parse_query().get("filter", [""])[0]
    path = hooks.shell.choose_open_path(name)
    logger.info("open dialog (%s) -> %s", name, path or "cancelled")
    h.send_bytes(json.dumps({"path": path or ""}).encode(), "application/json")


def open_in_window(h: Handler, document: pathlib.Path) -> None:
    """Open a document the way a desktop editor does: in a window of its own.

    Replacing the document in the window that asked would discard whatever is
    open there, unsaved changes included, without asking -- which is what this
    used to do.
    """
    if not hooks.shell.windowed:
        # Nowhere to put a second document: `libera --serve` and the harness
        # have one window and no way to make another.
        try:
            opening.open_document(h.session, document)
        except NotReadyError:
            opened = False
        else:
            opened = True
            state.reset()
        body = json.dumps({"opened": opened, "here": True}).encode()
        h.send_bytes(body, "application/json")
        return

    opened = hooks.shell.open_window(document)
    logger.info("open in a new window: %s", document)
    body = json.dumps({"opened": opened, "here": False}).encode()
    h.send_bytes(body, "application/json")


def take_hand_off(h: Handler) -> None:
    """A second launch giving its documents to this instance.

    The token first: this server is on 127.0.0.1, where any page in any browser
    can POST to it, and opening a file of the caller's choosing is not
    something to do for a web page. See `instance`.
    """
    try:
        body = read_json_body(h)
        token = str(body.get("token", ""))
        documents = [pathlib.Path(d) for d in body.get("documents", [])]
    except (ValueError, TypeError):
        h.send_error(400)
        return
    if not instance.is_own_token(token):
        logger.warning("hand-off refused: wrong token")
        h.send_error(403)
        return
    if not hooks.shell.windowed:
        h.send_bytes(b'{"opened": false}', "application/json")
        return
    for document in documents:
        if document.is_file():
            logger.info("hand-off: %s", document)
            hooks.shell.open_window(document)
        else:
            logger.warning("hand-off: no such file %s", document)
    if not documents:
        hooks.shell.show_start_window()
    # Taken, whether or not each one opened: one that did not has said so on
    # screen, and "not taken" would start a second instance.
    h.send_bytes(b'{"opened": true}', "application/json")


def open_document(h: Handler) -> None:
    """File > Open: pick a document and open it in a new window."""
    path = hooks.shell.choose_open_path("documents")
    if not path:
        logger.info("open document: cancelled")
        h.send_bytes(b'{"opened": false, "here": true}', "application/json")
        return
    open_in_window(h, pathlib.Path(path))


def set_fullscreen(h: Handler) -> None:
    """Slides entering or leaving a demonstration.

    A setter, not a toggle: sdkjs sends true on start and false on end, and a
    toggle drifts out of step the first time either is missed.
    """
    on = h.read_body().decode().strip() == "1"
    hooks.shell.set_fullscreen(on)
    logger.debug("fullscreen -> %s", on)
    h.send_no_content()


def reveal(h: Handler) -> None:
    """File > Open File Location."""
    path = h.session.read_current_document()
    shown = desktop.reveal(path) if path else False
    note = "" if shown else " (nothing to show)"
    logger.info("reveal -> %s%s", path or "no current file", note)
    h.send_no_content()


def open_url(h: Handler) -> None:
    """Open an external link in the user's browser.

    http(s) only: the page must not be able to talk the host into opening a
    file:// URL or anything else the desktop would act on.
    """
    url = h.read_body().decode("utf-8", "replace").strip()
    if not re.match(r"^https?://[^\s]+$", url):
        logger.warning("open-url refused: %r", url[:80])
        h.send_error(400)
        return
    # The page is told nothing either way: there is nothing useful for it to do
    # about the desktop's configuration. desktop.open_url logs the verdict.
    desktop.open_url(url)
    h.send_no_content()


def import_media(h: Handler) -> None:
    """Copy a picked file into the document's media folder, native-style.

    LocalFileGetImageUrl returns the *name* it was stored under, which the
    editor then resolves through the document URL — so the file has to
    actually be in media/ or the image resolves to nothing.
    """
    src = pathlib.Path(h.read_body().decode())
    if not src.is_file():
        h.send_bytes(b'{"name": ""}', "application/json")
        return
    h.session.media.mkdir(parents=True, exist_ok=True)
    name = src.name
    n = 1
    while (h.session.media / name).exists():
        name = f"{src.stem}-{n}{src.suffix}"
        n += 1
    shutil.copyfile(src, h.session.media / name)
    logger.info("media import: %s -> media/%s", src, name)
    h.send_bytes(json.dumps({"name": name}).encode(), "application/json")


def receive_report(h: Handler) -> None:
    report = read_json_body(h)
    for c in report.get("calls", []):
        state.SEEN.setdefault(c["name"], 0)
        state.SEEN[c["name"]] += 1

    events = report.get("events", [])
    for e in events:
        logger.warning("[%s] %s: %s", e["frame"], e["kind"], e["text"])
        state.ERRORS.append(e)

    # The editor's own error dialog and ours are two dialogs for one fault,
    # and the second one is the confusing one. asc_onError means the editor
    # has already said something, so we say nothing and leave the recovery to
    # File > Reload, which is always there.
    editor_spoke = any(e.get("kind") == "asc_onError" for e in events)
    for e in events:
        if e.get("kind") == "error":
            handle_editor_error(h.session, e["text"], quiet=editor_spoke)
    h.send_no_content()


def handle_editor_error(session: Session, message: str, *, quiet: bool = False) -> None:
    """The editor threw where nothing caught it, so its state is a guess.

    Only uncaught errors, not every console.error and not asc_onError: the
    editor reports plenty it has already handled, and a dialog for those would
    train people to dismiss the one that matters.

    `quiet` when the editor is putting up its own dialog about the same fault.
    Two dialogs for one error is what a user called confusing, and they were
    right -- so this stays silent and File > Reload remains the way out.
    """
    if session.reload_offered:
        return
    session.reload_offered = True
    if quiet:
        logger.info("editor error: it is telling the user itself")
        return
    hooks.shell.offer_reload(session, message)


def create_new(h: Handler) -> None:
    """File > New: a blank document, in a window of its own.

    `type` names the editor -- word, cell, slide -- the way the editor's own
    execCommand("create:new", type) sends it, and the way the start window
    asks for a spreadsheet rather than a document. Absent means "the same kind
    as the window that asked", which is what its session already says. Any
    other name is refused: it used to make the window's own kind, quietly.

    The editor's own File > Create New asks for its own kind, and the bridge
    lets the user choose instead (bridge-desktop.js, chooseNewKind), so any
    kind can arrive here from any window.
    """
    wanted = h.parse_query().get("type", [""])[0]
    app = next((a for a in apps.ALL if a.doctype == wanted), None)
    if wanted and app is None:
        h.send_error(400, "no such kind of document")
        return
    blank = h.session.choose_blank(app)
    if not blank.is_file():
        h.send_error(500, explain=f"no blank document at {blank}")
        return
    if hooks.shell.windowed:
        opened = hooks.shell.open_window(None, app)
        logger.info("new document in a new window")
        body = json.dumps({"opened": opened, "here": False}).encode()
        h.send_bytes(body, "application/json")
        return
    if app is not None and app is not h.session.editor:
        # `libera --serve` has this one window, and a document of another kind
        # cannot take the place of the one in it: the page would stay, say, a
        # word processor showing a spreadsheet's blank.
        h.send_error(409, f"A new {app.noun.lower()} needs a window of its own")
        return
    if not convert_to_editor_bin(h.session, blank):
        h.send_error(500, "could not convert the blank document")
        return
    shutil.rmtree(h.session.out_dir, ignore_errors=True)
    state.reset()
    h.send_bytes(b'{"here": true}', "application/json")


def open_recent(h: Handler) -> None:
    """Open a document the editor picked from the Recent list."""
    wanted = str(read_json_body(h).get("id", ""))
    # Only something already in the list: the page must not be able to name an
    # arbitrary path and have the host open it.
    known = {e["path"] for e in read_recents(h.session)}
    if wanted not in known:
        logger.warning("open:recent refused: %r", wanted[:80])
        h.send_error(404)
        return
    open_in_window(h, pathlib.Path(wanted))


def record_abilities(h: Handler) -> None:
    """The editor reporting what it can do: undo, redo.

    Pushed rather than asked for, because a menu is validated on the GUI
    thread and asking the editor from there would deadlock.
    """
    h.session.abilities.update(read_json_body(h))
    h.send_no_content()


def record_modified(h: Handler) -> None:
    h.session.mark_modified(bool(read_json_body(h).get("modified")))
    h.send_no_content()
