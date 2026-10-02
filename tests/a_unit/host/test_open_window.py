"""A document that will not open, opened from inside the running application.

File > Open, Open Recent, a Finder double-click and a second `libera FILE` all
reach the same window opener. When the converter refused the document it
raised into whichever of them had asked: a request lost its connection with
no answer, a menu action printed a traceback nobody saw, the new session
stayed registered with no window -- and a second launch, finding its hand-off
answered by a dropped connection, started a whole second instance.
"""

from __future__ import annotations

import pytest

from libera.host import app
from libera.host.session import SESSIONS, NotReadyError, Session, configure


@pytest.fixture
def running(tmp_path, monkeypatch):
    """One session, as `run()` leaves it, and a converter that refuses."""
    SESSIONS.clear()
    configure(Session(payload=tmp_path / "payload", work=tmp_path / "sessions" / "0"))

    def refuse(_session, document):
        msg = f"could not open {document}"
        raise NotReadyError(msg)

    monkeypatch.setattr(app.opening, "open_document", refuse)
    monkeypatch.setattr(
        app, "_create_window", lambda *_a, **_k: pytest.fail("a window")
    )
    said: list[str] = []
    monkeypatch.setattr(
        app.dialogs, "say", lambda heading, _detail: said.append(heading)
    )
    yield said
    SESSIONS.clear()


def test_it_is_said_on_screen_and_leaves_no_session_behind(running, tmp_path):
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a document")

    app.WindowedShell(43110).open_window(broken)

    assert running == ["Libera Suite could not open “broken.docx”"]
    assert list(SESSIONS) == ["0"], "a session was left with no window"


def test_run_reaches_the_gui_loop_with_windows_to_open_in(tmp_path, monkeypatch):
    """run(), with fakes for what needs a display, up to webview.start().

    The windowed shell has to be in place before the first document opens,
    which may ask whether to recover its unsaved edits; the server starts
    first so that the shell knows its port. The toolkit's own preparation is
    left out: on a Mac it renames the process.
    """
    from types import SimpleNamespace

    import webview

    from libera.host import hooks

    class Event:
        def __iadd__(self, _handler):
            return self

    monkeypatch.setattr(hooks, "shell", hooks.HeadlessShell())  # put back after
    # run() announces itself; somewhere of this test's own, not the shared path.
    monkeypatch.setattr(app.instance, "get_path", lambda: tmp_path / "instance.json")
    monkeypatch.setattr(app.native, "prepare", lambda: None)
    monkeypatch.setattr(
        app.server,
        "make_server",
        lambda _port, _session: SimpleNamespace(serve_forever=lambda: None),
    )
    monkeypatch.setattr(
        app,
        "_create_window",
        lambda *_a, **_k: SimpleNamespace(
            uid="w", events=SimpleNamespace(closed=Event())
        ),
    )
    at_start: list = []
    monkeypatch.setattr(webview, "start", lambda **_: at_start.append(hooks.shell))

    try:
        app.run(tmp_path / "payload", tmp_path / "sessions", [])
    finally:
        app.START_WINDOW.clear()

    assert len(at_start) == 1, "run() never reached the GUI loop"
    assert at_start[0].windowed
    assert SESSIONS["0"].id == "0"
