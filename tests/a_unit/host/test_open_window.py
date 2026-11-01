"""A document that will not open, opened from inside the running application.

File > Open, Open Recent, a Finder double-click and a second `libera FILE` all
reach the same window opener. When the converter refused the document it
raised into whichever of them had asked: a request lost its connection with
no answer, a menu action printed a traceback nobody saw, the new session
stayed registered with no window -- and a second launch, finding its hand-off
answered by a dropped connection, started a whole second instance.
"""

from __future__ import annotations

import threading
from collections import UserList

import pytest

from libera.host import app, locking
from libera.host.convert import ConversionError
from libera.host.session import SESSIONS, Session, configure
from libera.host.window import windows


@pytest.fixture
def running(tmp_path, monkeypatch):
    """One session, as `run()` leaves it, and a converter that refuses."""
    SESSIONS.clear()
    configure(Session(payload=tmp_path / "payload", work=tmp_path / "sessions" / "0"))

    def refuse(_session, document):
        msg = f"x2t could not convert {document.name} (exit status 1)"
        raise ConversionError(msg)

    monkeypatch.setattr(app.opening.convert, "convert_to_editor_bin", refuse)
    monkeypatch.setattr(app, "create_window", lambda *_a, **_k: FakeWindow("w1"))
    closed: list[str] = []
    monkeypatch.setattr(
        app, "close_session_window", lambda session: closed.append(session.id)
    )
    said: list[str] = []
    monkeypatch.setattr(
        app.dialogs, "say", lambda heading, _detail: said.append(heading)
    )
    yield said, closed
    SESSIONS.clear()


def test_it_is_said_on_screen_and_its_window_closed(running, tmp_path):
    """The window opens before the converter has read the document, so that
    the editor loads meanwhile; the window of one it refuses closes again,
    and its session goes with it."""
    said, closed = running
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a document")

    assert app.WindowedShell(43110).open_window(broken)
    (made,) = (s for s in SESSIONS.values() if s.id != "0")
    assert made.converting is not None
    made.converting.join()

    assert said == ["Libera Suite could not open “broken.docx”"]
    assert closed == [made.id]


@pytest.fixture
def no_display(tmp_path, monkeypatch):
    """run(), with fakes for what needs a display, up to webview.start(), which
    each test fakes its own way. The toolkit's own preparation is left out: on
    a Mac it renames the process."""
    from types import SimpleNamespace

    from libera.host import hooks

    class Event:
        def __iadd__(self, _handler):
            return self

    monkeypatch.setattr(hooks, "shell", hooks.HeadlessShell())  # put back after
    # run() announces itself; somewhere of this test's own, not the shared path.
    monkeypatch.setattr(app.instance, "get_path", lambda: tmp_path / "instance.json")
    monkeypatch.setattr(app.native, "prepare", lambda: None)
    # On macOS it runs AppKit's loop again once start() returns.
    monkeypatch.setattr(app.native, "stay_open", lambda: None)
    # It builds the font index on a thread that outlives the test, holding the
    # lock the font tests take.
    monkeypatch.setattr(app.fonts, "build_behind", lambda *_: None)
    monkeypatch.setattr(
        app.server,
        "make_server",
        lambda _port, _session: SimpleNamespace(serve_forever=lambda: None),
    )
    monkeypatch.setattr(
        app,
        "create_window",
        lambda *_a, **_k: SimpleNamespace(
            uid="w", events=SimpleNamespace(closing=Event(), closed=Event())
        ),
    )
    monkeypatch.setattr(windows, "_start_windows", [])


def test_run_reaches_the_gui_loop_with_windows_to_open_in(
    no_display, tmp_path, monkeypatch
):
    """The windowed shell has to be in place before the first document opens,
    which may ask whether to recover its unsaved edits; the server starts
    first so that the shell knows its port."""
    import webview

    from libera.host import hooks

    at_start: list = []
    monkeypatch.setattr(webview, "start", lambda **_: at_start.append(hooks.shell))

    hook = threading.excepthook

    app.run(tmp_path / "payload", tmp_path / "sessions", [])

    assert threading.excepthook is hook, "run() left its thread hook behind"
    assert len(at_start) == 1, "run() never reached the GUI loop"
    assert at_start[0].windowed
    (first,) = SESSIONS.values()
    assert first.work.parent == tmp_path / "sessions"


def test_a_first_document_the_converter_refuses_is_said_and_its_window_closed(
    no_display, tmp_path, monkeypatch
):
    """The first window too opens before the conversion ends. A refusal used
    to raise out of run(), before there was any window; it is now said, and
    its window closed, as a later document's is."""
    import webview

    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a document")

    def refuse(_session, document):
        msg = f"x2t could not convert {document.name} (exit status 1)"
        raise ConversionError(msg)

    monkeypatch.setattr(app.opening.convert, "convert_to_editor_bin", refuse)
    said: list[str] = []
    monkeypatch.setattr(app.dialogs, "say", lambda heading, _: said.append(heading))
    closed: list[str] = []
    monkeypatch.setattr(
        app, "close_session_window", lambda session: closed.append(session.id)
    )

    converting: list = []

    def gui_loop(**_):
        (session,) = SESSIONS.values()
        converting.append(session.converting)
        session.converting.join()

    monkeypatch.setattr(webview, "start", gui_loop)

    app.run(tmp_path / "payload", tmp_path / "sessions", [broken])

    (thread,) = converting
    assert thread is not None, "converted before the window was made"
    assert said == ["Libera Suite could not open “broken.docx”"]
    assert len(closed) == 1, "the window stayed open"


