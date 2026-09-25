"""The host opens URLs on the desktop, so the page must not choose the scheme.

The editor asks the host to open external links because WKWebView drops
script-opened windows. That hands page content a lever on the desktop, and the
only thing between the two is this check.

`desktop.open_url` is stubbed here rather than `subprocess`: the endpoint's job
is to decide *whether* a URL reaches the desktop, and that is the boundary
worth pinning. How the desktop is asked, and whether it agreed, belongs to
test_desktop_open_url.py beside it.
"""

from __future__ import annotations

import pytest

from libera.host import desktop, server


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
    """Every URL that reached the desktop."""
    urls: list[str] = []
    monkeypatch.setattr(desktop, "open_url", lambda url: urls.append(url) or True)
    return urls


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
    assert launched == [url]


def test_the_page_is_told_nothing_when_the_desktop_refuses(monkeypatch):
    """A desktop with no handler is the desktop's business, not the page's.

    There is nothing useful a page can do about it, and telling it would hand
    page content a way to probe what the machine has installed.
    """
    monkeypatch.setattr(desktop, "open_url", lambda _url: False)
    h = FakeHandler(b"https://example.com/x")

    server.post_open_url(h)

    assert h.status == 204
