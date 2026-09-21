"""Who the editor says you are ends up in documents you send to other people.

Upstream's placeholder is "Chuk.Gek", and it is not only the face in the
corner: it is the author recorded against every tracked change, and it is
written into the saved file.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from libera.host import apps, desktop, server
from libera.host.session import Host, use


def a_window() -> None:
    """editor_url reads the session for its doctype, so bind one.

    Every caller in the application does -- cmd_serve and both window paths
    configure a session first -- but a test has to say so.
    """
    use(Host(payload=Path("/payload"), work=Path("/work"), app=apps.WORDS))


def test_the_user_has_a_name_and_an_id():
    user_id, name = desktop.local_user()
    assert user_id
    assert name
    assert "Chuk" not in name


def test_the_editor_is_told_both():
    a_window()
    url = server.editor_url(43110, "Note.docx", "abc")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    user_id, name = desktop.local_user()

    # index.html.desktop falls back to Chuk.Gek for name and uid-901 for id
    # whenever these are absent, so both have to be there.
    assert query["username"] == [name]
    assert query["userid"] == [user_id]


def test_a_name_with_a_space_survives_the_url():
    """Full names have spaces in them, and an unencoded one truncates the
    parameter."""
    a_window()
    url = server.editor_url(43110, "Note.docx", "abc")
    _, name = desktop.local_user()
    if " " in name:
        assert urllib.parse.quote(name) in url
