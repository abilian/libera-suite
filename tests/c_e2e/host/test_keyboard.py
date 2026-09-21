"""What the page does with a keystroke the menu bar also owns.

Cmd-N has been wrong twice: once making two windows because the page acted as
well as the menu, once making none because the page claimed the key instead of
merely declining it. Both were in this JavaScript, and a browser can drive it.

What a browser cannot do is *be* AppKit. These tests cover the page's half of
the contract -- given what the host says the menu owns, does the page act or
not -- and nothing here says whether the menu then fires. That half needs a
real application; see notes/04-plan.md.

The server runs in-process rather than as `libera --serve`, because the whole
point is to vary what the host tells the page, and a subprocess with no window
always reports an empty list.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import urllib.request
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Error, sync_playwright

from libera import payload as payload_mod
from libera.host import menu, opening, server, session as sessions
from libera.host.session import Host

if TYPE_CHECKING:
    from collections.abc import Iterator

# The editor takes a while to be ready for a keystroke, and a key pressed at a
# page that has not finished booting tells us nothing.
READY = 180_000


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Editor:
    """A loaded editor, and what the host was asked to do while it ran."""

    def __init__(self, page, port: int) -> None:
        self.page = page
        self._calls = f"http://127.0.0.1:{port}/__host__/calls"

    def report(self) -> dict:
        with urllib.request.urlopen(self._calls, timeout=30) as r:
            return json.load(r)

    def asked_for(self, route: str) -> int:
        return self.report()["routes"].get(route, 0)

    def wait_until_ready(self) -> None:
        self.page.wait_for_function(
            "() => { const f = document.querySelector('iframe');"
            "return f && f.contentWindow && f.contentWindow.Asc"
            " && f.contentWindow.Asc.editor; }",
            timeout=READY,
        )

    def claimed(self, key: str) -> bool:
        """Did anything in the page call preventDefault on that keystroke?

        This is what tells AppKit "the page took it", and a page that claims a
        key the menu bar owns stops the menu firing -- which is how Cmd-N went
        from two windows to none. Chromium has no menu bar to observe, but the
        event records the claim either way.
        """
        # Every frame, because the editor is in the iframe and that is where
        # the keydown happens -- page.evaluate alone reads the outer document,
        # whose __keys array stays empty.
        return any(
            frame.evaluate(
                "(k) => (window.__keys || []).some("
                "(e) => e.metaKey && e.key === k && e.defaultPrevented)",
                key,
            )
            for frame in self.page.frames
        )

    def saw(self, key: str) -> int:
        """How many frames saw that keystroke at all. Zero means it went
        nowhere, and an assertion about it would prove nothing."""
        return sum(
            frame.evaluate(
                "(k) => (window.__keys || []).filter("
                "(e) => e.metaKey && e.key === k).length",
                key,
            )
            for frame in self.page.frames
        )

    def press(self, combination: str) -> None:
        """Type at the document, the way someone editing it would.

        The click is not decoration. The editor is in an iframe, and a key sent
        to a page whose focus is still on the outer document reaches nothing --
        measured: no click, no keydown in the frame, no request to the host.
        """
        self.page.locator("iframe").first.click(
            position={"x": 300, "y": 300}, force=True
        )
        self.page.wait_for_timeout(300)
        self.page.keyboard.press(combination)
        # The request is a synchronous XHR from the page, but the keystroke
        # that triggers it is not: give it a moment to arrive.
        self.page.wait_for_timeout(1500)


@pytest.fixture
def editor_with(tmp_path, sample_document, monkeypatch):
    """An editor in a real browser, told that the menu owns `owned`."""

    def _open(owned: list[dict]) -> Iterator[Editor]:
        monkeypatch.setattr(server.get, "owned_keys", lambda: owned)
        sessions.SESSIONS.clear()
        sessions.configure(
            Host(
                payload=payload_mod.resolve().root,
                work=tmp_path / "0",
                document=sample_document,
            )
        )
        opening.open_document(sample_document)
        server.ROUTES.clear()

        port = free_port()
        httpd = server.make_server(port)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return httpd, port

    made: list = []

    def open_editor(owned: list[dict]) -> Editor:
        httpd, port = _open(owned)
        made.append(httpd)
        play = sync_playwright().start()
        made.append(play)
        try:
            browser = play.chromium.launch()
        except Error as e:  # the browser was never downloaded
            pytest.skip(
                f"needs Playwright's chromium: uv run playwright install chromium ({e})"
            )
        made.append(browser)
        page = browser.new_page()
        # Before any page script, in every frame: keep the event objects so a
        # test can read defaultPrevented once dispatch is over. The bridge
        # calls stopImmediatePropagation, so a listener cannot be *told* what
        # happened afterwards -- but the event itself remembers.
        page.add_init_script(
            "window.__keys = [];"
            "window.addEventListener('keydown', (e) => window.__keys.push(e), true);"
        )
        page.goto(server.editor_url(port, sample_document.name, "0"))
        editor = Editor(page, port)
        editor.wait_until_ready()
        return editor

    yield open_editor

    for thing in reversed(made):
        for close in ("close", "shutdown", "stop"):
            if hasattr(thing, close):
                getattr(thing, close)()
                break
    sessions.SESSIONS.clear()


def test_the_page_yields_a_key_the_menu_bar_owns(editor_with):
    """Cmd-N with a menu bar: AppKit's job, so the page must not also ask."""
    editor = editor_with([s.as_json() for s in menu.PAGE_YIELDS])
    editor.press("Meta+n")

    assert editor.asked_for("new") == 0


@pytest.mark.xfail(
    not sys.platform.startswith("darwin"),
    strict=True,
    reason=(
        "No New accelerator on Linux. Measured in the container: the keystroke"
        " reaches the editor -- one frame sees it -- and no `new` request"
        " follows, for Meta+n or Control+n. The menu bar that owns it is"
        " macOS-only (host/menu.py), and the web layer does not handle the key"
        " itself off a Mac. strict, so this tells us if it ever starts working."
    ),
)
def test_the_page_handles_the_key_when_nothing_else_will(editor_with):
    """The same key with no menu bar -- `libera --serve` -- must work.

    On macOS this is the real path for a serve-only run. On Linux it is the
    *only* path, and it does not work: see the xfail above, and the known
    issue in docs/src/guide/status.md.
    """
    editor = editor_with([])
    editor.press("Meta+n")

    assert editor.asked_for("new") == 1


def test_the_page_declines_the_key_without_claiming_it(editor_with):
    """Declining and swallowing are one line apart and opposite.

    stopImmediatePropagation stops the editor's own handler, which is wanted.
    preventDefault marks the event handled, WKWebView reports that to AppKit as
    "the page took it", and the menu item does not fire either. Both together
    is the obvious thing to write, and it makes Cmd-N do nothing at all.
    """
    editor = editor_with([s.as_json() for s in menu.PAGE_YIELDS])
    editor.press("Meta+n")

    assert editor.asked_for("new") == 0, "the page acted on a key the menu owns"
    assert not editor.claimed("n"), (
        "the page claimed the key, so the menu will not fire"
    )
