"""The loopback HTTP server the editor talks to.

By what is asked for, in this order, nothing importing upward:

    api            what an endpoint is: @endpoint, Request, Response
    diagnostics    what the host was asked for and could not answer
    start_window   the start window: its page, the editors, the payload
    spelling       the personal dictionary
    editor         the editor's page: its bridge, its reports, its address
    document       the open document: handing it over, its edits, saving it
    opening        getting documents into windows: open, recent, new
    payload_files  the payload as static files, the bridge spliced in
    admission      who may ask; the headers on every answer
    routes         the host API: the marked endpoints, gathered into a table
    adapter        the only module that knows the web framework
    listener       the socket, the threads, the port

Endpoints are functions from a `api.Request` to a `api.Response`,
marked `@endpoint(method, name)` where they are defined. In the five domain
modules a marked name is an entry point, an underscored one a helper, and any
other is used elsewhere in the host.

The names below are the surface. Mutable state is re-exported by reference, so
`server.ASKED` and `diagnostics.ASKED` are the same dict and a test that reads
either sees what the other wrote.
"""

from __future__ import annotations

from libera.host.server.diagnostics import (
    ASKED,
    ERRORS,
    MEDIA_SERVED,
    NOT_FOUND,
    SEEN,
    build_report,
)
from libera.host.server.editor import (
    BRIDGE_PARTS,
    handle_editor_error,
    list_owned_keys,
    make_editor_url,
    open_url,
    record_abilities,
)
from libera.host.server.listener import (
    Server,
    check_ready,
    find_free_port,
    make_server,
)
from libera.host.server.opening import create_new

__all__ = [
    "ASKED",
    "BRIDGE_PARTS",
    "ERRORS",
    "MEDIA_SERVED",
    "NOT_FOUND",
    "SEEN",
    "Server",
    "build_report",
    "check_ready",
    "create_new",
    "find_free_port",
    "handle_editor_error",
    "list_owned_keys",
    "make_editor_url",
    "make_server",
    "open_url",
    "record_abilities",
]
