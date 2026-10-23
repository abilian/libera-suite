"""What runs on the GUI thread, and what must not.

AppKit is main-thread-only and does not warn, so asking it which window is
key from a menu or request thread worked until it did not. A reload went the
other way: all of it ran on the GUI thread, two x2t runs included, and every
window froze while it did.
"""

from __future__ import annotations

import logging
import sys
import threading
from types import SimpleNamespace

import pytest

from libera.host import window
from libera.host.window import gtk as gtk_window


def test_the_key_window_is_asked_for_on_the_gui_thread(monkeypatch):
    shown = SimpleNamespace(uid="shown")
    on_gui_thread = threading.local()

    def run_on_gui_thread(work):
        on_gui_thread.yes = True
        try:
            return work()
        finally:
            on_gui_thread.yes = False

    def find_key_window(_windows):
        assert getattr(on_gui_thread, "yes", False), "asked AppKit off its thread"
        return shown

    monkeypatch.setattr(window.windows.webview, "windows", [shown])
    monkeypatch.setattr(window.windows.native, "run_on_gui_thread", run_on_gui_thread)
    monkeypatch.setattr(window.windows.native, "find_key_window", find_key_window)

    assert window.windows.find_front_window() is shown


def test_gtk_names_the_active_window_and_none_when_none_is():
    """pywebview's active_window() raised on GTK whenever no window was
    active, at startup and each time the focus left the application."""

    def made(active: bool) -> SimpleNamespace:
        return SimpleNamespace(native=SimpleNamespace(is_active=lambda: active))

    behind, front = made(active=False), made(active=True)
    unbuilt = SimpleNamespace(native=None)
    assert gtk_window.find_key_window([unbuilt, behind, front]) is front
    assert gtk_window.find_key_window([unbuilt, behind]) is None


def test_a_reload_runs_on_the_thread_that_asked(monkeypatch):
    """Never the GUI thread: pywebview hands load_url over by itself."""
    ran_on: list[threading.Thread] = []

    def refuse(_work):
        msg = "a reload has no business on the GUI thread"
        raise AssertionError(msg)

    monkeypatch.setattr(window.dialogs.native, "run_on_gui_thread", refuse)
    monkeypatch.setattr(
        window.dialogs,
        "reload_session",
        lambda _session, _port: ran_on.append(threading.current_thread()),
    )

    window.dialogs.reload(SimpleNamespace(), 8080)

    assert ran_on == [threading.current_thread()]


def raise_from_a_thread(ask) -> RuntimeError | None:
    """Ask from another thread, as a request does, and give up after a while.

    A question whose GUI side failed used to wait for an answer for good, so
    the test waits a bounded time and reports what came back, if anything.
    """
    raised: list[RuntimeError] = []

    def run():
        try:
            ask()
        except RuntimeError as e:
            raised.append(e)

    asker = threading.Thread(target=run, daemon=True)
    asker.start()
    asker.join(timeout=5)
    assert not asker.is_alive(), "still waiting for a dialog that never came up"
    return raised[0] if raised else None


def gui_thread(work) -> None:
    """A GUI thread as pyobjc's callAfter and GLib's idle_add give one: the
    work runs elsewhere, and what it raises is logged there and goes no
    further."""

    def run():
        try:
            work()
        except RuntimeError as e:
            logging.getLogger(__name__).info("the GUI thread logged %s", e)

    threading.Thread(target=run, daemon=True).start()


def broken(*_args, **_kwargs):
    msg = "the toolkit could not build it"
    raise RuntimeError(msg)


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit's save panel")
def test_a_save_panel_that_cannot_be_built_is_raised_to_the_asker(monkeypatch):
    macos = pytest.importorskip("libera.host.window.macos")
    monkeypatch.setattr(macos.AppHelper, "callAfter", gui_thread)
    monkeypatch.setattr(macos, "build_save_panel", broken)

    raised = raise_from_a_thread(
        lambda: macos.run_save_panel("a.docx", [("Word", "docx")], None, None)
    )

    assert isinstance(raised, RuntimeError)


def test_a_gtk_dialog_that_cannot_be_built_is_raised_to_the_asker(monkeypatch):
    gtk = SimpleNamespace(
        MessageDialog=broken,
        MessageType=SimpleNamespace(QUESTION=1, INFO=2),
        ResponseType=SimpleNamespace(DELETE_EVENT=-4),
    )
    glib = SimpleNamespace(idle_add=gui_thread)
    monkeypatch.setitem(sys.modules, "gi", SimpleNamespace(repository=None))
    monkeypatch.setitem(sys.modules, "gi.repository", SimpleNamespace(GLib=glib))
    monkeypatch.setattr(window.gtk, "_import_gtk", lambda: gtk)

    raised = raise_from_a_thread(
        lambda: gtk_window._run_dialog(
            "Title", "Message", [("OK", 1)], None, asking=False
        )
    )

    assert isinstance(raised, RuntimeError)
