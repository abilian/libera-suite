"""Everything served by GET: the bridge, and what the page asks about itself.

Above `state` and below `handler`. Nothing here writes a document; the POST
side does that.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import pathlib
import sys

from libera.host import apps, hooks, shortcuts
from libera.host.convert import deobfuscate
from libera.host.recents import get_recents
from libera.host.server import state
from libera.host.session import H, contains, current_path

logger = logging.getLogger(__name__)

BRIDGE_PARTS = ("bridge-runtime.js", "bridge-page.js", "bridge-desktop.js")
INJECT = b"".join(
    [b'<script src="/sdkjs/common/spell/spell.js"></script>']
    + [b'<script src="/__host__/%s"></script>' % part.encode() for part in BRIDGE_PARTS]
)


def _get_start() -> tuple[bytes, str]:
    """The start window's page. Ours, not the payload's.

    Upstream keeps its start screen in the C++ shell, so there is nothing to
    reuse: this is a plain page served by the host, talking to the same
    /__host__/ endpoints the editor does. No bridge, no sdkjs, no theme.
    """
    page = pathlib.Path(__file__).with_name("start.html").read_bytes()
    return page, "text/html; charset=utf-8"


def _get_apps() -> tuple[bytes, str]:
    """The editors, for a page that offers to make a new document."""
    body = [
        {
            "name": app.name,
            "kind": app.noun,
            "doctype": app.doctype,
            "ext": app.ext,
            "creates": app.blank is not None,
        }
        for app in apps.ALL
    ]
    return json.dumps(body).encode(), "application/json"


def _get_payload_info() -> tuple[bytes, str]:
    """Where the payload came from, for the start window to show.

    The same facts `libera --payload-status` prints. Read from the installed
    payload's own payload.json, so a development tree honestly reports that it
    knows nothing.
    """
    # Imported here, not at module scope: the host runs without the installer
    # in `libera --serve`, and this is the only thing that wants it.
    from libera import payload as payload_mod

    info = {}
    marker = H.payload / "payload.json"
    if marker.is_file():
        try:
            info = json.loads(marker.read_text(encoding="utf-8"))
        except ValueError:
            info = {}
    body = {
        "root": str(H.payload),
        # How this process found it -- LIBERA_PAYLOAD, a config file, or the
        # installed copy -- which is not in payload.json because it is not a
        # property of the payload.
        "origin": payload_mod.resolve().origin,
        "version": info.get("payload_version") or "local build",
        "platform": info.get("platform"),
        "built": info.get("built"),
    }
    return json.dumps(body).encode(), "application/json"


def _get_current() -> tuple[bytes, str]:
    p = current_path()
    return json.dumps({"path": str(p) if p else ""}).encode(), "application/json"


def _get_opened() -> tuple[bytes, str]:
    data = H.editor_bin.read_bytes()
    body = {"b64": base64.b64encode(data).decode(), "len": len(data)}
    return json.dumps(body).encode(), "application/json"


def _get_bridge(part: str) -> tuple[bytes, str]:
    """One part of the bridge, with the harness's self-capture armed if wanted.

    The flag rides on the first part, which is the one the others depend on.
    """
    source = pathlib.Path(__file__).with_name(part).read_bytes()
    if part != BRIDGE_PARTS[0]:
        return source, "application/javascript"

    # The flags ride on the first part, which is the one the others depend on:
    #
    #   LIBERA_SHOT        the harness wants the page to photograph itself
    #   LIBERA_OWNED_KEYS  key equivalents a macOS menu bar already fires, so
    #                       the page must not act on them too -- menu.PAGE_YIELDS
    #                       is the one definition, and this is how the page
    #                       reads it. Empty without a menu: `libera --serve` and
    #                       the harness have none and nothing to yield to.
    prelude = (
        f"var LIBERA_SHOT = {str(H.shot is not None).lower()};\n"
        f"var LIBERA_OWNED_KEYS = {json.dumps(owned_keys())};\n"
    )
    return prelude.encode() + source, "application/javascript"


def owned_keys() -> list[dict]:
    """The key equivalents the native menu bar fires, for the page to yield.

    macOS only, and not for want of a menu elsewhere: the GTK bar carries no
    accelerators at all (`menu/gtk.py` says why), so on Linux the page owns
    every key and has nothing to yield.

    WINDOW_OPENER is installed by window.run and by nothing else, so it is the
    test for "this process has windows and therefore a menu".
    """
    if sys.platform != "darwin" or hooks.WINDOW_OPENER is None:
        return []
    return [shortcut.as_json() for shortcut in shortcuts.PAGE_YIELDS]


def host_get(name: str) -> tuple[bytes | None, str]:
    """Resolve a /__host__/ GET. Returns (body, content-type); None body = 404."""
    exact = {
        "calls": lambda: (state.host_report(), "application/json"),
        "apps": _get_apps,
        "current": _get_current,
        "payload": _get_payload_info,
        "recents": get_recents,
        "start": _get_start,
        "opened": _get_opened,
    }.get(name)
    if exact:
        return exact()

    if name in BRIDGE_PARTS:
        return _get_bridge(name)

    prefix, _, rest = name.partition("/")
    if prefix == "media":
        f = H.media / rest
        if contains(H.media, f):
            state.MEDIA_SERVED.add(f.name)
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            return f.read_bytes(), ctype
    elif prefix == "fonts":
        f = H.fonts / rest
        if contains(H.fonts, f):
            return deobfuscate(f.read_bytes()), "application/octet-stream"
    return None, ""
