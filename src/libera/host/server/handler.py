"""The HTTP plumbing: one request handler, one server, one URL.

The top of the package. It owns the socket, dispatches to `get` and `post`,
and splices the bridge into every HTML page on the way out.
"""

from __future__ import annotations

import http.server
import logging
import pathlib
import socket
import time
import urllib.parse
from typing import TYPE_CHECKING

from libera import logs
from libera.host.desktop import local_user
from libera.host.server import get, post, state
from libera.host.session import H, NotReadyError, bind

if TYPE_CHECKING:
    import io
    from typing import Any, BinaryIO

logger = logging.getLogger(__name__)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server, **kw) -> None:
        # The payload is the same for every session, so the static root comes
        # from the server; anything session-shaped is bound per request below.
        super().__init__(
            request, client_address, server, directory=str(server.payload), **kw
        )

    def bind_session(self) -> None:
        """Bind the session this request names, or the first one.

        Static requests carry no session and do not need one -- the payload is
        shared. Everything the bridge sends does carry one, because a request
        about a document has to reach the right document.
        """
        bind(self.query().get("session", [""])[0])

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        code = getattr(code, "value", code)
        if code == state.NOT_FOUND_CODE:
            state.NOT_FOUND.add(self.path.split("?")[0])
        if code in {200, 204}:
            return
        # A 404 is usually the editor asking for something we chose not to
        # ship -- its help, its plugins -- and the e2e suite checks the whole
        # set of them anyway. Anything else went wrong.
        logger.log(
            logging.DEBUG if code == state.NOT_FOUND_CODE else logging.WARNING,
            "%s %s",
            code,
            self.path,
        )

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _trace(self, tag: str) -> None:
        """Two lines per request: one as it starts, one as it finishes.

        -vvv, and nothing less. It exists because "the editor stopped" and
        "the server stopped answering" look identical from the outside, and
        telling them apart needs to know which requests were made and which
        came back. During a document load that is thousands of lines.
        """
        if logs.tracing_requests():
            logger.debug("%.3f %s %s %s", time.time(), tag, self.command, self.path)

    def do_POST(self) -> None:
        self.bind_session()
        route = self.path.split("?")[0].removeprefix("/__host__/")
        state.ROUTES[route] = state.ROUTES.get(route, 0) + 1
        handler = {
            "new": post.create_new,
            "changes": post.post_changes,
            "save": post.post_save,
            "open": post.post_open,
            "media-import": post.post_media_import,
            "open-document": post.post_open_document,
            "fullscreen": post.post_fullscreen,
            "reveal": post.post_reveal,
            "open-url": post.post_open_url,
            "open-recent": post.post_open_recent,
            "modified": post.post_modified,
            "can": post.post_can,
            "report": post.post_report,
            "shot": post.post_shot,
        }.get(route)
        if handler is None:
            self.send_error(404)
            return
        handler(self)

    def query(self) -> dict[str, list[str]]:
        return urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query, keep_blank_values=True
        )

    def body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def no_content(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        self._trace("get>")
        self.bind_session()
        try:
            if self.path == "/document_editor_service_worker.js":
                self.send_bytes(H.service_worker.read_bytes(), "application/javascript")
                return
            if self.path.startswith("/__host__/"):
                self.serve_host(self.path[len("/__host__/") :].split("?")[0])
                return
            super().do_GET()
        finally:
            self._trace("done")

    def serve_host(self, name: str) -> None:
        """GET side of the POC API. Static files fall through to the base class."""
        body, ctype = get.host_get(name)
        if body is None:
            self.send_error(404)
            return
        self.send_bytes(body, ctype)

    def send_bytes(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_head(self) -> io.BytesIO | BinaryIO | None:
        """Splice the bridge into every HTML page, including the editor iframe."""
        path = pathlib.Path(self.translate_path(self.path))
        if path.suffix != ".html" or not path.is_file():
            return super().send_head()

        body = path.read_bytes()
        marker = b"<head>"
        i = body.lower().find(marker)
        if i == -1:
            msg = f"no <head> to inject into: {path}"
            raise RuntimeError(msg)
        body = body[: i + len(marker)] + get.INJECT + body[i + len(marker) :]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return None if self.command == "HEAD" else __import__("io").BytesIO(body)


def check_ready() -> None:
    """Fail early and legibly rather than 404-ing every asset.

    The payload only. Editor.bin is session state, not payload, and a start
    window has no document and therefore no Editor.bin -- opening one is what
    creates it, and opening reports its own failure.
    """
    for path in (H.web, H.sdkjs_common / "AllFonts.js"):
        if not path.exists():
            msg = f"missing: {path}"
            raise NotReadyError(msg)
    if not any(H.fonts.glob("*")):
        msg = f"no fonts in {H.fonts}"
        raise NotReadyError(msg)


class Server(http.server.ThreadingHTTPServer):
    """The server, plus the one thing every request needs before a session.

    A subclass rather than an attribute set from outside: `httpd.payload = ...`
    works at runtime and is invisible to everything else, including the reader
    wondering where Handler.__init__ gets `server.payload` from.
    """

    payload: pathlib.Path


def make_server(port: int) -> Server:
    check_ready()
    httpd = Server(("127.0.0.1", port), Handler)
    # Shared by every session, and needed before any session is bound.
    httpd.payload = H.payload
    return httpd


PREFERRED_PORT = 43110


def free_port() -> int:
    """The editor's port: the usual one, or any free one if it is taken.

    A second window falls back and forgets its settings. One window remembering
    beats neither, and the alternative is failing to start.
    """
    with socket.socket() as s:
        # SO_REUSEADDR because the previous window's connections sit in
        # TIME_WAIT for a couple of minutes after it closes, and without it a
        # relaunch inside that window silently lands on a different port --
        # which is to say, a different origin with none of the settings.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", PREFERRED_PORT))
        except OSError:
            s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def editor_url(port: int, title: str = "document.docx", session: str = "") -> str:
    """The editor's address, with the session that answers for it.

    doctype is what api.js's appMap turns into an editor directory -- word,
    cell, slide, diagram -- so it, and not the file name, is what decides
    whether Words or Tables comes up. filetype has to agree with it or the
    editor loads and then refuses the document.

    The editor loads itself in an iframe and forwards only the parameters it
    knows, so the session never reaches the inner frame's URL. It does not need
    to: the frames are same-origin, and the bridge reads it off the top window.
    """
    user_id, user_name = local_user()
    app = H.editor
    mode = "edit" if app.editable else "view"
    ext = pathlib.Path(title).suffix.lstrip(".").lower() or app.ext
    return (
        f"http://127.0.0.1:{port}/web-apps/apps/api/documents/index.html"
        f"?doctype={app.doctype}&mode={mode}&lang=en"
        f"&title={urllib.parse.quote(title)}"
        f"&filetype={ext}&session={urllib.parse.quote(session)}"
        f"&userid={urllib.parse.quote(user_id)}"
        f"&username={urllib.parse.quote(user_name)}"
    )
