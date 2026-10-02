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
import urllib.parse

from libera.host import apps, hooks, shortcuts
from libera.host.recents import read_recents_for_editor
from libera.host.server import state
from libera.host.session import Session, is_inside

logger = logging.getLogger(__name__)

BRIDGE_PARTS = ("bridge-runtime.js", "bridge-page.js", "bridge-desktop.js")
INJECT = b"".join(
    [b'<script src="/sdkjs/common/spell/spell.js"></script>']
    + [b'<script src="/__host__/%s"></script>' % part.encode() for part in BRIDGE_PARTS]
)


def _serve_start() -> tuple[bytes, str]:
    """The start window's page. Ours, not the payload's.

    Upstream keeps its start screen in the C++ shell, so there is nothing to
    reuse: this is a plain page served by the host, talking to the same
    /__host__/ endpoints the editor does. No bridge, no sdkjs, no theme.
    """
    page = pathlib.Path(__file__).with_name("start.html").read_bytes()
    return page, "text/html; charset=utf-8"


def _serve_apps() -> tuple[bytes, str]:
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


def _serve_payload(session: Session) -> tuple[bytes, str]:
    """Where the payload came from, for the start window to show.

    The same facts `libera --payload-status` prints. Read from the installed
    payload's own payload.json, so a development tree honestly reports that it
    knows nothing.
    """
    # Imported here, not at module scope: the host runs without the installer
    # in `libera --serve`, and this is the only thing that wants it.
    from libera import payload as payload_mod

    # Unreadable is not the same as absent: a payload.json that will not parse
    # was shown as "local build", which is what a tree with none is told.
    marker = session.payload / "payload.json"
    info = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
    body = {
        "root": str(session.payload),
        # How this process found it -- LIBERA_PAYLOAD, a config file, or the
        # installed copy -- which is not in payload.json because it is not a
        # property of the payload.
        "origin": payload_mod.resolve().origin,
        "version": info.get("payload_version") or "local build",
        "platform": info.get("platform"),
        "built": info.get("built"),
    }
    return json.dumps(body).encode(), "application/json"


def _serve_current(session: Session) -> tuple[bytes, str]:
    p = session.read_current_document()
    return json.dumps({"path": str(p) if p else ""}).encode(), "application/json"


def _serve_opened(session: Session) -> tuple[bytes, str]:
    data = session.editor_bin.read_bytes()
    body = {"b64": base64.b64encode(data).decode(), "len": len(data)}
    return json.dumps(body).encode(), "application/json"


def _serve_bridge(session: Session, part: str) -> tuple[bytes, str]:
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
        f"var LIBERA_SHOT = {str(session.shot is not None).lower()};\n"
        f"var LIBERA_OWNED_KEYS = {json.dumps(list_owned_keys())};\n"
    )
    return prelude.encode() + source, "application/javascript"


def list_owned_keys() -> list[dict]:
    """The key equivalents the native menu bar fires, for the page to yield.

    macOS only, and not for want of a menu elsewhere: the GTK bar carries no
    accelerators at all (`menu/gtk.py` says why), so on Linux the page owns
    every key and has nothing to yield.

    `shell.windowed` is the test for "this process has windows and therefore
    a menu".
    """
    if sys.platform != "darwin" or not hooks.shell.windowed:
        return []
    return [shortcut.as_json() for shortcut in shortcuts.PAGE_YIELDS]


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


def deobfuscated(data: bytes) -> bytes:
    n = min(32, len(data))
    head = bytes(b ^ ODTTF_KEY[i % 16] for i, b in enumerate(data[:n]))
    return head + data[n:]


def serve(session: Session, name: str) -> tuple[bytes | None, str]:
    """Resolve a /__host__/ GET. Returns (body, content-type); None body = 404."""
    exact = {
        "calls": lambda: (state.build_report(session), "application/json"),
        "apps": _serve_apps,
        "current": lambda: _serve_current(session),
        "payload": lambda: _serve_payload(session),
        "recents": lambda: read_recents_for_editor(session),
        "start": _serve_start,
        "opened": lambda: _serve_opened(session),
    }.get(name)
    if exact:
        return exact()

    if name in BRIDGE_PARTS:
        return _serve_bridge(session, name)

    prefix, _, rest = name.partition("/")
    # As the page wrote it: a picture imported as "My Photo.png" is asked for
    # as My%20Photo.png, and was never found. Decoded before the containment
    # check, so an encoded ".." is refused like a plain one.
    rest = urllib.parse.unquote(rest)
    if prefix == "media":
        f = session.media / rest
        if is_inside(session.media, f):
            state.MEDIA_SERVED.add(f.name)
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            return f.read_bytes(), ctype
    elif prefix == "fonts":
        f = session.fonts / rest
        if is_inside(session.fonts, f):
            return deobfuscated(f.read_bytes()), "application/octet-stream"
    return None, ""
