"""Getting documents into windows: File > Open, Open Recent and the list it
shows, File > New, and a second launch handing its documents over.

This module decides *which* document a window shows; `document` handles what
a window does with the one it has.
"""

from __future__ import annotations

import logging
import pathlib
import shutil
import threading
from typing import TypeGuard

from libera.host import apps, hooks, opening as host_opening
from libera.host.convert import ConversionError, convert_to_editor_bin
from libera.host.recents import read_recents, read_recents_for_editor
from libera.host.server import diagnostics
from libera.host.server.api import Refused, Request, Response, answer_json, endpoint

logger = logging.getLogger(__name__)


@endpoint("GET", "recents")
def serve_recents(r: Request) -> Response:
    """The Recent list, in the shape the editor's File > Open Recent reads."""
    body, ctype = read_recents_for_editor(r.session)
    return Response(body=body, content_type=ctype)


@endpoint("POST", "choose-file")
def choose_file(r: Request) -> Response:
    """Serve OpenFilenameDialog: a file for the editor to insert, not a
    document to open. With no user to ask, nothing is chosen."""
    kind = r.read_field("filter", str, "")
    path = hooks.shell.choose_open_path(kind)
    logger.info("open dialog (%s) -> %s", kind, path or "cancelled")
    if path:
        r.session.offered.add(pathlib.Path(path))
    return answer_json({"path": path or ""})


def _opened(opened: bool, *, here: bool) -> Response:
    """Whether a document opened, and whether in the window that asked: only
    then does the page reload to show it (bridge-runtime.js, openedHere)."""
    return answer_json({"opened": opened, "here": here})


def _open_in_window(r: Request, document: pathlib.Path) -> Response:
    """Open a document the way a desktop editor does: in a window of its own.

    Replacing the document in the window that asked would discard whatever is
    open there, unsaved changes included, without asking -- which is what this
    used to do.
    """
    if not hooks.shell.windowed:
        # Nowhere to put a second document: `libera --serve` and the harness
        # have one window and no way to make another.
        try:
            host_opening.open_document(r.session, document)
        except ConversionError:
            opened = False
        else:
            opened = True
            diagnostics.reset()
        return _opened(opened, here=True)

    opened = hooks.shell.open_window(document)
    logger.info("open in a new window: %s", document)
    return _opened(opened, here=False)


@endpoint("POST", "open-document")
def open_document(r: Request) -> Response:
    """File > Open: pick a document and open it in a new window."""
    path = hooks.shell.choose_open_path("documents")
    if not path:
        logger.info("open document: cancelled")
        return _opened(False, here=True)
    return _open_in_window(r, pathlib.Path(path))


@endpoint("POST", "open-recent")
def open_recent(r: Request) -> Response:
    """Open a document the editor picked from the Recent list."""
    wanted = r.read_field("id", str)
    # Only something already in the list: the page must not be able to name an
    # arbitrary path and have the host open it.
    known = {e["path"] for e in read_recents(r.session)}
    if wanted not in known:
        logger.warning("open:recent refused: %r", wanted[:80])
        raise Refused(404)
    return _open_in_window(r, pathlib.Path(wanted))


def _is_list_of_str(found: object) -> TypeGuard[list[str]]:
    return isinstance(found, list) and all(isinstance(d, str) for d in found)


@endpoint("POST", "drop")
def take_drop(r: Request) -> Response:
    """Files dropped on a window, which the page knows by name only.

    The shell has their paths from the drag itself, so the page cannot name a
    file of its choosing: a name that was never dropped resolves to nothing.
    Documents open in windows of their own, as File > Open puts them, on a
    thread, so that the page is not held for a conversion. The rest come back as paths,
    which GetDropFiles hands to sdkjs, and sdkjs inserts the images among them.
    """
    names = r.read_json().get("names")
    if not _is_list_of_str(names):
        raise Refused(400, "names is not a list of file names")
    paths = hooks.shell.take_dropped(names)
    documents = [path for path in paths if apps.is_document(path)]
    for document in documents:
        threading.Thread(
            target=hooks.shell.open_window, args=(document,), daemon=True
        ).start()
    # Names against paths found tells a drag the native layer did not record
    # from one it did: the first thing to know when a drop does nothing.
    logger.info(
        "drop: %d named, %d found: %d documents, %d other files",
        len(names),
        len(paths),
        len(documents),
        len(paths) - len(documents),
    )
    others = [p for p in paths if p not in documents]
    r.session.offered.update(others)
    return answer_json({"paths": [str(p) for p in others]})


@endpoint("POST", "new")
def create_new(r: Request) -> Response:
    """File > New: a blank document, in a window of its own.

    `type` names the editor -- word, cell, slide -- the way the editor's own
    execCommand("create:new", type) sends it, and the way the start window
    asks for a spreadsheet rather than a document. Absent means "the same kind
    as the window that asked", which is what its session already says. Any
    other name is refused: it used to make the window's own kind, without a
    word.

    The editor's own File > Create New asks for its own kind, and the bridge
    lets the user choose instead (bridge-desktop.js, chooseNewKind), so any
    kind can arrive here from any window.
    """
    wanted = r.read_field("type", str, "")
    app = next((a for a in apps.ALL if a.doctype == wanted), None)
    if wanted and app is None:
        raise Refused(400, "no such kind of document")
    blank = r.session.choose_blank(app)
    if not blank.is_file():
        raise Refused(500, f"no blank document at {blank}")
    if hooks.shell.windowed:
        opened = hooks.shell.open_window(None, app)
        logger.info("new document in a new window")
        return _opened(opened, here=False)
    if app is not None and app is not r.session.editor:
        # `libera --serve` has this one window, and a document of another kind
        # cannot take the place of the one in it: the page would stay, say, a
        # word processor showing a spreadsheet's blank.
        raise Refused(409, f"A new {app.noun.lower()} needs a window of its own")
    try:
        convert_to_editor_bin(r.session, blank)
    except ConversionError as e:
        raise Refused(500, str(e)) from e
    shutil.rmtree(r.session.out_dir, ignore_errors=True)
    diagnostics.reset()
    return _opened(True, here=True)


@endpoint("POST", "hand-off")
def take_hand_off(r: Request) -> Response:
    """A second launch giving its documents to this instance.

    Only this user may have a file of their choosing opened: admission has
    checked the key, which the sender read from instance.json. See `instance`.

    Answered at once, and opened on a thread. The sender waits
    instance.HAND_OFF_TIMEOUT for the answer and reads a late one as "no
    instance": it then starts a second beside this one, which sweeps this
    one's session directories. Opening takes a conversion, and a recovery or
    an error dialog waits on the user.
    """
    documents = r.read_json().get("documents", [])
    if not _is_list_of_str(documents):
        raise Refused(400, "documents is a list of paths")
    if not hooks.shell.windowed:
        return _opened(False, here=False)
    threading.Thread(
        target=_open_handed_off,
        args=([pathlib.Path(d) for d in documents],),
        daemon=True,
    ).start()
    # Taken, whether or not each one opens: one that does not says so on
    # screen, and "not taken" would start a second instance.
    return _opened(True, here=False)


def _open_handed_off(documents: list[pathlib.Path]) -> None:
    for document in documents:
        if document.is_file():
            logger.info("hand-off: %s", document)
            hooks.shell.open_window(document)
        else:
            logger.warning("hand-off: no such file %s", document)
    if not documents:
        hooks.shell.show_start_window()
