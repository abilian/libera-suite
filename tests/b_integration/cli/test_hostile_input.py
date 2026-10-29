"""A converted document cannot make x2t read a file or the network for it.

The converter is libxml2 2.9.2, called with its default options, which
resolve no external entity; this holds it there. Measured on 2026-10-29,
notes/plans/converter-hardening.md (probe 1): neither a file nor a URL was
read, and the external DTD was not fetched.
"""

from __future__ import annotations

import http.server
import re
import threading
import zipfile

import pytest

from libera import cli
from libera.host import apps

MARKER = "zqx-file-content-7731"


class Listener(http.server.BaseHTTPRequestHandler):
    asked: list[str]

    def do_GET(self):
        self.asked.append(self.path)
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_):
        pass


@pytest.fixture
def listener():
    """A web server on loopback that records every request made to it."""
    Listener.asked = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1], Listener.asked
    server.shutdown()


def test_external_entities_are_not_read(tmp_path, monkeypatch, live_payload, listener):
    port, asked = listener
    secret = tmp_path / "secret.txt"
    secret.write_text(MARKER)
    with zipfile.ZipFile(live_payload / "empty" / apps.WORDS.blank) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    declarations = (
        f'<!DOCTYPE w:document [<!ENTITY f SYSTEM "{secret.as_uri()}">'
        f'<!ENTITY h SYSTEM "http://127.0.0.1:{port}/entity">'
        f'<!ENTITY % p SYSTEM "http://127.0.0.1:{port}/dtd"> %p;]>'
    )
    body = "<w:p><w:r><w:t>file:&f; http:&h; end</w:t></w:r></w:p>"
    document = parts["word/document.xml"].decode()
    document = re.sub(r"(<\?xml[^>]*\?>)", lambda m: m[1] + declarations, document)
    document, n = re.subn(
        r"(<w:body>).*?(<w:sectPr\b)",
        lambda m: m[1] + body + m[2],
        document,
        flags=re.DOTALL,
    )
    assert n == 1
    assert "<!DOCTYPE" in document
    parts["word/document.xml"] = document.encode()
    with zipfile.ZipFile(tmp_path / "entities.docx", "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--convert", "entities.docx", "-t", "txt"]) == 0

    text = (tmp_path / "entities.txt").read_text(encoding="utf-8-sig")
    # The text around the entities came through, so the paragraph was read.
    assert "file:" in text
    assert "end" in text
    assert MARKER not in text
    assert asked == []
