"""The editor's page as a client of the host: the bridge it is given, what it
reports about itself, the few things it asks of the desktop (full screen for a
slideshow, a link in the browser), and the address it lives at.
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
import sys
import urllib.parse
from typing import TYPE_CHECKING

from libera import timeline
from libera.host import desktop, hooks, instance, language, shortcuts
from libera.host.desktop import lookup_local_user
from libera.host.server import diagnostics
from libera.host.server.api import NO_CONTENT, Refused, Request, Response, endpoint

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)


BRIDGE_PARTS = ("bridge-runtime.js", "bridge-page.js", "bridge-desktop.js")

INJECT = b"".join(
    [b'<script src="/sdkjs/common/spell/spell.js"></script>']
    + [b'<script src="/__host__/%s"></script>' % part.encode() for part in BRIDGE_PARTS]
)


JAVASCRIPT = "application/javascript"


@endpoint("GET", *BRIDGE_PARTS)
def serve_bridge(r: Request) -> Response:
    """One part of the bridge, the first with the page's flags before it."""
    part = r.name
    source = pathlib.Path(__file__).with_name(part).read_bytes()
    if part != BRIDGE_PARTS[0]:
        return Response(body=source, content_type=JAVASCRIPT)
    session = r.session

    # The flags ride on the first part, which is the one the others depend on:
    #
    #   LIBERA_SHOT        the harness wants the page to photograph itself
    #   LIBERA_OWNED_KEYS  key equivalents a macOS menu bar already fires, so
    #                       the page must not act on them too. The page reads
    #                       them here from shortcuts.PAGE_YIELDS, the one
    #                       definition. Empty without a menu: `libera --serve` and
    #                       the harness have none and nothing to yield to.
    #   LIBERA_PAGE_KEYS   the keys the page runs itself, on Windows, where no
    #                       menu bar has them -- shortcuts.PAGE_RUNS.
    #   LIBERA_LOCKED_BY   who else has the document open, from their lock
    #                       file, or null: the editor opens it in its locked
    #                       mode (locking.hold, bridge-desktop LocalStartOpen).
    #   LIBERA_STRINGS     our strings in the interface language, English to
    #                       it, for the few the bridge shows (bridge-desktop tr).
    prelude = (
        f"var LIBERA_SHOT = {str(session.shot is not None).lower()};\n"
        f"var LIBERA_OWNED_KEYS = {json.dumps(list_owned_keys())};\n"
        f"var LIBERA_PAGE_KEYS = {json.dumps(list_page_keys())};\n"
        f"var LIBERA_LOCKED_BY = {json.dumps(session.locked_by)};\n"
        f"var LIBERA_STRINGS = {json.dumps(language.get_catalogue())};\n"
    )
    return Response(body=prelude.encode() + source, content_type=JAVASCRIPT)


def list_owned_keys() -> list[dict]:
    """The key equivalents the native menu bar fires, for the page to yield.

    macOS only. The GTK bar's accelerators reach the window before WebKit, so
    the page never sees them to yield (`menu/gtk.py`), and the WinForms bar has
    none.

    `shell.windowed` is the test for "this process has windows and therefore
    a menu".
    """
    if sys.platform != "darwin" or not hooks.shell.windowed:
        return []
    return [shortcut.as_json() for shortcut in shortcuts.PAGE_YIELDS]


# What the menu bar asks the editor about: menu.actions reads these names.
_ABILITIES = frozenset({"undo", "redo"})


@endpoint("POST", "can")
def record_abilities(r: Request) -> Response:
    """The editor reporting what it can do: undo, redo.

    The editor pushes this, because a menu is validated on the GUI thread and
    asking the editor from there would deadlock.
    """
    abilities = r.read_json()
    if not abilities.keys() <= _ABILITIES or not all(
        isinstance(v, bool) for v in abilities.values()
    ):
        raise Refused(400, "only undo and redo, each true or false")
    r.session.abilities.update(abilities)
    return NO_CONTENT


def _is_list_of(found: object, *keys: str) -> bool:
    """A list of JSON objects, each with these keys holding strings."""
    return isinstance(found, list) and all(
        isinstance(item, dict) and all(isinstance(item.get(k), str) for k in keys)
        for item in found
    )


