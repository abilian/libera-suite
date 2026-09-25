"""Help says where the documentation is when it cannot open a browser.

`show_help` asked `webbrowser` to open the docs and threw away the False it
gets back when there is nothing to run. On a machine with no browser -- a
Flatpak on a minimal desktop, a headless box -- the menu item did nothing at
all, which is the hardest kind of bug for a user to report.

Both directions matter. Saying nothing when the browser opened would be noise
on every machine that works.
"""

from __future__ import annotations

import pytest

from libera.host.menu import actions
from libera.host.window import dialogs


@pytest.fixture
def messages(monkeypatch):
    """Whatever `_open_help` would have put on screen."""
    said: list[tuple[str, str]] = []
    monkeypatch.setattr(dialogs, "say", lambda h, d: said.append((h, d)))
    return said


def browser(monkeypatch, *, works: bool):
    opened: list[str] = []

    def fake_open(url: str) -> bool:
        opened.append(url)
        return works

    monkeypatch.setattr(actions.webbrowser, "open", fake_open)
    return opened


def test_no_browser_gets_the_url_on_screen(monkeypatch, messages):
    opened = browser(monkeypatch, works=False)

    actions._open_help()

    assert opened == [actions.HELP_URL], "it did not try to open anything"
    assert messages, "nothing told the user, so Help did nothing visible"
    heading, detail = messages[0]
    assert actions.HELP_URL in detail, (
        f"the message has to carry the URL, or it is no better than silence: {detail!r}"
    )
    assert heading, "an alert with no heading"


def test_a_working_browser_says_nothing(monkeypatch, messages):
    browser(monkeypatch, works=True)

    actions._open_help()

    assert not messages, (
        "it reported a failure after the browser opened, which would fire on "
        "every machine where Help works"
    )
