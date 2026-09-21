"""Starting a slideshow, which is the first thing in Slides that is not typing.

`Show from the beginning` was a TypeError and an asc_onError -25: sdkjs calls
AscDesktopEditor.SetFullscreen guarded on nothing but the bridge existing, and
the bridge did not have it. Nothing in the suite drove a toolbar button, so
nothing caught it.

The button is real and so is the click. #slot-btn-dt-start-over has been
stable across the editors we ship; if upstream renames it this test fails
loudly, which is the right way to find out.
"""

from __future__ import annotations

import json
import shutil
import socket
import threading
import urllib.request

import pytest
from playwright.sync_api import Error, sync_playwright

from libera import payload as payload_mod
from libera.host import opening, server, session as sessions
from libera.host.session import Host

LOUD = ("error", "reject", "asc_onError")
READY = 180_000


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def slides(tmp_path):
    """Slides, open on the payload's blank deck, in a real browser."""
    root = payload_mod.resolve().root
    deck = tmp_path / "deck.pptx"
    shutil.copyfile(root / "empty" / "new.pptx", deck)

    sessions.SESSIONS.clear()
    sessions.configure(Host(payload=root, work=tmp_path / "0", document=deck))
    opening.open_document(deck)
    server.ROUTES.clear()

    port = free_port()
    httpd = server.make_server(port)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    play = sync_playwright().start()
    try:
        browser = play.chromium.launch()
    except Error as e:
        play.stop()
        httpd.shutdown()
        pytest.skip(f"needs Playwright's chromium: playwright install chromium ({e})")
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(server.editor_url(port, deck.name, "0"))
    page.wait_for_function(
        "() => { const f = document.querySelector('iframe');"
        "return f && f.contentWindow && f.contentWindow.Asc"
        " && f.contentWindow.Asc.editor; }",
        timeout=READY,
    )
    page.wait_for_timeout(3000)

    def report() -> dict:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/__host__/calls", timeout=30
        ) as r:
            return json.load(r)

    page.report = report
    page.editor = page.frames[1]
    yield page

    browser.close()
    play.stop()
    httpd.shutdown()
    sessions.SESSIONS.clear()


def loud_errors(report: dict) -> list[str]:
    return [
        f"{e['kind']}: {e['text'].splitlines()[0][:160]}"
        for e in report["errors"]
        if e["kind"] in LOUD
    ]


def start_the_show(page) -> None:
    page.editor.locator("#slot-btn-dt-start-over").click()
    page.wait_for_timeout(2500)


def end_the_show(page) -> None:
    """Leave the slideshow, which is where the presenter window is torn down.

    Escape, not a click on the canvas: measured, both reach
    DemonstrationReporterEnd, and the preview element that takes the click is
    not the one with the id that looks right (#presentation-preview is an
    empty shell; #pe-preview is the visible one).
    """
    page.keyboard.press("Escape")
    page.wait_for_timeout(2500)


def test_ending_a_slideshow_does_not_raise(slides):
    """The reported bug: clicking past the last slide.

    sdkjs tears the presenter window down on the way out -- endReporter --
    guarded on nothing but the bridge existing. It threw, the editor raised
    asc_onError, and the user got two dialogs for one fault.
    """
    start_the_show(slides)
    end_the_show(slides)

    assert loud_errors(slides.report()) == []


def test_show_from_the_beginning_does_not_raise(slides):
    """The bug, exactly: a TypeError the moment the slideshow starts."""
    assert loud_errors(slides.report()) == [], "broken before the click"

    start_the_show(slides)

    assert loud_errors(slides.report()) == []


def test_show_from_the_beginning_asks_the_host_for_fullscreen(slides):
    """sdkjs asks the host to take the window over, and means it.

    With no window -- this server has none -- the host says nothing happened
    and the show runs where it is. What matters is that the call arrives.
    """
    start_the_show(slides)

    assert slides.report()["routes"].get("fullscreen") == 1


def test_the_bridge_carries_the_method_sdkjs_calls_unguarded(slides):
    """sdkjs guards on `undefined !== window.AscDesktopEditor` and no further.

    The bridge's Proxy returns undefined for anything it does not implement,
    which is right for a feature check and a TypeError for a call like this
    one.
    """
    kind = slides.editor.evaluate("() => typeof window.AscDesktopEditor.SetFullscreen")
    assert kind == "function"
