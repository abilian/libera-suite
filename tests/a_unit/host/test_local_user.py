"""Who the editor says you are ends up in documents you send to other people.

Upstream's placeholder is "Chuk.Gek", and it is not only the face in the
corner: it is the author recorded against every tracked change, and it is
written into the saved file.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from libera.host import apps, desktop, server
from libera.host.session import Session
from libera.payload import locate


def a_window() -> Session:
    """make_editor_url takes the session, for its doctype and its id."""
    return Session(payload=Path("/payload"), work=Path("/abc"), app=apps.WORDS)


def test_the_user_has_a_name_and_an_id():
    user_id, name = desktop.lookup_local_user()
    assert user_id
    assert name
    assert "Chuk" not in name


def test_the_editor_is_told_both():
    url = server.make_editor_url(43110, a_window(), "Note.docx")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    name = desktop.lookup_local_user()[1]

    # index.html.desktop falls back to Chuk.Gek for name and uid-901 for id
    # whenever these are absent, so both have to be there.
    assert query["username"] == [name]
    assert query["userid"][0]


def test_the_editor_is_not_told_the_login(tmp_path, monkeypatch):
    """The PDF editor writes the id into every annotation, as /OUserID, so the
    login went out in each PDF saved (measured, 2026-10-29). Nothing else
    reads it -- a lock file has the login from desktop.lookup_local_user --
    but it has to stay the same from one session to the next, since it is
    how an annotation is known as yours."""
    monkeypatch.setattr(locate, "get_state_dir", lambda: tmp_path)
    login = desktop.lookup_local_user()[0]

    def told() -> str:
        # A new process each time, as far as the id knows.
        desktop.editor_user_id.cache_clear()
        url = server.make_editor_url(43110, a_window(), "Note.pdf")
        return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["userid"][0]

    try:
        first, second = told(), told()
    finally:
        desktop.editor_user_id.cache_clear()

    assert first == second
    assert login not in first
    assert (tmp_path / "editor-user-id").read_text(encoding="utf-8") == first


def test_a_name_with_a_space_survives_the_url(monkeypatch):
    """Full names have spaces in them, and an unencoded one truncates the
    parameter.

    A name with a space, every time: it used to be whatever this machine's
    user was called, and the assertion ran only if that had a space in it.
    """
    monkeypatch.setattr(
        server.editor, "lookup_local_user", lambda: ("jdupont", "Jeanne Dupont")
    )

    url = server.make_editor_url(43110, a_window(), "Note.docx")

    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["username"] == ["Jeanne Dupont"]


def test_a_configured_name_comes_first(tmp_path, monkeypatch):
    """For a document that has to go out under another name than the
    account's. The name does not change the id."""
    config = tmp_path / "config.toml"
    config.write_text('user_name = "Jeanne Dupont"\n', encoding="utf-8")
    monkeypatch.setattr(locate, "get_config_file", lambda: config)
    desktop.lookup_local_user.cache_clear()
    try:
        url = server.make_editor_url(43110, a_window(), "Note.docx")
        login = desktop.lookup_local_user()[0]
    finally:
        desktop.lookup_local_user.cache_clear()

    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["username"] == ["Jeanne Dupont"]
    assert login != "Jeanne Dupont"
    assert "Jeanne" not in query["userid"][0]


def test_without_a_config_file_it_is_the_account_name(tmp_path, monkeypatch):
    monkeypatch.setattr(locate, "get_config_file", lambda: tmp_path / "none.toml")
    desktop.lookup_local_user.cache_clear()
    try:
        login, name = desktop.lookup_local_user()
    finally:
        desktop.lookup_local_user.cache_clear()

    assert name
    assert name != "Jeanne Dupont"
    assert login
