"""The desktop host: a loopback server and a window, around the editor payload.

The layers, innermost first, and nothing imports anything above it:

    apps       the four editors, and the five things that differ between them
    shortcuts  the key equivalents the menu bar owns, and the page yields
    session    who is editing what, bound per request
    hooks      callbacks the window layer installs
    desktop    reveal a file, open a URL, whose account this is
    convert    x2t: documents in, documents out
    recents    the Recent list
    opening    opening a document into a session
    server     HTTP: routing, endpoints, the injected bridge
    window     windows, dialogs, the close prompt
    menu       the macOS menu bar
    app        run(): the server, the first windows, the menu

`tests/a_unit/test_layering.py` checks that order against the real import
graph, so this is a contract rather than a description. Two edges used to
break it, both hidden behind function-level imports -- `server` and `window`
reaching up to `menu`. `shortcuts` and `app` are where the things they were
reaching for went.
"""

from __future__ import annotations

from libera.host.server import make_server
from libera.host.session import Host

__all__ = ["Host", "make_server"]
