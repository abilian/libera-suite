"""The one module that knows the web framework.

Bottle, which pywebview already depends on, so it costs nothing to ship. This
module copies what an endpoint needs out of Bottle's request into a
`api.Request`, finds the endpoint in `routes`, and turns the
`api.Response` it returns into Bottle's. Bottle's own `request` belongs to
the thread serving it -- the shape every thread bug in this host had -- so it is
read here and nowhere else, and `tests/a_unit/host/test_layering.py` holds that.
Swapping the framework changes this module alone.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import TYPE_CHECKING, Any

import bottle

from libera import logs, timeline
from libera.host.server import admission, diagnostics, payload_files, routes
from libera.host.server.api import Refused, Request, Response

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable, Iterable

    from libera.host.session import Session

logger = logging.getLogger(__name__)


def make_app(payload: pathlib.Path) -> Callable[..., Iterable[bytes]]:
    """The WSGI application: the host API, the service worker, and the payload."""
    app = bottle.Bottle()

    @app.route("/__host__/<name:path>", method=["GET", "POST"])
    def host(name: str) -> bottle.HTTPResponse:
        method = bottle.request.method

        def answer(session: Session) -> Response:
            found = routes.find_route(method, name)
            if found is None:
                raise Refused(404)
            endpoint, matched, rest = found
            # Admitted and routed: a name another origin made up is not a key.
            if method == "POST":
                diagnostics.count(diagnostics.ASKED, matched)
            return endpoint(_make_request(session, matched, rest))

        return _answer(answer)

    @app.route("/document_editor_service_worker.js", method=["GET", "HEAD"])
    def service_worker() -> bottle.HTTPResponse:
        return _answer(
            lambda session: payload_files.serve_service_worker(Request(session))
        )

    @app.route("/<path:path>", method=["GET", "HEAD"])
    def static(path: str) -> bottle.HTTPResponse:
        if_none_match = bottle.request.headers.get("If-None-Match", "")
        return _answer(
            lambda session: payload_files.serve_file(
                payload, path, if_none_match, session.fonts
            )
        )

    return _with_headers(app)


def _make_request(session: Session, name: str, path: str) -> Request:
    req = bottle.request
    return Request(
        session,
        body=req.body.read() if req.method == "POST" else b"",
        query=_parse_query(),
        name=name,
        path=path,
    )


def _parse_query() -> dict[str, list[str]]:
    return urllib.parse.parse_qs(bottle.request.query_string, keep_blank_values=True)


def _answer(endpoint: Callable[[Session], Response]) -> bottle.HTTPResponse:
    """Admit the request, run the endpoint, and answer for it when it fails.

    The one place a request's failure is caught: a route that raised used to
    close the connection with no answer, which the editor sees as a network
    fault. A refused request is answered with its status, admission's or the
    endpoint's; anything else is a 500 -- logged, with the traceback.
    """
    req = bottle.request
    timeline.mark("first-request")
    query = _parse_query()
    port = str(req.environ["SERVER_PORT"])
    try:
        session = admission.admit(headers=req.headers, port=port, query=query)
        answer = endpoint(session)
    except Refused as e:
        return _to_bottle(_refusal(e.status, e.explain))
    except Exception:
        logger.exception("%s %s failed", req.method, req.path)
        return _to_bottle(_refusal(500))
    response = _to_bottle(answer)
    # A window's first page: the key came in its URL, and from now on the
    # cookie brings it.
    if "key" in query:
        response.set_header("Set-Cookie", admission.key_cookie(port))
    return response


# A refused request's answer can echo what it was sent -- an unknown session
# says which -- so it is never served as a page: as HTML, a script sent as a
# session id would run in our origin, where our own endpoints take its requests.
PLAIN_TEXT = "text/plain; charset=utf-8"


def _refusal(status: int, explain: str = "") -> Response:
    return Response(status, explain=explain, content_type=PLAIN_TEXT)


def _to_bottle(answer: Response) -> bottle.HTTPResponse:
    headers = dict(answer.headers)
    if answer.content_type:
        headers["Content-Type"] = answer.content_type
    # What the host answers describes the moment it was asked.
    headers.setdefault("Cache-Control", "no-store")
    if answer.file is not None:
        headers["Content-Length"] = str(answer.file.stat().st_size)
        return bottle.HTTPResponse(answer.file.open("rb"), answer.status, headers)
    return bottle.HTTPResponse(answer.body or answer.explain, answer.status, headers)


def _with_headers(app: bottle.Bottle) -> Callable[..., Iterable[bytes]]:
    """The headers on every answer and the log line of every request, whichever
    route or error produced it."""

    def wrapped(environ: dict[str, Any], start_response: Callable[..., Any]) -> Any:
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "")
        if logs.is_tracing_requests():
            logger.debug("%.3f asked %s %s", time.time(), method, path)

        def start(status: str, headers: list[tuple[str, str]], *rest: Any) -> Any:
            names = {name.lower() for name, _ in headers}
            headers.extend(admission.SECURITY_HEADERS)
            if "cache-control" not in names:
                headers.append(("Cache-Control", "no-cache"))
            _log_answer(int(status.split(maxsplit=1)[0]), path)
            return start_response(status, headers, *rest)

        try:
            return app(environ, start)
        finally:
            if logs.is_tracing_requests():
                logger.debug("%.3f done %s %s", time.time(), method, path)

    return wrapped


def _log_answer(code: int, path: str) -> None:
    if code == diagnostics.NOT_FOUND_CODE:
        diagnostics.NOT_FOUND.add(path)
    # 304 is the ETag answer: the webview already holds that file.
    if code in {200, 204, 304}:
        return
    # A 404 is usually the editor asking for something we chose not to ship --
    # its help, its plugins -- and the e2e suite checks the whole set of them
    # anyway. Anything else went wrong.
    logger.log(
        logging.DEBUG if code == diagnostics.NOT_FOUND_CODE else logging.WARNING,
        "%s %s",
        code,
        path,
    )
