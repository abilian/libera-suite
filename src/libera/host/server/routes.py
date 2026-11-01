"""The host API: every address under /__host__/, the method it takes, and the
endpoint that answers it.

Each endpoint says so where it is defined, with `@endpoint(method, name)`;
this module gathers them from the modules that make up the API, and from
nothing else. `tests/a_unit/host/test_routes.py` pins the whole list, so an
endpoint that lost its mark, or gained one, is a failing test where it would
otherwise be an address that stopped answering without a word.

The method belongs to the route: a GET never changes anything, and admission
leans on that -- another site's page cannot send a POST without an Origin,
which admission refuses.
"""

from __future__ import annotations

from libera.host.server import (
    diagnostics,
    document,
    editor,
    opening,
    payload_files,
    spelling,
    start_window,
)
from libera.host.server.api import Endpoint

MODULES = (
    document,
    opening,
    editor,
    spelling,
    start_window,
    diagnostics,
    payload_files,
)

ENDPOINTS = tuple(
    found
    for module in MODULES
    for found in vars(module).values()
    if isinstance(found, Endpoint)
)

ROUTES: dict[tuple[str, str], Endpoint] = {
    (e.method, name): e for e in ENDPOINTS if not e.prefix for name in e.names
}

# Routes with a name after them: media/photo.png, fonts/012.
PREFIX_ROUTES: dict[tuple[str, str], Endpoint] = {
    (e.method, name): e for e in ENDPOINTS if e.prefix for name in e.names
}


def find_route(method: str, name: str) -> tuple[Endpoint, str, str] | None:
    """The endpoint for `method /__host__/name`, the name it matched, and what
    follows a prefix."""
    exact = ROUTES.get((method, name))
    if exact is not None:
        return exact, name, ""
    prefix, _, rest = name.partition("/")
    found = PREFIX_ROUTES.get((method, prefix))
    return (found, prefix, rest) if found is not None else None
