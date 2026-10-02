"""An editor in a real browser, served in-process, for tests that drive it.

`libera --serve` in a subprocess (the tier's own conftest) cannot be told
anything, and these tests vary what the host says: which keys the menu bar
owns, for one. So the server runs here, in the test process, and a Playwright
Chromium loads the editor from it. It has no window opener, like `--serve`.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import (
    Error,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)
from support import find_free_port

from libera import payload as payload_mod
from libera.host import opening, server, session as sessions
from libera.host.session import Session

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# The editor takes a while to be ready for a keystroke, and a key pressed at a
# page that has not finished booting tells us nothing.
READY = 180_000


class Editor:
    """A loaded editor, and what the host was asked to do while it ran."""

    def __init__(self, page, port: int) -> None:
        self.page = page
        self._calls = f"http://127.0.0.1:{port}/__host__/calls"
        # Requests the page gave up on: a load that never finishes is one of
        # these, and saying so is the difference between a stall and a stopwatch.
        self.failed: list[str] = []
        page.on("requestfailed", lambda r: self.failed.append(f"{r.url} ({r.failure})"))

    def report(self) -> dict:
        with urllib.request.urlopen(self._calls, timeout=30) as r:
            return json.load(r)

    def asked_for(self, route: str) -> int:
        return self.report()["routes"].get(route, 0)

    def wait_until_ready(self) -> None:
        """Until the document is laid out and the load mask is down.

        It waited for `Asc.editor`, which exists half a second in, well before
        the document has loaded. A test acting then clicked behind the load
        mask, or as the mask came down -- when the editor ignores a click on
        File. Both were caught under CPU load: test_create_new failed one run in
        five.

        onDocumentContentReady is the editor saying the document is laid out,
        read from this page's own call log: the host's counters are shared by
        every page in the process.

        A load that never gets there says which requests failed. That is how
        the stall at "Loading document: 8%" was found: a font request reset by
        the host's listen backlog, which the editor's font loader does not
        retry. See Server.request_queue_size.
        """
        try:
            self.page.wait_for_function(
                "() => { const f = document.querySelector('iframe');"
                " const d = f && f.contentDocument;"
                " return (window.__libera_calls || []).some("
                "(c) => c.name === 'onDocumentContentReady')"
                " && !!d && !d.querySelector('.asc-loadmask'); }",
                timeout=READY,
            )
        except PlaywrightTimeoutError as e:
            failed = "\n  ".join(self.failed) or "none"
            msg = (
                f"the editor never finished loading within {READY // 1000}s\n"
                f"requests that failed:\n  {failed}"
            )
            raise AssertionError(msg) from e

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

    @property
    def frame(self):
        """The editor's own frame, inside the wrapper page."""
        return next(f for f in self.page.frames if "/main/index.html" in f.url)

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
    """An editor in a real browser, told that the menu owns `owned`.

    On the sample document unless given another, whose extension picks the
    editor.
    """

    def _open(owned: list[dict], document: Path) -> Iterator[Editor]:
        monkeypatch.setattr(server.get, "list_owned_keys", lambda: owned)
        sessions.SESSIONS.clear()
        opened = Session(
            payload=payload_mod.resolve().root,
            work=tmp_path / "0",
            document=document,
        )
        sessions.configure(opened)
        opening.open_document(opened, document)

        port = find_free_port()
        httpd = server.make_server(port, opened)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return httpd, port, opened

    made: list = []

    def open_editor(owned: list[dict], document: Path | None = None) -> Editor:
        document = document or sample_document
        httpd, port, opened = _open(owned, document)
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
        editor = Editor(page, port)  # before the page loads: it watches requests
        page.goto(server.make_editor_url(port, opened, document.name))
        editor.wait_until_ready()
        return editor

    yield open_editor

    for thing in reversed(made):
        for close in ("close", "shutdown", "stop"):
            if hasattr(thing, close):
                getattr(thing, close)()
                break
    sessions.SESSIONS.clear()
