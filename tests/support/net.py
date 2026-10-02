"""A port for a test server, which nothing else is listening on."""

from __future__ import annotations

import socket


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])