@endpoint("POST", "page-log")
def receive_page_log(r: Request) -> Response:
    """What the bridge saw since it last said: the AscDesktopEditor calls the
    editor made and what went wrong in the page."""
    log = r.read_json()
    calls, events = log.get("calls", []), log.get("events", [])
    if not _is_list_of(calls, "name") or not _is_list_of(
        events, "frame", "kind", "text"
    ):
        raise Refused(400, "calls and events are lists of what the bridge logs")

    for c in calls:
        diagnostics.count(diagnostics.SEEN, c["name"])
        if c["name"] == "onDocumentContentReady":
            timeline.mark("editor-ready", again=True)

    for e in events:
        logger.warning("[%s] %s: %s", e["frame"], e["kind"], e["text"])
        diagnostics.ERRORS.append(e)

    # The editor's own error dialog and ours are two dialogs for one fault;
    # the second is the confusing one. asc_onError means the editor
    # has already said something, so we say nothing and leave the recovery to
    # File > Reload, which is always there.
    editor_spoke = any(e["kind"] == "asc_onError" for e in events)
    for e in events:
        if e["kind"] == "error":
            handle_editor_error(r.session, e["text"], quiet=editor_spoke)
    return NO_CONTENT


def handle_editor_error(session: Session, message: str, *, quiet: bool = False) -> None:
    """The editor threw where nothing caught it, so its state is a guess.

    Only uncaught errors, not every console.error and not asc_onError: a
    dialog for each of the many the editor has already handled would train
    people to dismiss the one that matters.

    `quiet` when the editor is putting up its own dialog about the same fault.
    A user called two dialogs for one error confusing, rightly, so this stays
    silent and File > Reload remains the way out.
    """
    if session.reload_offered:
        return
    session.reload_offered = True
    if quiet:
        logger.info("editor error: it is telling the user itself")
        return
    hooks.shell.offer_reload(session, message)


@endpoint("POST", "fullscreen")
def set_fullscreen(r: Request) -> Response:
    """Slides entering or leaving a demonstration.

    A setter, not a toggle: sdkjs sends true on start and false on end, and a
    toggle drifts out of step the first time either is missed.
    """
    on = r.read_field("on", bool)
    hooks.shell.set_fullscreen(on)
    logger.debug("fullscreen -> %s", on)
    return NO_CONTENT


@endpoint("POST", "open-url")
def open_url(r: Request) -> Response:
    """Open an external link in the user's browser.

    http(s) only: the page must not be able to talk the host into opening a
    file:// URL or anything else the desktop would act on.
    """
    url = r.read_field("url", str)
    # fullmatch: `$` also matches before a final newline.
    if not re.fullmatch(r"https?://\S+", url):
        logger.warning("open-url refused: %r", url[:80])
        raise Refused(400)
    # The page is told nothing either way: there is nothing useful for it to do
    # about the desktop's configuration. desktop.open_url logs the verdict.
    desktop.open_url(url)
    return NO_CONTENT


def make_editor_url(port: int, session: Session, title: str) -> str:
    """The editor's address, with the session that answers for it.

    doctype is what api.js's appMap turns into an editor directory -- word,
    cell, slide, diagram -- so doctype, whatever the file name, decides
    whether Words or Tables comes up. filetype has to agree with it or the
    editor loads and then refuses the document.

    The editor loads itself in an iframe and forwards only the parameters it
    knows, so the session never reaches the inner frame's URL. It does not need
    to: the frames are same-origin, and the bridge reads it off the top window.
    The key goes no further than this first request, whose answer sets the
    cookie that brings it from then on: see `admission`.
    """
    user_id, user_name = lookup_local_user()
    app = session.editor
    mode = "edit" if app.editable else "view"
    ext = pathlib.Path(title).suffix.lstrip(".").lower() or app.ext
    return (
        f"http://127.0.0.1:{port}/web-apps/apps/api/documents/index.html"
        f"?doctype={app.doctype}&mode={mode}"
        f"&lang={urllib.parse.quote(language.get_language())}"
        f"&title={urllib.parse.quote(title)}"
        f"&filetype={ext}&session={urllib.parse.quote(session.id)}"
        f"&key={instance.TOKEN}"
        f"&userid={urllib.parse.quote(user_id)}"
        f"&username={urllib.parse.quote(user_name)}"
    )


def list_page_keys() -> dict[str, dict]:
    """The keys the page runs itself, by action: on Windows only, whose bar has
    no accelerators. The macOS and GTK bars have them, and on macOS Ctrl-N is a
    text-editing key."""
    if sys.platform != "win32":
        return {}
    return {name: key.as_json() for name, key in shortcuts.PAGE_RUNS.items()}
