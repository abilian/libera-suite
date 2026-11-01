"""The socket: the server the adapter's application runs on, one thread per
request, and the port it listens on.
"""

from __future__ import annotations

import logging
import socket
import socketserver
import sys
from typing import TYPE_CHECKING, Any, override
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

from libera.host.server import adapter
from libera.host.session import NotReadyError

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)


def check_ready(session: Session) -> None:
    """Fail early and legibly, before every asset 404s.

    The payload only. Editor.bin is session state; a start window has no
    document and therefore no Editor.bin -- opening one creates it and reports
    its own failure.
    """
    for path in (session.payload, session.layout.web_all_fonts):
        if not path.exists():
            msg = f"missing: {path}"
            raise NotReadyError(msg)
    if not any(session.layout.fonts.glob("*")):
        msg = f"no fonts in {session.layout.fonts}"
        raise NotReadyError(msg)


class QuietHandler(WSGIRequestHandler):
    """wsgiref's handler, without its line per request on stderr:
    `_log_answer` does the logging."""

    @override
    def log_message(self, format: str, *args: Any) -> None:
        pass


class Server(socketserver.ThreadingMixIn, WSGIServer):
    """The server: a thread per request, as http.server's was."""

    daemon_threads = True

    # On Windows a listener rebinds through TIME_WAIT without SO_REUSEADDR,
    # which there lets a second socket bind a port another is already
    # listening on. Two instances would then share PREFERRED_PORT
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

    @override
    def server_bind(self) -> None:
        if sys.platform == "win32":
            _set_exclusive(self.socket)
        super().server_bind()

    @override
    def handle_error(self, request: Any, client_address: Any) -> None:
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
    missing. Both cases want the platform test where the attribute is read.
    """
    if sys.platform == "win32":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)


def make_server(port: int, session: Session) -> Server:
    """The server, on that port, for the payload `session` and every other
    session share: static files need it before any request names a session."""
    check_ready(session)
    httpd = Server(("127.0.0.1", port), QuietHandler)
    httpd.set_app(adapter.make_app(session.payload))
    return httpd


PREFERRED_PORT = 43110


def find_free_port() -> int:
    """The editor's port: the usual one, or any free one if it is taken.

    A second window falls back and forgets its settings. One window remembering
    beats neither; the alternative is failing to start.
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
