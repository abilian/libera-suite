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

from libera.host import apps, desktop, hooks
from libera.host.convert import convert_to_editor_bin, save_changes, save_document
from libera.host.desktop import reveal
from libera.host.recents import read_recents, remember_recent
from libera.host.server import state
from libera.host.session import (
    EDITOR_STATE,
    H,
    current_path,
    current_session,
    set_modified,
)

if TYPE_CHECKING:
    from libera.host.server.handler import Handler

logger = logging.getLogger(__name__)


def post_shot(h: Handler) -> None:
    """The editor's own canvas, captured in the page and posted here.

    Replaces Chromium's --screenshot, which only fires when
    --virtual-time-budget expires and takes the browser down with it.
    """
    if H.shot is None:
        h.send_error(404)
        return
    H.shot.write_bytes(base64.b64decode(h.body()))
    h.no_content()


def post_changes(h: Handler) -> None:
    raw = h.body().decode()
    q = h.query()
    idx = q.get("index", [""])[0]
    save_changes(raw, int(idx) if idx else None, int(q.get("count", ["0"])[0]))
    h.no_content()


def post_save(h: Handler) -> None:
    do_save(h, json.loads(h.body() or b"{}"))


def post_open(h: Handler) -> None:
    """Serve OpenFilenameDialog. No chooser installed means "cancelled"."""
    name = h.query().get("filter", [""])[0]
    path = hooks.OPEN_PATH_CHOOSER(name) if hooks.OPEN_PATH_CHOOSER else None
    logger.info("open dialog (%s) -> %s", name, path or "cancelled")
    h.send_bytes(json.dumps({"path": path or ""}).encode(), "application/json")


def open_in_window(h: Handler, document: pathlib.Path) -> None:
    """Open a document the way a desktop editor does: in a window of its own.

    Replacing the document in the window that asked would discard whatever is
    open there, unsaved changes included, without asking -- which is what this
    used to do.
    """
    if hooks.WINDOW_OPENER is None:
        # Nowhere to put a second document: `libera --serve` and the harness
        # have one window and no way to make another.
        ok = convert_to_editor_bin(document)
        if ok:
            H.current.write_text(str(document), encoding="utf-8")
            state.MEDIA_SERVED.clear()
            state.SEEN.clear()
            state.ERRORS.clear()
            remember_recent(document)
        body = json.dumps({"opened": ok, "here": True}).encode()
        h.send_bytes(body, "application/json")
        return

    hooks.WINDOW_OPENER(document)
    logger.info("open in a new window: %s", document)
    h.send_bytes(b'{"opened": true, "here": false}', "application/json")


def post_open_document(h: Handler) -> None:
    """File > Open: pick a document and open it in a new window."""
    path = hooks.OPEN_PATH_CHOOSER("documents") if hooks.OPEN_PATH_CHOOSER else None
    if not path:
        logger.info("open document: cancelled")
        h.send_bytes(b'{"opened": false, "here": true}', "application/json")
        return
    open_in_window(h, pathlib.Path(path))


def post_fullscreen(h: Handler) -> None:
    """Slides entering or leaving a demonstration.

    A setter, not a toggle: sdkjs sends true on start and false on end, and a
    toggle drifts out of step the first time either is missed.
    """
    on = h.body().decode().strip() == "1"
    if hooks.FULLSCREEN is not None:
        hooks.FULLSCREEN(on)
    logger.debug("fullscreen -> %s", on)
    h.no_content()


def post_reveal(h: Handler) -> None:
    """File > Open File Location."""
    path = current_path()
    shown = reveal(path) if path else False
    note = "" if shown else " (nothing to show)"
    logger.info("reveal -> %s%s", path or "no current file", note)
    h.no_content()


def post_open_url(h: Handler) -> None:
    """Open an external link in the user's browser.

    http(s) only: the page must not be able to talk the host into opening a
    file:// URL or anything else the desktop would act on.
    """
    url = h.body().decode("utf-8", "replace").strip()
    if not re.match(r"^https?://[^\s]+$", url):
        logger.warning("open-url refused: %r", url[:80])
        h.send_error(400)
        return
    # The page is told nothing either way: there is nothing useful for it to do
    # about the desktop's configuration. desktop.open_url logs the verdict.
    desktop.open_url(url)
    h.no_content()


