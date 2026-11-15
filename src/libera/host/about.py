"""Who wrote what, in one place, for everything that has to say so.

Three surfaces need the same sentences and used to hold their own copy: the
editor's own About panel (through the theme's `about.json`, which is
build-time and lives in `build/payload/theme/libera/meta/`), the macOS About
panel (through `NSHumanReadableCopyright`), and Help > About on Linux. A fourth,
`--payload-status`, prints the revisions instead of the prose.

The text lives here, in one copy, because the attribution is the one string in
this application that has to be *correct* as well as present: it names somebody
else's work, says the build is modified, and names the licence that requires
both. Three copies drift; the one that drifts is the copy no one reads until it
matters.

**"includes components from", not "is based on".** The host is ours and original;
what comes from upstream is the editor payload. "Based on" invites the reading
that the whole application is a derivative of theirs, which overstates their
claim and understates ours. The payload is a modified AGPL work, which is what
these lines say.

The layer below every other: this module imports nothing from the host, so
anything may read it.
"""

from __future__ import annotations

import importlib.metadata

from libera.payload import locate

SOURCE_URL = "https://github.com/abilian/libera-suite"

#: The one-paragraph notice. Names the original developer, says the components
#: are modified, names the licence, and points at the source. Short enough for
#: the editor's About panel, which centres it as a single label.
ATTRIBUTION = (
    "Libera Suite includes components from Euro-Office, itself a fork of "
    "ONLYOFFICE by Ascensio System SIA. Those components are free software "
    "under the GNU AGPL v3 and are modified. The exact upstream revisions this "
    f"build came from, and every change applied to them: {SOURCE_URL}"
)

#: The macOS About panel and the Flatpak's AppStream metadata both want one
#: line. `libera --payload-status` prints the revisions the long form promises.
COPYRIGHT = (
    "Copyright (c) 2026 Abilian SAS. Includes modified AGPL v3 components from "
    "Euro-Office, a fork of ONLYOFFICE by Ascensio System SIA."
)


def app_version() -> str:
    return importlib.metadata.version("libera")


def format_version() -> str:
    """The application and the payload it wants: what `--version` prints and
    every About says.

    Both, because the two move independently: a host fix should not force a
    120 MB re-download, nor a payload rebuilt from new upstream pins need a host
    release. A bug report that names only one of them does not say which pair
    was in play. `--diagnose` prints these and much more; this is
    the line somebody pastes into an issue.
    """
    return f"libera {app_version()} (payload {locate.PAYLOAD_VERSION})"


def format_notice() -> str:
    """The About dialog's body: which versions, then the attribution, then
    where to look. A bug report needs the versions, where About used to say
    only who wrote what."""
    return (
        f"{format_version()}\n\n"
        f"{ATTRIBUTION}\n\n"
        "The host is Apache-2.0. Run `libera --payload-status` for the exact "
        "revisions of every upstream repository this payload was built from."
    )
