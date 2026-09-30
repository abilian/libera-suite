"""Payload files are revalidated before a browser reuses them.

WebView2 keeps one HTTP cache for the origin, 127.0.0.1:43110, whatever
payload is behind it. With nothing but a Last-Modified header it reused its
copy of AllFonts.js from the previous payload without asking: a freshly
installed payload with 32 web fonts was driven by an index of 188, the editor
asked for fonts that were not there, and the document never rendered.

Modification time cannot settle it either -- archives keep their files' times,
so two payloads can serve the same name with the same Last-Modified -- hence an
ETag over the file's full path, size and nanosecond mtime.
"""

from __future__ import annotations

import http.client
import os
import threading

import pytest

from libera.host import session
from libera.host.server import handler
from libera.host.session import Host


@pytest.fixture
def serve(tmp_path):
    """A real server over a payload directory, answering on a loopback port.

    Every request binds a session before it looks at a path, so there is one.
    """
    session.configure(Host(payload=tmp_path / "payload", work=tmp_path / "work"))
    servers = []

    def start(root):
        (root / "sdkjs" / "common").mkdir(parents=True, exist_ok=True)
        server = handler.Server(("127.0.0.1", 0), handler.Handler)
        server.payload = root
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return server.server_address[1]

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def get(port, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    response = conn.getresponse()
    body = response.read()
    conn.close()
    return response, body


def test_a_payload_file_says_revalidate_and_names_itself(serve, tmp_path):
    root = tmp_path / "payload"
    port = serve(root)
    (root / "sdkjs" / "common" / "AllFonts.js").write_text("fonts = 32", "utf-8")

    response, body = get(port, "/sdkjs/common/AllFonts.js")

    assert body == b"fonts = 32"
    assert response.getheader("Cache-Control") == "no-cache"
    assert response.getheader("ETag")


def test_an_unchanged_file_is_a_304(serve, tmp_path):
    root = tmp_path / "payload"
    port = serve(root)
    (root / "sdkjs" / "common" / "AllFonts.js").write_text("fonts = 32", "utf-8")
    first, _ = get(port, "/sdkjs/common/AllFonts.js")

    again, body = get(
        port, "/sdkjs/common/AllFonts.js", {"If-None-Match": first.getheader("ETag")}
    )

    assert again.status == 304
    assert body == b""


def test_another_payload_with_the_same_file_times_is_not_a_304(serve, tmp_path):
    """What an archive does: same name, same Last-Modified, different bytes."""
    old, new = tmp_path / "old", tmp_path / "new"
    old_port, new_port = serve(old), serve(new)
    for root, text in ((old, "fonts = 188"), (new, "fonts = 032")):
        f = root / "sdkjs" / "common" / "AllFonts.js"
        f.write_text(text, "utf-8")
    stamp = (old / "sdkjs" / "common" / "AllFonts.js").stat()
    os.utime(
        new / "sdkjs" / "common" / "AllFonts.js",
        ns=(stamp.st_atime_ns, stamp.st_mtime_ns),
    )
    cached, _ = get(old_port, "/sdkjs/common/AllFonts.js")

    fresh, body = get(
        new_port,
        "/sdkjs/common/AllFonts.js",
        {
            "If-None-Match": cached.getheader("ETag"),
            "If-Modified-Since": cached.getheader("Last-Modified"),
        },
    )

    assert fresh.status == 200
    assert body == b"fonts = 032"
