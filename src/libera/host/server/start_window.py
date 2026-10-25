"""The start window: its page, the editors it offers, and where the payload
came from.
"""

from __future__ import annotations

import html
import json
import pathlib
import re

from libera.host import apps, language
from libera.host.server.api import Request, Response, answer_json, endpoint


@endpoint("GET", "start")
def serve_start(_r: Request) -> Response:
    """The start window's page, ours: the payload has none.

    Upstream keeps its start screen in the C++ shell, so there is nothing to
    reuse: this is a plain page served by the host, talking to the same
    /__host__/ endpoints the editor does. It loads none of the bridge, sdkjs
    or the theme.
    """
    page = pathlib.Path(__file__).with_name("start-window.html")
    filled = fill_in(page.read_text(encoding="utf-8"))
    return Response(body=filled.encode(), content_type="text/html; charset=utf-8")


# The page's text, as `{{English}}`, and where its script finds the rest.
MARKED = re.compile(r"\{\{(.+?)\}\}")
STRINGS = "/* LIBERA_STRINGS */ {}"


def fill_in(page: str) -> str:
    """The start window in the interface language: its marked text translated,
    and the catalogue handed to its script, whose `tr` looks the rest up."""
    page = MARKED.sub(lambda m: html.escape(language.translate(m[1])), page)
    lang = language.get_interface_language()
    direction = "rtl" if lang in language.RIGHT_TO_LEFT else "ltr"
    page = page.replace('<html lang="en">', f'<html lang="{lang}" dir="{direction}">')
    return page.replace(STRINGS, json.dumps(language.get_catalogue()))


@endpoint("GET", "apps")
def serve_apps(_r: Request) -> Response:
    """The editors, for a page that offers to make a new document."""
    body = [
        {
            "name": app.name,
            "kind": language.translate(app.noun),
            "doctype": app.doctype,
            "ext": app.ext,
            "creates": app.blank is not None,
        }
        for app in apps.ALL
    ]
    return answer_json(body)


@endpoint("GET", "payload")
def serve_payload(r: Request) -> Response:
    """Where the payload came from, for the start window to show.

    The same facts `libera --payload-status` prints. Read from the installed
    payload's own payload.json, so a development tree reports that it
    knows nothing.
    """
    # Imported here, since this is the only thing that wants the installer and
    # `libera --serve` runs the host without it.
    from libera import payload as payload_mod

    # Unreadable is not the same as absent: a payload.json that will not parse
    # was shown as "local build", which is what a tree with none is told.
    marker = r.session.layout.record
    info = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
    body = {
        "root": str(r.session.payload),
        # How this process found it -- LIBERA_PAYLOAD, a config file, or the
        # installed copy -- which is not in payload.json because it is not a
        # property of the payload.
        "origin": payload_mod.resolve().origin,
        "version": info.get("payload_version") or language.translate("local build"),
        "platform": info.get("platform"),
        "built": info.get("built"),
    }
    return answer_json(body)
