"""The host API, pinned: every address the bridge and the start window call.

Endpoints are marked where they are defined (`@endpoint`) and gathered by
`server.routes`. A mark lost in an edit would leave an address quietly
answering 404, which the editor sees as a network fault, and a stray one would
open an address nobody meant to. Either way the list changes, and this fails.
"""

from __future__ import annotations

from libera.host.server import routes

API = {
    # The open document.
    ("GET", "opened"),
    ("GET", "current"),
    ("POST", "changes"),
    ("POST", "modified"),
    ("POST", "save"),
    ("POST", "close"),
    ("POST", "reveal"),
    ("POST", "media-import"),
    # Getting documents into windows.
    ("GET", "recents"),
    ("POST", "choose-file"),
    ("POST", "open-document"),
    ("POST", "open-recent"),
    ("POST", "drop"),
    ("POST", "new"),
    ("POST", "hand-off"),
    # The editor's page.
    ("GET", "bridge-runtime.js"),
    ("GET", "bridge-page.js"),
    ("GET", "bridge-desktop.js"),
    ("POST", "can"),
    ("POST", "page-log"),
    ("POST", "fullscreen"),
    ("POST", "open-url"),
    # The personal dictionary.
    ("GET", "words"),
    ("POST", "words"),
    # The start window.
    ("GET", "start"),
    ("GET", "apps"),
    ("GET", "payload"),
    # The regression harness.
    ("GET", "report"),
    ("POST", "shot"),
}
PREFIXES = {("GET", "media"), ("GET", "fonts")}


def test_the_api_is_exactly_what_the_page_calls():
    assert set(routes.ROUTES) == API
    assert set(routes.PREFIX_ROUTES) == PREFIXES


def test_no_address_is_claimed_twice():
    claimed = [(e.method, n, e.prefix) for e in routes.ENDPOINTS for n in e.names]
    assert len(claimed) == len(set(claimed))
