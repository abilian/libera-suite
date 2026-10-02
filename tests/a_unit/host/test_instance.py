"""One running Libera Suite: a second launch hands its documents to the first.

The hand-off is what double-clicking a second document does on Windows, where
every double-click is a new process. What can go wrong is who gets to open a
file (the token), what a stale announcement costs (nothing but a start), and
whose announcement goes when an instance exits (only its own).
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest
from support import ScriptedShell

from libera.host import hooks, instance
from libera.host.server import post
from libera.payload import locate


@pytest.fixture
def state(tmp_path, monkeypatch):
    """A temporary state directory, with instance.json inside it.

    The suite-wide `no_running_instance` fixture points instance.get_path at a
    temporary file of its own; these tests also need get_state_dir, so both point
    at the same directory here -- which is where the real path() would put it.
    """
    monkeypatch.setattr(locate, "get_state_dir", lambda: tmp_path)
    monkeypatch.setattr(instance, "get_path", lambda: tmp_path / "instance.json")
    return tmp_path


@pytest.fixture
def running(state):
    """A stand-in for the first instance's server: records what it is sent."""
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            body = b'{"opened": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    instance.announce(server.server_address[1])
    yield received
    server.shutdown()
    server.server_close()


def test_nothing_announced_means_start_here(state):
    assert instance.hand_off([]) is False


def test_a_stale_announcement_means_start_here(state):
    """A crash leaves the file behind, and nothing listens on its port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
    instance.announce(dead_port)

    assert instance.hand_off([state / "a.docx"]) is False


def test_a_running_instance_takes_the_documents(running, tmp_path):
    doc = tmp_path / "Report.docx"

    assert instance.hand_off([doc]) is True
    assert running == [{"token": instance.TOKEN, "documents": [str(doc)]}]


def test_withdraw_leaves_another_instances_announcement(state):
    """The first instance to exit must not orphan the one still running."""
    (state / "instance.json").write_text(
        json.dumps({"port": 1, "token": "someone-else", "pid": 1}), encoding="utf-8"
    )
    instance.withdraw()
    assert (state / "instance.json").is_file()

    instance.announce(2)
    instance.withdraw()
    assert not (state / "instance.json").exists()


@pytest.fixture
def handler():
    """Enough of server.Handler for take_hand_off: a body, and its answers."""

    def make(body: dict):
        h = SimpleNamespace(errors=[], sent=[])
        h.read_body = lambda: json.dumps(body).encode()
        h.send_error = h.errors.append
        h.send_bytes = lambda data, _ctype: h.sent.append(json.loads(data))
        return h

    return make


@pytest.fixture
def opened(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            open_window=lambda doc, _app=None: calls.append(doc),
            show_start_window=lambda: calls.append("start"),
        ),
    )
    return calls


def test_a_wrong_token_opens_nothing(handler, opened, tmp_path):
    """Any page in any browser can POST to 127.0.0.1; the token is the fence."""
    doc = tmp_path / "Report.docx"
    doc.write_bytes(b"PK")
    h = handler({"token": "guessed", "documents": [str(doc)]})

    post.take_hand_off(h)

    assert h.errors == [403]
    assert opened == []


def test_the_right_token_opens_each_file_that_exists(handler, opened, tmp_path):
    doc = tmp_path / "Report.docx"
    doc.write_bytes(b"PK")
    h = handler({
        "token": instance.TOKEN,
        "documents": [str(doc), str(tmp_path / "gone.docx")],
    })

    post.take_hand_off(h)

    assert opened == [doc]
    assert h.sent == [{"opened": True}]


def test_no_documents_puts_the_start_window_up(handler, opened):
    """The icon clicked while Libera Suite is already open."""
    h = handler({"token": instance.TOKEN, "documents": []})

    post.take_hand_off(h)

    assert opened == ["start"]
