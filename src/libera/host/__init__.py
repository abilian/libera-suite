"""The desktop host: a loopback server and a window, around the editor payload.

The layers, innermost first, and nothing imports anything above it:

    about      who wrote what: the attribution every surface has to say
    language   the user's language and region: the editor's, and the blank's
    apps       the four editors, and the six things that differ between them
    shortcuts  the key equivalents the menu bar owns, and the page yields
    changelog  every edit since a document was opened
    session    one window: its files, its document, what the host knows of it
    hooks      the shell: what the host asks of whoever owns the windows
    desktop    reveal a file, open a URL, whose account this is
    updates    once a day, whether a newer version is out
    instance   one running copy: a second launch hands its documents over
    locking    lock files: a document open here, or open somewhere else
    convert    x2t: documents in, documents out
    saving     what a save request means, and doing the save
    recents    the Recent list
    opening    opening a document into a session, and recovering a crash
    server     HTTP: routing, endpoints, the injected bridge
    window     windows, dialogs, the close prompt
    menu       the menu bar
    app        run(): the server, the first windows, the menu

`tests/a_unit/host/test_layering.py` checks that order against the real import
graph, so this list is a contract. Two edges used to break it, both hidden
behind function-level imports: `server` and `window` reaching up to `menu`. The
things they were reaching for went to `shortcuts` and `app`.
"""

from __future__ import annotations

from libera.host.server import make_server
from libera.host.session import Session

__all__ = ["Session", "make_server"]
