"""The payload, served as static files: every editor asset, with the bridge
spliced into every HTML page; the fonts, as the editor's web loader expects
them; and our own service worker.
"""

from __future__ import annotations

import hashlib
import mimetypes
import pathlib

from libera.host.server import editor
from libera.host.server.api import Refused, Request, Response, endpoint
from libera.host.session import is_inside
from libera.payload import fonts

# The editor registers a service worker at the origin root. This is the one it
# gets: it caches nothing, and clears what upstream's cached.
SERVICE_WORKER = pathlib.Path(__file__).with_name("service-worker.js")


def serve_service_worker() -> Response:
    """Ours, replacing the payload's: see service-worker.js for why."""
    return Response(body=SERVICE_WORKER.read_bytes(), content_type=editor.JAVASCRIPT)


def serve_file(
    payload: pathlib.Path,
    path: str,
    if_none_match: str,
    font_index: pathlib.Path,
) -> Response:
    """A payload file, with the bridge spliced into every HTML page, the
    editor's iframe included.

    Any other file revalidates by ETag before it is reused. Not by
    modification time: files unpacked from the release archives keep the
    archive's times, so two payloads can hold the same name with the same
    Last-Modified. The tag is the file's full path, size and nanosecond mtime,
    so a different payload root, or a regenerated file, is a different tag.

    The font list and the font menu's pictures are the fonts' index's.
    """
    root, target = payload, payload / path
    if own := fonts.find_served(font_index, path):
        root, target = font_index, own
    if target.is_dir():
        target /= "index.html"
    if not is_inside(root, target):
        raise Refused(404)
    if target.suffix == ".html":
        body = target.read_bytes()
        marker = b"<head>"
        i = body.lower().find(marker)
        if i == -1:
            msg = f"no <head> to inject into: {target}"
            raise RuntimeError(msg)
        body = body[: i + len(marker)] + editor.INJECT + body[i + len(marker) :]
        return Response(body=body, content_type="text/html; charset=utf-8")
    etag = _make_etag(target)
    if etag in if_none_match:
        return Response(304, content_type="", headers={"ETag": etag})
    ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return Response(
        content_type=ctype,
        file=target,
        headers={
            "ETag": etag,
            # Revalidate every time. Without it Chromium reused its copy on
            # heuristic freshness. WebView2 keeps that cache for the origin
            # across payloads, so a document opened against a new payload ran
            # sdkjs with the previous one's AllFonts.js, asked for fonts the new
            # set does not have, and died in text shaping.
            "Cache-Control": "no-cache",
        },
    )


def _make_etag(path: pathlib.Path) -> str:
    st = path.stat()
    identity = f"{path}|{st.st_size}|{st.st_mtime_ns}".encode()
    return '"' + hashlib.sha256(identity).hexdigest()[:24] + '"'


@endpoint("GET", "fonts", prefix=True)
def serve_font(r: Request) -> Response:
    """The font at that place in the fonts' index, untouched.

    A number and nothing else, so a page can reach no file the index does not
    list. isascii as well, because int() reads other scripts' digits too.
    Not the web copies allfontsgen's --output-web makes, which it obfuscates
    for the web loader to undo, and which a payload no longer carries.
    """
    number = r.path
    files = fonts.read_font_files(r.session.all_fonts)
    if not (number.isascii() and number.isdigit() and int(number) < len(files)):
        raise Refused(404)
    return Response(content_type="application/octet-stream", file=files[int(number)])
