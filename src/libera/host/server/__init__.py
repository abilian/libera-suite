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

from libera.host.server.get import BRIDGE_PARTS, host_get, owned_keys
from libera.host.server.handler import (
    Handler,
    Server,
    check_ready,
    editor_url,
    free_port,
    make_server,
)
from libera.host.server.post import (
    broken,
    create_new,
    post_can,
    post_open_url,
)
from libera.host.server.state import (
    ERRORS,
    MEDIA_SERVED,
    NOT_FOUND,
    OFFERED,
    ROUTES,
    SEEN,
    host_report,
)

__all__ = [
    "BRIDGE_PARTS",
    "ERRORS",
    "MEDIA_SERVED",
    "NOT_FOUND",
    "OFFERED",
    "ROUTES",
    "SEEN",
    "Handler",
    "Server",
    "broken",
    "check_ready",
    "create_new",
    "editor_url",
    "free_port",
    "host_get",
    "host_report",
    "make_server",
    "owned_keys",
    "post_can",
    "post_open_url",
]
