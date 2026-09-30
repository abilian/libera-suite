"""Handing a URL to the desktop, and knowing whether the desktop took it.

This replaced `webbrowser.open`, whose return value looks like an answer and is
not one. On Linux it ends in `BackgroundBrowser.open`:

    p = subprocess.Popen(cmdline, close_fds=True, start_new_session=True)
    return (p.poll() is None)

`p.poll() is None` is true whenever the process has not exited in the instant
since it was spawned, which is always. So it reported success for `xdg-open`
exiting 3 with nothing registered for https, and Help appeared to do nothing
at all -- no window, no message, no log line.
"""

from __future__ import annotations

import logging
import sys
from types import SimpleNamespace

import pytest

from libera.host import desktop

URL = "https://docs.liberasuite.eu/"


@pytest.fixture
def opener(monkeypatch):
    """Record the command, and answer however the test asks.

    Models `Popen`, not `run`: the code waits with a timeout and leaves the
    child alone when it expires, because on a desktop that succeeds the opener
    never exits -- it stays attached to the browser it started.

    Not on Windows, which has no opener to spawn and wait for: see the
    `startfile` tests at the end.
    """
    if sys.platform == "win32":
        pytest.skip("Windows opens through os.startfile, not a spawned opener")
    calls: list[list[str]] = []
    answer: dict = {"code": 0, "killed": False}

    def fake_popen(cmd, **_):
        calls.append(cmd)

        def wait(timeout=None):
            if answer["code"] == "running":
                # The same class the code catches, taken from the module under
                # test rather than imported here.
                raise desktop.subprocess.TimeoutExpired(cmd, timeout)
            return answer["code"]

        def kill():
            answer["killed"] = True

        return SimpleNamespace(wait=wait, kill=kill)

    monkeypatch.setattr(desktop.subprocess, "Popen", fake_popen)
    return SimpleNamespace(calls=calls, answer=answer)


def test_a_desktop_that_opens_it_is_believed(opener):
    assert desktop.open_url(URL) is True
    assert opener.calls, "nothing was asked to open it"
    assert opener.calls[0][-1] == URL, "the URL never reached the command"


def test_a_desktop_with_no_handler_is_reported(opener, caplog):
    """The case webbrowser.open could not distinguish."""
    opener.answer["code"] = 3

    with caplog.at_level(logging.WARNING, logger="libera.host.desktop"):
        opened = desktop.open_url(URL)

    assert opened is False, "a failed open was reported as a success"
    assert caplog.records, "it failed silently"
    assert "3" in caplog.text, f"the status is not in the log line: {caplog.text!r}"


def test_the_url_is_the_last_argument(opener):
    """So a URL is never read as an option by whatever runs it."""
    desktop.open_url("https://example.com/-x")
    assert opener.calls[0][-1] == "https://example.com/-x"


def test_an_opener_still_running_has_taken_it(opener, caplog):
    """The success case on Linux, and the one a plain `run` cannot survive.

    Measured: `xdg-open` on a working desktop stays attached to the browser it
    started and was still running at 25 seconds. Waiting for it is what hung
    the bridge's open-url endpoint, so the wait is bounded and a timeout is
    read as success.
    """
    opener.answer["code"] = "running"

    with caplog.at_level(logging.INFO, logger="libera.host.desktop"):
        opened = desktop.open_url(URL)

    assert opened is True, "a browser that opened was reported as a failure"
    assert not opener.answer["killed"], (
        "the opener was killed on timeout, which closes the browser it started"
    )


@pytest.mark.skipif(sys.platform != "darwin", reason="the macOS opener")
def test_macos_uses_an_absolute_path():
    """`open` is a common enough word to shadow; the system one is meant."""
    assert desktop.opener() == ["/usr/bin/open"]


@pytest.fixture
def startfile(monkeypatch):
    """Windows' ShellExecute, recorded; `fail` makes it raise as it does when
    nothing is registered for the target."""
    calls: list[str] = []
    state = {"fail": False}

    def fake(target):
        calls.append(target)
        if state["fail"]:
            raise OSError(1155, "No application is associated", target)

    monkeypatch.setattr(desktop.sys, "platform", "win32")
    monkeypatch.setattr(desktop.os, "startfile", fake, raising=False)
    return SimpleNamespace(calls=calls, state=state)


def test_windows_hands_the_url_to_the_shell(startfile):
    assert desktop.open_url(URL) is True
    assert startfile.calls == [URL]


def test_windows_reports_a_url_nothing_can_open(startfile, caplog):
    """ShellExecute raises at once when there is no handler, so there is no
    five-second wait to read the answer out of."""
    startfile.state["fail"] = True
    with caplog.at_level(logging.WARNING, logger="libera.host.desktop"):
        assert desktop.open_url(URL) is False
    assert URL in caplog.text


def test_windows_reveals_a_file_with_one_explorer_argument(
    startfile, monkeypatch, tmp_path
):
    """`/select,` and the path are one word: Explorer parses its own command
    line, and split in two it opens the folder and selects nothing."""
    doc = tmp_path / "report.docx"
    doc.write_bytes(b"PK")
    ran: list[list[str]] = []
    monkeypatch.setattr(desktop.subprocess, "run", lambda cmd, **_: ran.append(cmd))
    assert desktop.reveal(doc) is True
    assert ran == [["explorer", f"/select,{doc}"]]


def test_windows_opens_the_folder_of_a_document_not_yet_saved(startfile, tmp_path):
    assert desktop.reveal(tmp_path / "never-saved.docx") is True
    assert startfile.calls == [str(tmp_path)]
