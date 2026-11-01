"""The editor's page sends nothing off the machine on its own.

Every request the page makes goes to the host
on 127.0.0.1, and the host's Content-Security-Policy is what makes that hold
whatever the editor's code would like to do. Upstream's bundles still carry an
analytics loader. The one exception is a picture a document links to by its
web address, which is the document's own reference (notes/plans/release-0.5.md,
item D).
"""

from __future__ import annotations

import http.server
import shutil
import threading
from urllib.parse import urlparse

import pytest
from support import find_free_port

from libera import payload as payload_mod

# Every frame keeps what the policy refused, for the test to read.
WATCH_POLICY = (
    "window.__refused = [];"
    "document.addEventListener('securitypolicyviolation', (e) =>"
    " window.__refused.push(e.violatedDirective + ' ' + e.blockedURI));"
)


def refused(page) -> list[str]:
    found = []
    for frame in page.frames:
        found += frame.evaluate("window.__refused || []")
    return found


def left_the_machine(requested: list[str]) -> list[str]:
    return [
        url
        for url in requested
        if urlparse(url).scheme not in {"data", "blob"}
        and urlparse(url).hostname != "127.0.0.1"
    ]


@pytest.mark.parametrize("ext", ["docx", "xlsx", "pptx"])
def test_an_editor_reaches_nothing_but_the_host(editor_with, tmp_path, ext):
    document = tmp_path / f"blank.{ext}"
    shutil.copyfile(payload_mod.resolve().root / "empty" / f"new.{ext}", document)

    editor = editor_with([], document=document, init_script=WATCH_POLICY)
    editor.wait_for_nothing()

    assert left_the_machine(editor.requested) == []
    assert refused(editor.page) == []


def test_a_picture_the_document_links_to_is_fetched(editor_with, tmp_path):
    """The exception: a picture by its web address, which is the document's
    own reference. x2t fetches a Markdown document's; the page may fetch
    others. Either way it arrives, and the policy refuses nothing."""
    picture = next((payload_mod.resolve().root / "sdkjs").rglob("*.png")).read_bytes()
    asked: list[str] = []

    class Pictures(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            asked.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(picture)

        def log_message(self, *_args):
            pass

    port = find_free_port()
    elsewhere = http.server.ThreadingHTTPServer(("127.0.0.1", port), Pictures)
    threading.Thread(target=elsewhere.serve_forever, daemon=True).start()
    document = tmp_path / "linked.md"
    document.write_text(
        f"# Linked\n\n![a picture](http://127.0.0.1:{port}/picture.png)\n",
        encoding="utf-8",
    )
    try:
        editor = editor_with([], document=document, init_script=WATCH_POLICY)
        editor.wait_for_nothing()
    finally:
        elsewhere.shutdown()

    assert "/picture.png" in asked
    assert refused(editor.page) == []
