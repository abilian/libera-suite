"""What 0.6 and earlier downloaded: offered for removal once, removed only
when the answer is yes."""

from __future__ import annotations

import json

import pytest

from libera.host.server import start_window
from libera.host.server.api import Request
from libera.payload import leftovers, locate


@pytest.fixture(name="state")
def a_state_folder_with_an_old_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(locate, "get_state_dir", lambda: tmp_path)
    old = tmp_path / "payload" / "0.6" / "bin"
    old.mkdir(parents=True)
    (old / "x2t").write_bytes(b"x" * 3_000_000)
    return tmp_path


def ask(remove: bool | None = None) -> dict:
    if remove is None:
        response = start_window.serve_old_payloads(Request(None))
    else:
        body = json.dumps({"remove": remove}).encode()
        response = start_window.answer_old_payloads(Request(None, body))
    return json.loads(response.body)


def test_the_start_window_is_told_their_size(state):
    assert ask() == {"size_mb": 3}


def test_kept_they_stay_and_are_not_offered_again(state):
    assert ask(remove=False) == {"removed": False}

    assert (state / "payload" / "0.6").is_dir()
    assert ask() == {"size_mb": 0}


def test_removed_they_go(state):
    assert ask(remove=True) == {"removed": True}

    assert not (state / "payload").exists()
    assert ask() == {"size_mb": 0}


def test_with_none_there_is_nothing_to_offer(tmp_path, monkeypatch):
    monkeypatch.setattr(locate, "get_state_dir", lambda: tmp_path)
    assert not leftovers.should_offer()
    assert ask() == {"size_mb": 0}
