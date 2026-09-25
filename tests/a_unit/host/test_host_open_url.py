"""The host opens URLs on the desktop, so the page must not choose the scheme.

The editor asks the host to open external links because WKWebView drops
script-opened windows. That hands page content a lever on the desktop, and the
only thing between the two is this check.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

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


def desktop_answering(monkeypatch, returncode: int) -> list:
    """Stand in for the desktop, recording what it was asked to open.

    The stub answers with a `returncode`, because `post_open_url` reads one.
    A stub returning None passed for as long as the status was ignored, and
    became an AttributeError the moment it stopped being.
    """
    calls: list = []

    def fake_run(cmd, **_):
        calls.append(cmd)
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(server.post.subprocess, "run", fake_run)
    return calls


@pytest.fixture
def launched(monkeypatch):
    """A desktop that opens what it is given."""
    return desktop_answering(monkeypatch, 0)


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


def test_a_desktop_with_no_handler_is_logged_rather_than_hidden(monkeypatch, caplog):
    """xdg-open exits non-zero when nothing will take the link.

    That happened for real: a Flatpak on a machine with no browser reached the
    portal, the portal found no handler, and the log said `open-url -> …` as
    though the link had opened. The page still gets its 204, because there is
    nothing useful for it to do about the desktop's configuration.
    """
    desktop_answering(monkeypatch, 3)
    h = FakeHandler(b"https://example.com/x")

    with caplog.at_level(logging.WARNING, logger="libera.host.server.post"):
        server.post_open_url(h)

    assert h.status == 204, "the page is told nothing either way"
    assert caplog.records, "a link that opened nothing was reported as success"
    assert "3" in caplog.text, f"the status is not in the log line: {caplog.text!r}"