def post_media_import(h: Handler) -> None:
    do_media_import(h, h.body().decode())


def post_report(h: Handler) -> None:
    data = json.loads(h.body() or b"{}")
    for c in data.get("calls", []):
        state.SEEN.setdefault(c["name"], 0)
        state.SEEN[c["name"]] += 1

    events = data.get("events", [])
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
            broken(e["text"], quiet=editor_spoke)
    h.no_content()


def broken(message: str, *, quiet: bool = False) -> None:
    """The editor threw where nothing caught it, so its state is a guess.

    Only uncaught errors, not every console.error and not asc_onError: the
    editor reports plenty it has already handled, and a dialog for those would
    train people to dismiss the one that matters.

    `quiet` when the editor is putting up its own dialog about the same fault.
    Two dialogs for one error is what a user called confusing, and they were
    right -- so this stays silent and File > Reload remains the way out.
    """
    session = current_session()
    if hooks.BROKEN is None or session in state.OFFERED:
        return
    state.OFFERED.add(session)
    if quiet:
        logger.info("editor error: it is telling the user itself")
        return
    hooks.BROKEN(session, message)


def do_save(h: Handler, body: dict) -> None:
    """Serve LocalFileSave."""
    result = save_document(body)
    h.send_bytes(json.dumps(result).encode(), "application/json")


def do_media_import(h: Handler, path: str) -> None:
    """Copy a picked file into the document's media folder, native-style.

    LocalFileGetImageUrl returns the *name* it was stored under, which the
    editor then resolves through the document URL — so the file has to
    actually be in media/ or the image resolves to nothing.
    """
    src = pathlib.Path(path)
    if not src.is_file():
        h.send_bytes(b'{"name": ""}', "application/json")
        return
    H.media.mkdir(parents=True, exist_ok=True)
    name = src.name
    n = 1
    while (H.media / name).exists():
        name = f"{src.stem}-{n}{src.suffix}"
        n += 1
    shutil.copyfile(src, H.media / name)
    logger.info("media import: %s -> media/%s", src, name)
    h.send_bytes(json.dumps({"name": name}).encode(), "application/json")


def create_new(h: Handler) -> None:
    """File > New: a blank document, in a window of its own.

    `type` names the editor -- word, cell, slide -- the way the editor's own
    execCommand("create:new", type) sends it, and the way the start window
    asks for a spreadsheet rather than a document. Absent means "the same kind
    as the window that asked", which is what the bound session already says.
    """
    wanted = h.query().get("type", [""])[0]
    app = next((a for a in apps.ALL if a.doctype == wanted), None)
    blank = H.blank_for(app)
    if not blank.is_file():
        h.send_error(500, f"no blank document at {blank}")
        return
    if hooks.WINDOW_OPENER is not None:
        hooks.WINDOW_OPENER(None, app)
        logger.info("new document in a new window")
        h.send_bytes(b'{"here": false}', "application/json")
        return
    if not convert_to_editor_bin(blank):
        h.send_error(500, "could not convert the blank document")
        return
    shutil.rmtree(H.out, ignore_errors=True)
    state.MEDIA_SERVED.clear()
    state.SEEN.clear()
    state.ERRORS.clear()
    h.send_bytes(b'{"here": true}', "application/json")


def post_open_recent(h: Handler) -> None:
    """Open a document the editor picked from the Recent list."""
    wanted = json.loads(h.body() or b"{}").get("id")
    # Only something already in the list: the page must not be able to name an
    # arbitrary path and have the host open it.
    known = {e["path"] for e in read_recents()}
    if wanted not in known:
        logger.warning("open:recent refused: %r", str(wanted)[:80])
        h.send_error(404)
        return
    open_in_window(h, pathlib.Path(wanted))


def post_can(h: Handler) -> None:
    """The editor reporting what it can do: undo, redo.

    Pushed rather than asked for, because a menu is validated on the GUI
    thread and asking the editor from there would deadlock.
    """
    EDITOR_STATE.setdefault(current_session(), {}).update(json.loads(h.body() or b"{}"))
    h.no_content()


def post_modified(h: Handler) -> None:
    set_modified(bool(json.loads(h.body() or b"{}").get("modified")))
    h.no_content()
