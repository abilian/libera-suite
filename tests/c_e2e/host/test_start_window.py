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
import threading
import urllib.request
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect, sync_playwright
from support import find_free_port, keyed, launch

from libera import payload as payload_mod
from libera.host import language, recents, server, session as sessions
from libera.host.session import Session

# How long to watch for a request that must not come, after a sync point.
ABSENCE = 1_000


def answered(page, route: str):
    """Around a click: wait until the host has answered the request to `route`
    that the click makes. A count read after a fixed wait missed a request that
    arrived late, and a loaded machine makes them late."""
    path = f"/__host__/{route}"
    return page.expect_response(lambda r: urlparse(r.url).path == path)


@pytest.fixture
def start_window(tmp_path):
    """The start window, loaded, with three documents in the Recent list."""
    sessions.SESSIONS.clear()
    # The session state gets its own subtree. remember_recent refuses anything
    # under the recents file's own directory -- that is our plumbing, not the
    # user's documents -- so the two have to be genuinely apart.
    start = Session(payload=payload_mod.resolve().root, work=tmp_path / "state" / "0")
    sessions.configure(start)

    elsewhere = tmp_path / "Documents"
    elsewhere.mkdir()
    for name in ("Report.docx", "Budget.xlsx", "Deck.pptx"):
        (elsewhere / name).write_bytes(b"x")
        recents.remember_recent(start, elsewhere / name)

    port = find_free_port()
    httpd = server.make_server(port, start)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    play = sync_playwright().start()
    try:
        browser = launch(play)
    except pytest.skip.Exception:
        play.stop()
        httpd.shutdown()
        raise
    page = browser.new_page(viewport={"width": 720, "height": 640})
    page.goto(keyed(f"http://127.0.0.1:{port}/__host__/start"))
    page.wait_for_selector("#new button")

    def asked_for(route: str) -> int:
        with urllib.request.urlopen(
            keyed(f"http://127.0.0.1:{port}/__host__/report"), timeout=30
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


def test_it_speaks_the_interface_language(start_window, monkeypatch):
    """Its own text, the kinds the host names, and what its script writes."""
    monkeypatch.setattr(language, "get_language", lambda: "fr-FR")
    start_window.reload()
    start_window.wait_for_selector("#new button")
    french = language.read_catalogue("fr")

    assert start_window.locator("html").get_attribute("lang") == "fr"
    assert "{{" not in start_window.content()
    headings = start_window.locator("h2").all_inner_texts()
    assert headings == [french["New"], french["Open"], french["Recent"]]
    kinds = start_window.locator("#new .kind").all_inner_texts()
    assert french["Spreadsheet"] in kinds
    expect(start_window.locator("#payload dt").first).to_have_text(french["Components"])


def test_new_asks_the_host_for_that_kind(start_window):
    """Clicking Spreadsheet has to reach the host as a spreadsheet.

    The session behind the start window shows no document at all, so the kind
    cannot come from it -- it travels with the request.
    """
    with answered(start_window, "new"):
        start_window.locator("#new button", has_text="Spreadsheet").click()

    assert start_window.asked_for("new") == 1


def test_it_lists_the_recent_documents_newest_first(start_window):
    names = start_window.locator("#recent .name").all_inner_texts()
    assert names == ["Deck.pptx", "Budget.xlsx", "Report.docx"]


def test_a_recent_document_opens_by_the_path_the_host_handed_out(start_window):
    with answered(start_window, "open-recent"):
        start_window.locator("#recent button").first.click()

    assert start_window.asked_for("open-recent") == 1


def test_open_asks_the_host_to_put_a_panel_up(start_window):
    """Only a process with a window can show a file dialog, so the page asks."""
    with answered(start_window, "open-document"):
        start_window.locator("#open").click()

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
    with answered(start_window, "new"):
        button.click()
    button.click(force=True)
    # A request that must not come has no event to wait for. The first one has
    # been answered, so a second would already be on its way.
    start_window.wait_for_timeout(ABSENCE)

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
    with answered(start_window, "open-recent"):
        button.click()

    assert start_window.asked_for("open-recent") == 1, "the host was never asked"
    # What the page does with the answer comes after it: expect() waits.
    expect(button, "a failed click left the window dead").to_be_enabled()
    expect(
        start_window.locator("#problem"), "and said nothing about it"
    ).to_be_visible()


def test_a_cancelled_open_leaves_the_window_usable(start_window):
    """Cancelling the panel is not an error, so host() did not throw, and the
    buttons stayed disabled for good. With no window to put a panel on, the
    host answers as a cancelled panel does: 200, and nothing opened."""
    button = start_window.locator("#open")
    with answered(start_window, "open-document"):
        button.click()

    assert start_window.asked_for("open-document") == 1, "the host was never asked"
    # What the page does with the answer comes after it: expect() waits.
    expect(button, "a cancelled Open left the window dead").to_be_enabled()


def test_a_document_dropped_on_it_opens(start_window, monkeypatch, tmp_path):
    """Its own page, with no bridge, so its own drop handler: the host is asked
    by name, and the drop is cancelled so the page stays."""
    from support import ScriptedShell

    from libera.host import hooks

    report = tmp_path / "report.docx"
    opened: list = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            take_dropped=lambda names: [report] if report.name in names else [],
            open_window=lambda document, _app=None: opened.append(document) or True,
        ),
    )

    with answered(start_window, "drop"):
        prevented = start_window.evaluate(
            """() => {
              const data = new DataTransfer();
              data.items.add(new File(['x'], 'report.docx'));
              const drop = new DragEvent('drop',
                {bubbles: true, cancelable: true, dataTransfer: data});
              document.body.dispatchEvent(drop);
              return drop.defaultPrevented;
            }"""
        )

    assert prevented
    assert opened == [report]


def test_a_file_dragged_over_it_is_shown_to_be_welcome(start_window):
    """A drop that works with nothing on screen to say it will: an outline
    while the drag is over the window. (The pointer's "copy" cannot be read
    here: a script-made DataTransfer keeps dropEffect at "none".)"""
    start_window.evaluate(
        """() => {
          const data = new DataTransfer();
          data.items.add(new File(['x'], 'report.docx'));
          document.body.dispatchEvent(new DragEvent('dragover',
            {bubbles: true, cancelable: true, dataTransfer: data}));
        }"""
    )

    assert "dropping" in start_window.evaluate("document.body.className")
