"""The host opens URLs on the desktop, so the page must not choose the scheme.

The editor asks the host to open external links because WKWebView drops
script-opened windows. That hands page content a lever on the desktop, and the
only thing between the two is this check.
"""

from __future__ import annotations

import pytest

from libera.host import server


class FakeHandler:
    """Just enough of the request handler for post_open_url."""

    def __init__(self, body: bytes):
        self._body = body
        self.status = None
        self.opened = False

    def body(self) -> bytes:
        return self._body

    def send_error(self, code):
        self.status = code

    def no_content(self):
        self.status = 204


@pytest.fixture
def launched(monkeypatch):
    """Record what would have been handed to the desktop."""
    calls = []
    monkeypatch.setattr(
        server.post.subprocess, "run", lambda cmd, **_: calls.append(cmd)
    )
    return calls


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<script>x</script>",
        "  ",
        "https://example.com/ with space",
        "ssh://box/x",
    ],
)
def test_refuses_anything_but_http(url, launched):
    h = FakeHandler(url.encode())
    server.post_open_url(h)
    assert h.status == 400
    assert launched == []


@pytest.mark.parametrize("url", ["https://example.com/x", "http://example.com/"])
def test_opens_http(url, launched):
    h = FakeHandler(url.encode())
    server.post_open_url(h)
    assert h.status == 204
    assert len(launched) == 1
    assert launched[0][-1] == url
