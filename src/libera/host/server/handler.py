"""The HTTP plumbing: one request handler, one server, one URL.

The top of the package. It owns the socket, dispatches to `get` and `post`,
and splices the bridge into every HTML page on the way out.
"""

from __future__ import annotations

import contextlib
import hashlib
import http.server
import io
import logging
import pathlib
import socket
import sys
import time
import urllib.parse
from typing import TYPE_CHECKING, override

from libera import logs
from libera.host.desktop import lookup_local_user
from libera.host.server import get, post, state
from libera.host.session import NotReadyError, Session, lookup

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, BinaryIO

logger = logging.getLogger(__name__)

# The editor registers a service worker at the origin root. This is the one it
# gets: it caches nothing, and clears what upstream's cached.
SERVICE_WORKER = pathlib.Path(__file__).with_name("service-worker.js")

# Only our own pages may frame ours. Any site could put the start window in an
# iframe, and a click there sends new, open-recent and open-document with our
# origin, which admit() lets through. 'self' and not 'none': the editor
# frames itself.
FRAME_ANCESTORS = "frame-ancestors 'self'"


class Handler(http.server.SimpleHTTPRequestHandler):
    # The session this request is about, looked up by admit() from the id
    # in its query string, and handed to whatever answers it.
    session: Session

    def __init__(self, request, client_address, server, **kw) -> None:
        # The payload is the same for every session, so the static root comes
        # from the server; the session is looked up per request, by admit().
        super().__init__(
            request, client_address, server, directory=str(server.payload), **kw
        )

    def admit(self) -> bool:
        """Whether to serve this request. If not, it has been answered already.

        The server is on 127.0.0.1, which every page in every browser on this
        machine can reach, so what a page elsewhere could send is the question.

        **Host must be this server's address.** A page on a name its author
        controls can re-resolve that name to 127.0.0.1 -- DNS rebinding -- and
        is then same-origin with itself, so it reads every answer: the open
        document, the recent list, any file media-import was told to copy in.

        **Origin, when there is one, must be ours.** A browser sends it with
        every POST another page makes, and a text/plain POST needs no
        preflight. Measured before this check: a request from another origin,
        with no session named, truncated the open document's change log to
        nothing. Our own pages send our origin; the hand-off and the tests
        send none.

        **The session must exist.** Static requests name none and get the
        first, which is harmless because the payload is shared. A request
        about a document names its session, and one that has gone is refused:
        see session.lookup.
        """
        # The port this request arrived on, which is the server's.
        own = f"127.0.0.1:{self.connection.getsockname()[1]}"
        origin = self.headers.get("Origin")
        if self.headers.get("Host") != own or origin not in {None, f"http://{own}"}:
            logger.info("refused: Host %s, Origin %s", self.headers.get("Host"), origin)
            self.send_error(403)
            return False
        try:
            self.session = lookup(self.parse_query().get("session", [""])[0])
        except NotReadyError as e:
            # As the explanation, not the reason: the reason goes in the status
            # line, which http.server writes as latin-1, and an id that is not
            # raised UnicodeEncodeError there and dropped the connection.
            self.send_error(404, explain=str(e))
            return False
        return True

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        code = getattr(code, "value", code)
        if code == state.NOT_FOUND_CODE:
            state.NOT_FOUND.add(self.path.split("?")[0])
        # 304 is the ETag answer: the webview already holds that file.
        if code in {200, 204, 304}:
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
        if logs.is_tracing_requests():
            logger.debug("%.3f %s %s %s", time.time(), tag, self.command, self.path)

    def do_POST(self) -> None:
        if not self.admit():
            return
        route = self.path.split("?")[0].removeprefix("/__host__/")
        state.ROUTES[route] = state.ROUTES.get(route, 0) + 1
        handler = {
            "new": post.create_new,
            "changes": post.record_changes,
            "save": post.save,
            "open": post.show_open_dialog,
            "media-import": post.import_media,
            "open-document": post.open_document,
            "hand-off": post.take_hand_off,
            "fullscreen": post.set_fullscreen,
            "reveal": post.reveal,
            "open-url": post.open_url,
            "open-recent": post.open_recent,
            "modified": post.record_modified,
            "can": post.record_abilities,
            "report": post.receive_report,
            "shot": post.receive_shot,
        }.get(route)
        if handler is None:
            self.send_error(404)
            return
        self.answer(handler)

    def answer(self, route: Callable[[Handler], None]) -> None:
        """Run an endpoint, and answer for it when it fails.

        The one place a request's failure is caught: a route that raised used
        to close the connection with no response at all, which the editor sees
        as a network fault, and print a traceback past logs.py. A 400 for what
        the page sent, a 500 for the rest -- logged, with the traceback.
        """
        try:
            route(self)
        except post.BadRequestError as e:
            self.send_error(400, explain=str(e))
        except Exception:
            logger.exception("%s %s failed", self.command, self.path)
            # A route that had started its answer cannot start another; the
            # connection closes rather than carry a second one.
            self.close_connection = True
            with contextlib.suppress(OSError):
                self.send_error(500)

    def parse_query(self) -> dict[str, list[str]]:
        return urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query, keep_blank_values=True
        )

    def read_body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def send_no_content(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        self._trace("get>")
        try:
            if not self.admit():
                return
            if self.path == "/document_editor_service_worker.js":
                # Ours, not the payload's: see service-worker.js for why.
                self.send_bytes(SERVICE_WORKER.read_bytes(), "application/javascript")
                return
            if self.path.startswith("/__host__/"):
                name = self.path[len("/__host__/") :].split("?")[0]
                self.answer(lambda h: h.serve_host(name))
                return
            super().do_GET()
        finally:
            self._trace("done")

    def serve_host(self, name: str) -> None:
        """GET side of the POC API. Static files fall through to the base class."""
        body, ctype = get.serve(self.session, name)
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

    # The ETag of the static file being served, if any; end_headers adds it.
    _etag: str | None = None
    _cache_control_sent = False

    def send_response(self, code: int, message: str | None = None) -> None:
        self._cache_control_sent = False
        super().send_response(code, message)

    def send_header(self, keyword: str, value: str) -> None:
        if keyword.lower() == "cache-control":
            self._cache_control_sent = True
        super().send_header(keyword, value)

    def end_headers(self) -> None:
        """Every payload file revalidates, by ETag, before it is reused.

        Without a Cache-Control, SimpleHTTPRequestHandler's Last-Modified is
        all a browser has, and Chromium then reuses its copy on heuristic
        freshness without asking. WebView2 keeps that cache for the origin,
        127.0.0.1:43110, across payloads -- so a document opened against a
        freshly installed payload ran sdkjs with the *previous* payload's
        AllFonts.js: it asked for web fonts 075 and 154 of a set that has 32,
        got 404s, and died in text shaping on a null m_pFaceInfo. A payload
        update or a font regeneration would do the same to any user.
        """
        self.send_header("Content-Security-Policy", FRAME_ANCESTORS)
        if self._etag is not None and self.command in {"GET", "HEAD"}:
            self.send_header("ETag", self._etag)
        if not self._cache_control_sent:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self) -> io.BytesIO | BinaryIO | None:
        """Splice the bridge into every HTML page, including the editor iframe.

        Any other file is the base class's, revalidated by ETag. Not by
        modification time: files unpacked from the release archives keep the
        archive's times, so two different payloads can hold the same name with
        the same Last-Modified, and If-Modified-Since would answer 304 for the
        wrong one. The tag is the file's full path, size and nanosecond mtime,
        so a different payload root, or a regenerated file, is a different tag.
        """
        self._etag = None
        path = pathlib.Path(self.translate_path(self.path))
        if path.suffix != ".html" or not path.is_file():
            if path.is_file():
                self._etag = _make_etag(path)
                if self._etag in self.headers.get("If-None-Match", ""):
                    self.send_response(304)
                    self.end_headers()
                    return None
                del self.headers["If-Modified-Since"]
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
        return None if self.command == "HEAD" else io.BytesIO(body)


