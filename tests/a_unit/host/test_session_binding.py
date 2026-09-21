"""`H` is thread-local, so an unbound thread raises rather than defaulting.

That is the trap the whole module exists to make survivable, and File > New
from the macOS menu walked into it: menu actions run on a thread of their own.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from libera.host import apps
from libera.host.session import (
    SESSIONS,
    H,
    Host,
    NotReadyError,
    bind,
    current_session,
    use,
)


@pytest.fixture
def two_sessions(tmp_path):
    SESSIONS.clear()
    SESSIONS["0"] = Host(payload=tmp_path, work=tmp_path / "0", document=Path("a.docx"))
    SESSIONS["1"] = Host(payload=tmp_path, work=tmp_path / "1", document=Path("b.xlsx"))
    yield
    SESSIONS.clear()


def on_a_fresh_thread(work):
    """Run something on a thread that has never bound a session.

    Whatever it raises is re-raised here, so a test can assert on it rather
    than watch pytest report an unhandled thread exception and carry on.
    """
    out: list = []

    def run():
        try:
            out.append(("ok", work()))
        except BaseException as e:
            out.append(("raised", e))

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=5)
    assert out, "the thread never finished"
    kind, value = out[0]
    if kind == "raised":
        raise value
    return value


def test_an_unbound_thread_raises_rather_than_guessing(two_sessions):
    with pytest.raises(NotReadyError, match="no session bound"):
        on_a_fresh_thread(lambda: H.work)


def test_binding_by_name_reaches_that_session(two_sessions):
    def bound():
        bind("1")
        return H.editor.name, current_session()

    assert on_a_fresh_thread(bound) == ("tables", "1")


def test_an_unknown_name_falls_back_to_the_first_session(two_sessions):
    """What the menu hands over when no window matches, and what a static
    request carries: nothing."""

    def bound():
        bind("")
        return H.editor.name

    assert on_a_fresh_thread(bound) == "words"


def test_binding_with_no_sessions_at_all_says_so():
    SESSIONS.clear()
    with pytest.raises(NotReadyError, match="no sessions"):
        bind("0")


def test_file_new_picks_the_blank_of_the_window_that_asked(two_sessions):
    """The bug: New in a Tables window made an Untitled.docx, on a thread that
    had no session at all."""

    def blank_for(session):
        def work():
            bind(session)
            return H.blank.name

        return on_a_fresh_thread(work)

    assert blank_for("0") == apps.WORDS.blank
    assert blank_for("1") == apps.TABLES.blank


def test_binding_does_not_leak_between_threads(two_sessions):
    use(SESSIONS["0"], "0")
    assert on_a_fresh_thread(lambda: (bind("1"), current_session())[1]) == "1"
    assert current_session() == "0"
