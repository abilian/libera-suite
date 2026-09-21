"""The editor's port is its origin, and its origin is where its settings live.

localStorage is keyed by origin, so a random port each launch means the editor
forgets its theme, its units, its spellcheck language and every tip it has been
shown. These pin the stable-port behaviour and its fallback.

Both borrow a port rather than trusting PREFERRED_PORT to be free: a developer
with Libera Suite open would otherwise fail the suite.
"""

from __future__ import annotations

import socket

import pytest

from libera.host import server


@pytest.fixture
def spare_port():
    """A port the kernel just said was free."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_prefers_the_stable_port(monkeypatch, spare_port):
    monkeypatch.setattr(server.handler, "PREFERRED_PORT", spare_port)
    assert server.free_port() == spare_port


def test_falls_back_when_the_stable_port_is_taken(monkeypatch):
    """A second window has to open, even at the cost of its own settings."""
    held = socket.socket()
    # What a real second instance holds it with: HTTPServer.allow_reuse_address.
    held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    held.bind(("127.0.0.1", 0))
    held.listen(1)
    taken = int(held.getsockname()[1])
    monkeypatch.setattr(server.handler, "PREFERRED_PORT", taken)
    try:
        port = server.free_port()
    finally:
        held.close()

    assert port != taken
    assert port > 0