def _make_etag(path: pathlib.Path) -> str:
    st = path.stat()
    identity = f"{path}|{st.st_size}|{st.st_mtime_ns}".encode()
    return '"' + hashlib.sha256(identity).hexdigest()[:24] + '"'


def check_ready(session: Session) -> None:
    """Fail early and legibly rather than 404-ing every asset.

    The payload only. Editor.bin is session state, not payload, and a start
    window has no document and therefore no Editor.bin -- opening one is what
    creates it, and opening reports its own failure.
    """
    for path in (session.payload, session.sdkjs_common / "AllFonts.js"):
        if not path.exists():
            msg = f"missing: {path}"
            raise NotReadyError(msg)
    if not any(session.fonts.glob("*")):
        msg = f"no fonts in {session.fonts}"
        raise NotReadyError(msg)


class Server(http.server.ThreadingHTTPServer):
    """The server, plus the one thing every request needs before a session.

    A subclass rather than an attribute set from outside: `httpd.payload = ...`
    works at runtime and is invisible to everything else, including the reader
    wondering where Handler.__init__ gets `server.payload` from.
    """

    payload: pathlib.Path

    # On Windows SO_REUSEADDR is not about TIME_WAIT -- a listener rebinds
    # through that without it -- but lets a second socket bind a port another
    # is already listening on. Two instances would then share PREFERRED_PORT
    # and split its requests between them.
    allow_reuse_address = sys.platform != "win32"

    # The listen backlog: connections the kernel holds before the server
    # accepts them. socketserver's default is 5, and the editor opens with a
    # burst of font requests over half a dozen connections at once. One that
    # found the queue full was reset; the font loader does not retry, and the
    # document sat at "Loading document: 8%" for good -- the project's oldest
    # bug. Measured: 5 loads in 300 stalled, each with exactly one font request
    # reset, and none in 300 with this. Resetting one font request on purpose
    # stalls the load every time; delaying it by 3s does not.
    request_queue_size = socket.SOMAXCONN

    def server_bind(self) -> None:
        if sys.platform == "win32":
            _set_exclusive(self.socket)
        super().server_bind()

    @override
    def handle_error(self, request, client_address) -> None:
        """What escapes a handler, through logs.py rather than onto stderr.

        socketserver calls this from inside its own `except`, which is where
        the exception being reported comes from.
        """
        logger.error("request from %s failed", client_address, exc_info=sys.exc_info())


