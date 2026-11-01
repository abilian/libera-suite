"""Who may ask; what every answer says about itself.

The server is on 127.0.0.1, which every page in every browser on this machine
can reach, so this module is security policy.
"""

from __future__ import annotations

import hmac
import http.cookies
import logging
from typing import TYPE_CHECKING

from libera.host import instance
from libera.host.server.api import Refused
from libera.host.session import NotReadyError, Session, lookup

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

# Only our own pages may frame ours. Any site could put the start window in an
# iframe, and a click there sends new, open-recent and open-document with our
# origin, which admit() lets through. 'self' and not 'none': the editor
# frames itself.
FRAME_ANCESTORS = "frame-ancestors 'self'"

# Nothing the page loads or sends goes anywhere but this host, whatever the
# editor's code would like: upstream's bundles still carry an analytics
# loader, and the page sends nothing on its own. The exception is pictures,
# from anywhere: a document can link one by its web address, which is its own
# reference, as in every office suite. What sdkjs needs besides: eval and
# WebAssembly, inline scripts (the editor's pages and the start window have
# them), and blob: and data: for what it builds in memory -- workers, fonts,
# images. Measured by tests/c_e2e/host/test_network.py.
DIRECTIVES = (
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob:",
    "style-src 'self' 'unsafe-inline'",
    "img-src * data: blob:",
    "font-src 'self' data: blob:",
    "connect-src 'self' data: blob:",
    "media-src 'self' data: blob:",
    "worker-src 'self' blob:",
    "frame-src 'self' data: blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    FRAME_ANCESTORS,
)
POLICY = "; ".join(DIRECTIVES)

# On every answer, whichever route or error produced it.
SECURITY_HEADERS = (
    ("Content-Security-Policy", POLICY),
    # The declared type is the type: a browser that sniffed text/plain into
    # HTML would undo the adapter's guarantee that a refused request is
    # answered in plain text.
    ("X-Content-Type-Options", "nosniff"),
    # The key rides in each window's first URL: never in a Referer.
    ("Referrer-Policy", "no-referrer"),
)


def cookie_name(port: str) -> str:
    """The cookie that brings the key back once a window has shown it in its
    first URL: every later request the page makes, its frames, scripts and
    fonts included, sends it without the bridge having to add it.

    Named for the port, because a browser keeps cookies by host and not by
    port, and both copies of Libera Suite share one webview profile. With one
    name, a second copy (a hand-off that timed out) set its key over the
    first's, and every request of the first's that had only the cookie was
    refused.
    """
    return f"libera_key_{port}"


def key_cookie(port: str) -> str:
    """The Set-Cookie value that hands this instance's key to the page."""
    return f"{cookie_name(port)}={instance.TOKEN}; Path=/; HttpOnly; SameSite=Strict"


def admit(
    *,
    headers: Mapping[str, str],
    port: str,
    query: Mapping[str, list[str]],
) -> Session:
    """The session the request is about, if it may be served at all; refused
    otherwise.

    The server is on 127.0.0.1, which every page in every browser on this
    machine can reach, so what a page elsewhere could send is the question.

    **Host must be this server's address.** A page on a name its author
    controls can re-resolve that name to 127.0.0.1 -- DNS rebinding -- and is
    then same-origin with itself, so it reads every answer: the open document,
    the recent list, any file media-import was told to copy in.

    **Origin, when there is one, must be ours.** A browser sends it with every
    POST another page makes; a text/plain one needs no preflight.
    Measured before this check: a request from another origin, with no session
    named, truncated the open document's change log to nothing. Our own pages
    send our origin; the hand-off and the tests send none.

    **Sec-Fetch-Site, when there is one, must say so too.** A GET has no
    Origin, so another site could load `<script src>` from one of our
    addresses and read what it declares: the bridge's prelude says who has the
    open document locked. The browser marks every request it sends with where
    it came from: "same-origin" from our own pages, "none" from no page at all,
    a navigation the user or the application started. "same-site" is not ours:
    another port on 127.0.0.1 is the same site, and another origin.

    **The key must be this instance's**, in the query string or in its cookie.
    The three checks above stop a browser, and nothing else: any process on
    this machine, another account's included, can send whatever headers it
    likes. Measured before this check: `curl` from the command line read the
    open document out of /__host__/opened. The key is `instance.TOKEN`, in the
    window's first URL and, for a second launch, in instance.json, a file only
    this user can read.

    **The session must exist.** Static requests name none and get the first,
    which is harmless because the payload is shared. A request about a
    document names its session and is refused if that session has gone (see
    session.lookup).
    """
    check_browser(headers, port)
    presented = query.get("key", [""])[0] or _key_from(headers.get("Cookie"), port)
    if not hmac.compare_digest(presented.encode(), instance.TOKEN.encode()):
        logger.info("refused: no key, or the wrong one")
        raise Refused(403)
    try:
        return lookup(query.get("session", [""])[0])
    except NotReadyError as e:
        raise Refused(404, str(e)) from e


def check_browser(headers: Mapping[str, str], port: str) -> None:
    """Admission's first three checks, on what a browser sends: Host,
    Origin and Sec-Fetch-Site. Refused unless all three are ours."""
    host, origin = headers.get("Host"), headers.get("Origin")
    fetch_site = headers.get("Sec-Fetch-Site")
    own = f"127.0.0.1:{port}"
    if (
        host != own
        or origin not in {None, f"http://{own}"}
        or fetch_site not in {None, "same-origin", "none"}
    ):
        logger.info(
            "refused: Host %s, Origin %s, Sec-Fetch-Site %s", host, origin, fetch_site
        )
        raise Refused(403)


def _key_from(cookie: str | None, port: str) -> str:
    jar = http.cookies.SimpleCookie(cookie or "")
    found = jar.get(cookie_name(port))
    return found.value if found else ""
