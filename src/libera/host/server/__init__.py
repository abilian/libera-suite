"""The loopback HTTP server the editor talks to.

    state     what the host has been asked for, and what it could not answer
    get       the bridge, and what the page asks about itself
    post      the editor asking the host to do something
    handler   the socket, the dispatch, the bridge splice

One 690-line module became four, in that order, and nothing imports upward
except `post`'s type annotation of the handler -- which is a TYPE_CHECKING
import and therefore not one at runtime.

The names below are the surface. Mutable state is re-exported by reference, so
`server.ROUTES` and `state.ROUTES` are the same dict and a test that reads
either sees what the other wrote.
"""

from __future__ import annotations

from libera.host.server.get import BRIDGE_PARTS, list_owned_keys, serve
from libera.host.server.handler import (
    Handler,
    Server,
    check_ready,
    find_free_port,
    make_editor_url,
    make_server,
)
from libera.host.server.post import (
    create_new,
    handle_editor_error,
    open_url,
    record_abilities,
)
from libera.host.server.state import (
    ERRORS,
    MEDIA_SERVED,
    NOT_FOUND,
    ROUTES,
    SEEN,
    build_report,
)

__all__ = [
    "BRIDGE_PARTS",
    "ERRORS",
    "MEDIA_SERVED",
    "NOT_FOUND",
    "ROUTES",
    "SEEN",
    "Handler",
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
    "serve",
]