def _set_exclusive(s: socket.socket) -> None:
    """Refuse the port to every other socket while this one holds it.

    **The `sys.platform` test belongs inside the function**, not only at the two
    call sites that already have one. `SO_EXCLUSIVEADDRUSE` exists on Windows
    alone, so a body that reads it unconditionally is an unresolved attribute to
    every checker not running on Windows, and `make lint` on a Mac said so:
    *"Module `socket` has no member `SO_EXCLUSIVEADDRUSE`"*. A checker narrows on
    this comparison, so the guard here is the one it can see.

    That is the mirror of the reason `make lint-linux` exists. `sys.platform` is
    a fact at check time: a checker prunes the branches for other platforms,
    which hides what is in them -- and reports what is *outside* a branch as
    missing. Both halves want the platform test where the attribute is read.
    """
    if sys.platform == "win32":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)


def make_server(port: int, session: Session) -> Server:
    """The server, on that port, for the payload `session` and every other
    session share: static files need it before any request names a session."""
    check_ready(session)
    httpd = Server(("127.0.0.1", port), Handler)
    httpd.payload = session.payload
    return httpd


PREFERRED_PORT = 43110


def find_free_port() -> int:
    """The editor's port: the usual one, or any free one if it is taken.

    A second window falls back and forgets its settings. One window remembering
    beats neither, and the alternative is failing to start.
    """
    with socket.socket() as s:
        # SO_REUSEADDR because the previous window's connections sit in
        # TIME_WAIT for a couple of minutes after it closes, and without it a
        # relaunch inside that window silently lands on a different port --
        # which is to say, a different origin with none of the settings.
        # Windows means something else by it: see Server.allow_reuse_address.
        if sys.platform == "win32":
            _set_exclusive(s)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", PREFERRED_PORT))
        except OSError:
            s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def make_editor_url(port: int, session: Session, title: str) -> str:
    """The editor's address, with the session that answers for it.

    doctype is what api.js's appMap turns into an editor directory -- word,
    cell, slide, diagram -- so it, and not the file name, is what decides
    whether Words or Tables comes up. filetype has to agree with it or the
    editor loads and then refuses the document.

    The editor loads itself in an iframe and forwards only the parameters it
    knows, so the session never reaches the inner frame's URL. It does not need
    to: the frames are same-origin, and the bridge reads it off the top window.
    """
    user_id, user_name = lookup_local_user()
    app = session.editor
    mode = "edit" if app.editable else "view"
    ext = pathlib.Path(title).suffix.lstrip(".").lower() or app.ext
    return (
        f"http://127.0.0.1:{port}/web-apps/apps/api/documents/index.html"
        f"?doctype={app.doctype}&mode={mode}&lang=en"
        f"&title={urllib.parse.quote(title)}"
        f"&filetype={ext}&session={urllib.parse.quote(session.id)}"
        f"&userid={urllib.parse.quote(user_id)}"
        f"&username={urllib.parse.quote(user_name)}"
    )
