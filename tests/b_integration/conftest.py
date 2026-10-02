"""A live host server, against the real payload.

These exercise the HTTP surface the editor actually talks to, so they need a
payload: the endpoints serve files out of it, and saving runs x2t from it.
Without one the whole directory skips rather than pretending to pass.
"""

from __future__ import annotations

import json
import shutil
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from support import find_free_port

from libera import payload as payload_mod
from libera.host import opening, server, session as sessions
from libera.host.session import Session

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass
class LiveHost:
    """The server, plus the three ways the bridge talks to it."""

    url: str
    session: str
    host: Session
    document: Path

    def at(self, path: str, session: str | None = None) -> str:
        """A /__host__/ URL, carrying a session the way the bridge does."""
        sid = self.session if session is None else session
        joiner = "&" if "?" in path else "?"
        return f"{self.url}/__host__/{path}{joiner}session={sid}"

    def get(self, path: str, session: str | None = None) -> bytes:
        with urllib.request.urlopen(self.at(path, session), timeout=30) as r:
            return r.read()

    def json(self, path: str, session: str | None = None) -> Any:
        return json.loads(self.get(path, session))

    def get_static(self, path: str) -> bytes:
        """Out of the payload, the way the editor loads its own assets."""
        with urllib.request.urlopen(self.url + path, timeout=30) as r:
            return r.read()

    def post(
        self,
        path: str,
        body: bytes = b"",
        session: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        """Status and body, because half of what we check here is the status."""
        req = urllib.request.Request(
            self.at(path, session), data=body, method="POST", headers=headers or {}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()


@pytest.fixture
def opened(tmp_path, sample_document) -> Iterator[Session]:
    """One session with the sample document open, isolated from the user's own.

    Opening runs x2t, so this is where the payload first has to be real.

    A copy of the sample, not the sample: a plain save writes over the
    document that is open, and the sample is the session-wide one the e2e tier
    and render.py's thresholds read. Saved over, it made a full run read a
    different document from a tier run on its own.
    """
    sessions.SESSIONS.clear()
    document = tmp_path / sample_document.name
    shutil.copyfile(sample_document, document)
    session = Session(
        payload=payload_mod.resolve().root,
        work=tmp_path / "sessions" / "0",
        document=document,
    )
    sessions.configure(session)
    opening.open_document(session, document)
    try:
        yield session
    finally:
        sessions.SESSIONS.clear()


@pytest.fixture(scope="module")
def live_payload():
    """The installed payload's root, for tests that only read it."""
    return payload_mod.resolve().root


@pytest.fixture
def open_blank(tmp_path):
    """Open the payload's own blank for one editor, and return its session.

    A factory rather than a parametrized fixture: the callers want to say which
    editor inline, beside the format they are checking it can write.
    """

    def _open(app):
        payload = payload_mod.resolve().root
        blank = tmp_path / f"blank.{app.ext}"
        shutil.copyfile(payload / "empty" / app.blank, blank)
        session = Session(
            payload=payload, work=tmp_path / app.name, document=blank, app=app
        )
        sessions.configure(session)
        opening.open_document(session, blank)
        return session

    return _open


@pytest.fixture
def live(opened) -> Iterator[LiveHost]:
    """The server, on top of that session."""
    port = find_free_port()
    httpd = server.make_server(port, opened)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    assert opened.document is not None
    try:
        yield LiveHost(f"http://127.0.0.1:{port}", "0", opened, opened.document)
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
