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
    user_id, name = desktop.lookup_local_user()

    # index.html.desktop falls back to Chuk.Gek for name and uid-901 for id
    # whenever these are absent, so both have to be there.
    assert query["username"] == [name]
    assert query["userid"] == [user_id]


def test_a_name_with_a_space_survives_the_url(monkeypatch):
    """Full names have spaces in them, and an unencoded one truncates the
    parameter.

    A name with a space, every time: it used to be whatever this machine's
    user was called, and the assertion ran only if that had a space in it.
    """
    monkeypatch.setattr(
        server.handler, "lookup_local_user", lambda: ("jdupont", "Jeanne Dupont")
    )

    url = server.make_editor_url(43110, a_window(), "Note.docx")

    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["username"] == ["Jeanne Dupont"]
