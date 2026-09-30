"""The documents after the first wait for the GUI loop, not for a list.

`libera a.docx b.pptx` opens the first window on the main thread and the rest
from a thread, because pywebview can only create a window once `start()` is
running. The wait for that used `webview.windows`, which `create_window` fills
*before* `start()` is called:

    >>> webview.create_window("t", "about:blank")
    >>> len(webview.windows), webview.windows[0].events.shown.is_set()
    (1, False)

So the wait returned on its first iteration and every later document was created
against a GUI loop that did not exist yet, which leaves a window unshown. It
mostly worked because `open_window` converts a document first and usually lost
the race to `webview.start()` by a second or so.

These tests drive `_open_rest` with a stand-in window, so they need no GUI: the
question is only which condition it blocks on.
"""

from __future__ import annotations

import threading

from libera.host import app


class FakeEvent:
    """pywebview's Event, as far as this matters: set/is_set/wait."""

    def __init__(self) -> None:
        self._e = threading.Event()

    def set(self) -> None:
        self._e.set()

    def is_set(self) -> bool:
        return self._e.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._e.wait(timeout)


class FakeWindow:
    def __init__(self) -> None:
        self.events = type("E", (), {"shown": FakeEvent()})()


def test_it_waits_until_the_first_window_is_shown(monkeypatch) -> None:
    """Nothing opens while `shown` is unset, however long the thread runs."""
    monkeypatch.setattr(app, "SHOWN_TIMEOUT", 0.5)
    window = FakeWindow()
    opened: list[str] = []

    worker = threading.Thread(
        target=app._open_rest,
        args=(window, ["b.pptx"], lambda d: opened.append(str(d))),
        daemon=True,
    )
    worker.start()
    # Long enough to have finished if it were not waiting, short enough not to
    # reach the timeout that lets it through anyway.
    worker.join(0.2)
    assert opened == [], "opened a window before the first one was on screen"

    window.events.shown.set()
    worker.join(2)
    assert opened == ["b.pptx"]


def test_a_window_that_never_appears_does_not_swallow_the_documents(
    monkeypatch,
) -> None:
    """The timeout is a fallback, not a filter.

    Dropping what somebody named on the command line would be worse than
    opening it into a window that turns out to be slow.
    """
    monkeypatch.setattr(app, "SHOWN_TIMEOUT", 0.1)
    opened: list[str] = []

    app._open_rest(FakeWindow(), ["b.pptx", "c.xlsx"], lambda d: opened.append(str(d)))

    assert opened == ["b.pptx", "c.xlsx"]


def test_the_list_pywebview_fills_early_is_not_the_condition() -> None:
    """The regression itself, stated as a fact about `_open_rest`'s source.

    A non-empty `webview.windows` must not be what releases it, because that is
    true before `start()`. Read off the bytecode rather than the source: the
    docstrings here and in `_install_menu` both discuss `webview.windows`, so
    grepping the text matches the prose that explains the bug. `co_names` is
    what the function actually looks up.
    """
    names = set(app._open_rest.__code__.co_names)
    assert "shown" in names, f"does not wait on the shown event: {sorted(names)}"
    assert "windows" not in names, "back to waiting on a list create_window fills"
