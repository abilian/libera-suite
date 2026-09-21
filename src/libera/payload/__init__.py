"""The editor payload: finding one, building one, installing one.

    locate     where a payload is, and whether it is the right one
    generate   the parts that can only be built on this machine
    installer  fetch, verify, unpack, generate, put in place

One module per verb, in that order, and nothing imports upward. What was one
442-line module is three that each answer one question.

The names below are the package's surface and are re-exported so that
`payload.resolve(...)` still reads the way it did. Code *inside* the package
goes through the module -- `locate.data_dir()` -- because a test that replaces
a name has to replace it for every caller.

`installer`, not `install`: the package re-exports `install()` and a module of
that name would be shadowed by it, so `payload.install.bundled_manifest` would
be an attribute lookup on a function. `generate` keeps its name because
nothing outside the package calls it.
"""

from __future__ import annotations

from libera.payload.installer import (
    DEFAULT_ORIGIN,
    bundled_manifest,
    can_fetch,
    install,
    safe_extract,
)
from libera.payload.locate import (
    PAYLOAD_VERSION,
    Payload,
    PayloadError,
    config_file,
    current_platform,
    data_dir,
    looks_complete,
    resolve,
    sessions_dir,
    state_dir,
)

__all__ = [
    "DEFAULT_ORIGIN",
    "PAYLOAD_VERSION",
    "Payload",
    "PayloadError",
    "bundled_manifest",
    "can_fetch",
    "config_file",
    "current_platform",
    "data_dir",
    "install",
    "looks_complete",
    "resolve",
    "safe_extract",
    "sessions_dir",
    "state_dir",
]