def test_a_quit_that_never_returns_from_the_gui_loop_still_lets_go(
    no_display, tmp_path, monkeypatch
):
    """Cmd-Q on macOS ends the process inside webview.start(), so nothing after
    it runs: the document's lock file and the announcement to a second launch
    used to stay behind. What the toolkit runs on quitting has to release them.
    """
    import webview

    document = tmp_path / "report.docx"
    document.write_bytes(b"a document")
    quitting: list = []
    monkeypatch.setattr(app.native, "on_quit", quitting.append)
    left: list[bool] = []

    def quit_inside_the_gui_loop(**_):
        (session,) = SESSIONS.values()
        session.write_current_document(document)
        locking.hold(session, document)
        assert locking.lock_path(document).is_file()
        for work in quitting:
            work()
        # Checked here, before run()'s own way out, which a quit never reaches.
        left.append(locking.lock_path(document).exists())
        left.append((tmp_path / "instance.json").exists())

    monkeypatch.setattr(webview, "start", quit_inside_the_gui_loop)

    app.run(tmp_path / "payload", tmp_path / "sessions", [])

    assert left == [False, False], "the lock or the announcement outlived the quit"


class Hooks(UserList):
    """A pywebview event: handlers are added with `+=`."""

    def __iadd__(self, handler):
        self.append(handler)
        return self


class FakeWindow:
    """A pywebview window, reduced to what opening a document asks of it."""

    def __init__(self, uid: str) -> None:
        from types import SimpleNamespace

        self.uid = uid
        self.shown = 0
        self.events = SimpleNamespace(closing=Hooks(), closed=Hooks())

    def show(self) -> None:
        self.shown += 1


@pytest.fixture
def showing(tmp_path, monkeypatch):
    """A window already showing report.docx, and a converter that accepts."""
    import webview

    SESSIONS.clear()
    report = tmp_path / "report.docx"
    report.write_bytes(b"a document")
    configure(Session(payload=tmp_path / "payload", work=tmp_path / "sessions" / "0"))
    first = Session(
        payload=tmp_path / "payload", work=tmp_path / "sessions" / "1", document=report
    )
    configure(first)
    first.window = "w1"
    window = FakeWindow("w1")
    monkeypatch.setattr(webview, "windows", [window])
    monkeypatch.setattr(app.opening, "begin_opening", lambda *_: True)
    monkeypatch.setattr(
        app.opening, "convert_behind", lambda _s, _d, _failed, done: done()
    )
    created: list[str] = []

    def create(title, _url, *_a, **_k):
        created.append(title)
        return FakeWindow("new")

    monkeypatch.setattr(app, "create_window", create)
    monkeypatch.setattr(app, "close_start_window", lambda: None)
    yield report, window, created
    SESSIONS.clear()


def test_a_document_already_open_comes_to_the_front_instead(showing):
    """Two windows on one file each converted and saved on their own, and the
    last save won: the other window's edits were gone, with no warning."""
    report, window, created = showing

    assert app.WindowedShell(43110).open_window(report)

    assert window.shown == 1
    assert created == [], "a second window was opened on the same document"
    assert sorted(SESSIONS) == ["0", "1"]


def test_the_same_file_by_another_path_is_the_same_document(showing, tmp_path):
    report, window, created = showing
    (tmp_path / "link.docx").symlink_to(report)

    app.WindowedShell(43110).open_window(tmp_path / "link.docx")

    assert (window.shown, created) == (1, [])


def test_another_document_still_gets_a_window_of_its_own(showing, tmp_path):
    _report, window, created = showing
    other = tmp_path / "other.docx"
    other.write_bytes(b"another document")

    app.WindowedShell(43110).open_window(other)

    assert window.shown == 0
    assert len(created) == 1


def test_the_first_window_lets_go_of_its_document_when_it_closes(tmp_path, monkeypatch):
    """The first window was made apart from the others, wired to ask before
    closing but not to let go after: its lock file outlived Libera Suite, and
    LibreOffice took the document for one still open."""
    SESSIONS.clear()
    report = tmp_path / "report.docx"
    report.write_bytes(b"a document")
    first = Session(
        payload=tmp_path / "payload", work=tmp_path / "sessions" / "a", document=report
    )
    configure(first)
    locking.take(report)
    monkeypatch.setattr(app, "create_window", lambda *_a, **_k: FakeWindow("w1"))

    window = app._open_first_window(43110, first, None)
    for closed in window.events.closed:
        closed()

    assert not locking.lock_path(report).exists(), "the lock outlived the window"
    assert first.id not in SESSIONS


def test_a_thread_that_fails_says_so_on_screen(monkeypatch):
    """Opening, a menu action, a drop: each runs on a thread of its own, and
    launched from Finder or Explorer its traceback went to a stderr nobody
    sees."""
    said: list[str] = []
    monkeypatch.setattr(app.dialogs, "say", lambda heading, _: said.append(heading))
    monkeypatch.setattr(threading, "excepthook", app._say_thread_failed)

    def fails():
        msg = "the disk went away"
        raise OSError(msg)

    worker = threading.Thread(target=fails)
    worker.start()
    worker.join()

    assert said == ["Libera Suite ran into a problem"]


def test_the_last_window_closed_leaves_a_session_to_answer_for(tmp_path):
    """On macOS the application runs on with no window. A request that names
    no session, a second launch's hand-off among them, is answered for the
    first; with none left, every one was refused."""
    SESSIONS.clear()
    last = Session(payload=tmp_path / "payload", work=tmp_path / "sessions" / "0")
    configure(last)

    app.close_session(last)

    (left,) = SESSIONS.values()
    assert left.id != last.id
    assert left.document is None
    assert left.payload == last.payload
    SESSIONS.clear()
