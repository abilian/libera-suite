"""One Libera Suite per user: a second launch hands its documents to the first.

Double-clicking a second document starts a second process, and a second
process cannot share the first one's port -- so it would come up on another
origin, which is another localStorage, which is an editor that has forgotten
its theme, its units and every tip it has shown. It would also be a second
icon in the taskbar for what the user thinks of as one application.

So the running instance says where it is, in `instance.json` under the state
directory, and a later `libera FILE...` posts the paths to it and exits.

The file carries a random token, and the endpoint wants it. The server is on
127.0.0.1, where any web page the user visits can send it a POST; only a
process running as this user can read the token.
"""

from __future__ import annotations

import contextlib
import ctypes
import hmac
import json
import logging
import os
import secrets
import sys
import urllib.request
from typing import TYPE_CHECKING

from libera.payload import locate

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Long enough for a busy instance to answer, short enough that a stale file
# -- a crash left it, and nothing listens on that port now -- costs a user
# double-clicking a document no noticeable wait.
HAND_OFF_TIMEOUT = 3.0

TOKEN = secrets.token_urlsafe(32)


def get_path() -> Path:
    return locate.get_state_dir() / "instance.json"


def announce(port: int) -> None:
    """Say where this instance is. Called once the server is listening."""
    target = get_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_suffix(".tmp")
    staged.write_text(
        json.dumps({"port": port, "token": TOKEN, "pid": os.getpid()}),
        encoding="utf-8",
    )
    staged.replace(target)
    logger.info("instance: announced on port %d", port)


def withdraw() -> None:
    """Remove the announcement, if it is still ours. Called on the way out.

    Only ours: a second instance that could not reach this one (it was busy
    starting) announces itself over the top, and the first one to exit must
    not take the survivor's announcement with it.
    """
    with contextlib.suppress(OSError, ValueError):
        if json.loads(get_path().read_text(encoding="utf-8")).get("token") == TOKEN:
            get_path().unlink()


def is_own_token(token: str) -> bool:
    """Whether a hand-off request carries this instance's token."""
    return hmac.compare_digest(token.encode(), TOKEN.encode())


def hand_off(documents: list[Path]) -> bool:
    """Give the documents to a running instance. True means it took them.

    False means there is none to take them -- no announcement, or one that
    nothing answers -- and the caller starts the application itself. With no
    documents the running instance puts its start window up, which is what
    clicking the icon of an application that is already open does elsewhere.
    """
    try:
        known = json.loads(get_path().read_text(encoding="utf-8"))
        port, token = int(known["port"]), str(known["token"])
    except (OSError, ValueError, KeyError, TypeError):
        return False

    _allow_foreground()
    body = json.dumps({"token": token, "documents": [str(d) for d in documents]})
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/__host__/hand-off",
        data=body.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HAND_OFF_TIMEOUT) as answer:
            took = json.loads(answer.read()).get("opened") is True
    except (OSError, ValueError) as e:
        logger.info("instance: none answering on port %d (%s)", port, e)
        return False
    logger.info("instance: handed %d document(s) to port %d", len(documents), port)
    return took


def _allow_foreground() -> None:
    """Let the running instance bring its new window to the front.

    Windows gives foreground rights to the process the user just started --
    this one -- and refuses them to a background process that asks for them,
    so a window the first instance opens would otherwise appear behind
    whatever was in front, with a flashing taskbar button. ASFW_ANY hands the
    right on. Elsewhere there is nothing to hand.
    """
    # A block, not an early return: see desktop._start.
    if sys.platform == "win32":
        asfw_any = -1
        with contextlib.suppress(Exception):
            ctypes.windll.user32.AllowSetForegroundWindow(asfw_any)
