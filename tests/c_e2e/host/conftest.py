"""An editor in a real browser, served in-process, for tests that drive it.

`libera --serve` in a subprocess (the tier's own conftest) cannot be told
anything, and these tests vary what the host says: which keys the menu bar
owns, for one. So the server runs here, in the test process, and a Playwright
Chromium loads the editor from it. It has no window opener, like `--serve`.
"""

from __future__ import annotations

import json
import os
import platform
import threading
import urllib.request
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)
from support import find_free_port, keyed, launch

from c_e2e.conftest import SYNC_REPORTS, flush_reports
from libera import payload as payload_mod
from libera.host import opening, server, session as sessions
from libera.host.session import Session

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# Playwright pins macOS 14 to a WebKit build it no longer speaks to: the
# browser launches, then refuses "Playwright.closePage" and the setting
# "PushAPIEnabled", and new_page(), which has no timeout, never returns.
# Measured with Playwright 1.62 and WebKit 2251 on macOS 14.8, before any
# request reached the host.
OLD_WEBKIT = (
    "Playwright's WebKit for macOS 14 hangs in new_page(); use macOS 15+ or Linux"
)


def _is_macos_before(major: int) -> bool:
    release = platform.mac_ver()[0]
    return bool(release) and int(release.split(".")[0]) < major


# The editor takes a while to be ready for a keystroke, and a key pressed at a
# page that has not finished booting tells us nothing.
READY = 180_000
# How long to watch for something that must not happen. Only ever after a sync
# point, so this covers a request already on its way, not a page catching up.
ABSENCE = 1_000


class Editor:
    """A loaded editor, and what the host was asked to do while it ran."""

    def __init__(self, page, port: int) -> None:
        self.page = page
        self._calls = keyed(f"http://127.0.0.1:{port}/__host__/report")
        # Requests the page gave up on: a load that never finishes is one of
        # these, and saying so is the difference between a stall and a stopwatch.
        self.failed: list[str] = []
        page.on("requestfailed", lambda r: self.failed.append(f"{r.url} ({r.failure})"))
        # And every one it made, for a test of where one went.
        self.requested: list[str] = []
        page.on("request", lambda r: self.requested.append(r.url))

    def report(self) -> dict:
        with urllib.request.urlopen(self._calls, timeout=30) as r:
            return json.load(r)

    def reported(self) -> dict:
        """The report, once the page has posted everything it holds: an error
        raised since the bridge's last one-second tick is not in `report()`."""
        flush_reports(self.page)
        return self.report()

    def asked_for(self, route: str) -> int:
        return self.report()["routes"].get(route, 0)

    def answered(self, route: str):
        """Around an action: wait until the host has answered the request to
        `route` that the action makes. A count read after a fixed wait missed
        a request that arrived late, and a loaded machine makes them late."""
        path = f"/__host__/{route}"
        return self.page.expect_response(lambda r: urlparse(r.url).path == path)

    def wait_for_nothing(self) -> None:
        """The one fixed wait: for a request that must not come. There is no
        event to wait for, only time, so it follows a sync point the caller
        has already reached."""
        self.page.wait_for_timeout(ABSENCE)

    def wait_until_ready(self) -> None:
        """Until the document is laid out and the load mask is down.

        It waited for `Asc.editor`, which exists half a second in, well before
        the document has loaded. A test acting then clicked behind the load
        mask, or as the mask came down -- when the editor ignores a click on
        File. Both were caught under CPU load: test_create_new failed one run in
        five.

        onDocumentContentReady is the editor saying the document is laid out,
        read from this page's own record of the calls it made: the host's
        counters are shared by every page in the process. Not from
        the shared call log (the top frame's `__libera__.calls`), which each
        report empties, and the report goes the
        moment the document is ready: the PDF editor's ready call was gone
        before this looked, every time.

        A load that never gets there says which requests failed. That is how
        the stall at "Loading document: 8%" was found: a font request reset by
        the host's listen backlog, which the editor's font loader does not
        retry. See Server.request_queue_size.
        """
        try:
            self.page.wait_for_function(
                "() => { const f = document.querySelector('iframe');"
                " const d = f && f.contentDocument;"
                " return !!window.__libera_seen"
                " && window.__libera_seen.has('onDocumentContentReady')"
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
        So the key waits for the editor's frame to have the focus.

        What the key should make happen is the caller's to wait for:
        `answered` for a request, `wait_for_nothing` for none.
        """
        self.page.locator("iframe").first.click(
            position={"x": 300, "y": 300}, force=True
        )
        self.frame.wait_for_function("() => document.hasFocus()")
        self.page.keyboard.press(combination)


@pytest.fixture
def editor_with(tmp_path, sample_document, monkeypatch):
    """An editor in a real browser, told that the menu owns `owned`.

    On the sample document unless given another, whose extension picks the
    editor.
    """

    def _open(
        owned: list[dict],
        document: Path,
        locked_by: str | None,
        fonts: Path | None,
    ) -> Iterator[Editor]:
        monkeypatch.setattr(server.editor, "list_owned_keys", lambda: owned)
        sessions.SESSIONS.clear()
        opened = Session(
            payload=payload_mod.resolve().root,
            work=tmp_path / "0",
            document=document,
            fonts=fonts,
        )
        sessions.configure(opened)
        opening.open_document(opened, document)
        # What `locking.hold` records in a window; `--serve` never locks.
        opened.locked_by = locked_by

        port = find_free_port()
        httpd = server.make_server(port, opened)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return httpd, port, opened

    made: list = []

    def open_editor(
        owned: list[dict],
        document: Path | None = None,
        locked_by: str | None = None,
        fonts: Path | None = None,
        init_script: str | None = None,
    ) -> Editor:
        document = document or sample_document
        httpd, port, opened = _open(owned, document, locked_by, fonts)
        made.append(httpd)
        play = sync_playwright().start()
        made.append(play)
        # Chromium unless E2E_BROWSER says otherwise: webkit is the engine of
        # the macOS window, and the Save As race was WebKit's alone.
        engine = os.environ.get("E2E_BROWSER", "chromium")
        if engine == "webkit" and _is_macos_before(15):
            pytest.skip(OLD_WEBKIT)
        browser = launch(play, engine)
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
        page.add_init_script(SYNC_REPORTS)
        if init_script:
            page.add_init_script(init_script)
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
