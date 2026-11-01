"""The editor payload: finding it, and building what it cannot ship.

    locate     where the payload is, and whether it is the right one
    generate   the converter's configuration, and running allfontsgen
    fonts      the fonts' indexes, in the state folder
    leftovers  what 0.6 and earlier downloaded, removed when asked

One module per verb, in that order, and nothing imports upward. From 0.7 the
payload is two packages, libera-core and libera-web, which pip installs with
libera; nothing here downloads anything.

The names below are the package's surface and are re-exported so that
`payload.resolve(...)` still reads the way it did. Code *inside* the package
goes through the module -- `locate.get_data_dir()` -- because a test that replaces
a name has to replace it for every caller.
"""

from __future__ import annotations

from libera.payload.locate import (
    PAYLOAD_VERSION,
    Payload,
    PayloadError,
    get_current_platform,
    get_data_dir,
    get_named_config,
    get_sessions_dir,
    get_state_dir,
    is_complete,
    resolve,
)

__all__ = [
    "PAYLOAD_VERSION",
    "Payload",
    "PayloadError",
    "get_current_platform",
    "get_data_dir",
    "get_named_config",
    "get_sessions_dir",
    "get_state_dir",
    "is_complete",
    "resolve",
]
