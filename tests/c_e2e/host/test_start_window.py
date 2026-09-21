"""The start window: what `libera` on its own puts on screen.

Our page, not the payload's -- upstream keeps its start screen in the C++
shell. It talks to the host over the same /__host__/ endpoints the editor
uses, so a browser can drive it and the host can say what it was asked for.

The server runs in-process for the same reason test_keyboard.py does: these
check what the host was asked, and a subprocess would have to be interrogated
over HTTP anyway.
"""

from __future__ import annotations

import json
import socket
import threading
import urllib.request

import pytest
from playwright.sync_api import Error, sync_playwright

from libera import payload as payload_mod
from libera.host import recents, server, session as sessions
from libera.host.session import Host


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def start_window(tmp_path):
    """The start window, loaded, with three documents in the Recent list."""
    sessions.SESSIONS.clear()
    # The session state gets its own subtree. remember_recent refuses anything
    # under the recents file's own directory -- that is our plumbing, not the
    # user's documents -- so the two have to be genuinely apart.
    sessions.configure(
        Host(payload=payload_mod.resolve().root, work=tmp_path / "state" / "0")
    )
    server.ROUTES.clear()

    elsewhere = tmp_path / "Documents"
    elsewhere.mkdir()
    for name in ("Report.docx", "Budget.xlsx", "Deck.pptx"):
        (elsewhere / name).write_bytes(b"x")
        recents.remember_recent(elsewhere / name)

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
    page = browser.new_page(viewport={"width": 720, "height": 640})
    page.goto(f"http://127.0.0.1:{port}/__host__/start")
    page.wait_for_selector("#new button")

    def asked_for(route: str) -> int:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/__host__/calls", timeout=30
        ) as r:
            return json.load(r)["routes"].get(route, 0)

    page.asked_for = asked_for
    yield page

    browser.close()
    play.stop()
    httpd.shutdown()
    sessions.SESSIONS.clear()


def test_it_offers_a_new_document_of_each_kind_that_can_be_made(start_window):
    """Three editors can create; Diagrams is a viewer and must not be offered."""
    assert start_window.locator("#new .kind").all_inner_texts() == [
        "Document",
        "Spreadsheet",
        "Presentation",
    ]


def test_new_asks_the_host_for_that_kind(start_window):
    """Clicking Spreadsheet has to reach the host as a spreadsheet.

    The session behind the start window shows no document at all, so the kind
    cannot come from it -- it travels with the request.
    """
    start_window.locator("#new button", has_text="Spreadsheet").click()
    start_window.wait_for_timeout(1500)

    assert start_window.asked_for("new") == 1


def test_it_lists_the_recent_documents_newest_first(start_window):
    names = start_window.locator("#recent .name").all_inner_texts()
    assert names == ["Deck.pptx", "Budget.xlsx", "Report.docx"]


def test_a_recent_document_opens_by_the_path_the_host_handed_out(start_window):
    start_window.locator("#recent button").first.click()
    start_window.wait_for_timeout(1500)

    assert start_window.asked_for("open-recent") == 1


def test_open_asks_the_host_to_put_a_panel_up(start_window):
    """Only a process with a window can show a file dialog, so the page asks."""
    start_window.locator("#open").click()
    start_window.wait_for_timeout(1500)

    assert start_window.asked_for("open-document") == 1


def test_it_says_where_the_payload_came_from(start_window):
    """The management half of the window, such as it is today."""
    shown = start_window.locator("footer").inner_text()
    assert "installed" in shown or "LIBERA_PAYLOAD" in shown
    assert str(payload_mod.resolve().root) in shown


def test_one_click_is_all_it_takes(start_window):
    """The window is about to be closed by the host; a second click must not
    send a second request into a window that is going away."""
    button = start_window.locator("#new button", has_text="Document")
    button.click()
    start_window.wait_for_timeout(400)
    button.click(force=True)
    start_window.wait_for_timeout(1500)

    assert start_window.asked_for("new") == 1


def test_a_failed_click_leaves_the_window_usable(start_window, tmp_path):
    """fetch resolves for 404 and 500 -- only a network error rejects it.

    Awaiting the response and trusting it to throw left every button disabled
    and `leaving` stuck on, so any host-side failure turned the start window
    into something that was still on screen and took no clicks at all. That is
    how an unresponsive start screen happened.

    The failure here is real: the host refuses to open a recent document that
    is no longer on disk, because it checks the list against what exists.
    """
    (tmp_path / "Documents" / "Deck.pptx").unlink()

    button = start_window.locator("#recent button").first
    button.click()
    start_window.wait_for_timeout(1500)

    assert start_window.asked_for("open-recent") == 1, "the host was never asked"
    assert not button.is_disabled(), "a failed click left the window dead"
    assert start_window.locator("#problem").is_visible(), "and said nothing about it"
