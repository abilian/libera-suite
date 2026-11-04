"""Files dropped on a window: the page knows their names, the drag their paths.

pywebview's native layer records each dropped file as (name, path) in
`webview.dom._dnd_state`, a private dict. The host reads it directly
(`window.take_dropped`), so its shape is checked here against the installed
pywebview: an upgrade that changes it fails this file instead of every drop.
On GTK pywebview's handler records nothing, so `window.gtk` replaces it.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest
import webview.dom
from support import ScriptedShell

from libera.host import apps, hooks, window
from libera.host.server import document, opening
from libera.host.server.api import Refused, Request
from libera.host.session import Session
from libera.host.window import gtk


def test_pywebview_still_keeps_the_record_this_reads():
    state = webview.dom._dnd_state

    assert isinstance(state["num_listeners"], int)
    assert isinstance(state["paths"], list)


@pytest.fixture
def record(monkeypatch):
    """A drop record of the test's own, in place of pywebview's."""
    state = {"num_listeners": 0, "paths": []}
    monkeypatch.setattr(webview.dom, "_dnd_state", state)
    return state


def test_listening_is_what_makes_the_native_layer_record(record):
    window.listen_for_drops()

    assert record["num_listeners"] == 1


def test_the_newest_record_of_a_name_wins_and_every_one_goes(record):
    """A drop the page never asked about must not answer for the next file of
    the same name: that would insert, or open, a file nobody dropped."""
    record["paths"] += [
        ("photo.png", "/old/photo.png"),
        ("photo.png", "/new/photo.png"),
    ]

    assert window.take_dropped(["photo.png"]) == [Path("/new/photo.png")]
    assert record["paths"] == []


def test_a_name_nobody_dropped_resolves_to_nothing(record, monkeypatch):
    monkeypatch.setattr(window.windows, "DROP_WAIT", 0.05)
    record["paths"] += [("photo.png", "/a/photo.png")]

    found = window.take_dropped(["photo.png", "passwords.txt"])

    assert found == [Path("/a/photo.png")]


def test_a_record_that_arrives_late_is_waited_for(record):
    """On Windows the paths come in a message the page posts just before it
    asks, handled on another thread."""

    def arrive() -> None:
        time.sleep(0.1)
        record["paths"].append(("report.docx", "/docs/report.docx"))

    threading.Thread(target=arrive).start()

    assert window.take_dropped(["report.docx"]) == [Path("/docs/report.docx")]


def test_which_files_are_documents():
    assert apps.is_document(Path("/a/Report.DOCX"))
    assert apps.is_document(Path("/a/budget.ods"))
    assert not apps.is_document(Path("/a/photo.png"))
    assert not apps.is_document(Path("/a/archive.zip"))


def drop(tmp_path, monkeypatch, found: list[Path], body: object):
    opened: list[Path] = []
    done = threading.Event()

    def open_window(document, _app=None):
        opened.append(document)
        done.set()
        return True

    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(take_dropped=lambda _names: found, open_window=open_window),
    )
    asking = Session(payload=tmp_path / "payload", work=tmp_path / "1")
    answer = opening.take_drop(Request(asking, body=json.dumps(body).encode()))
    if any(apps.is_document(path) for path in found):
        done.wait(5)
    return json.loads(answer.body), opened


def dropped_files(tmp_path) -> list[Path]:
    found = [tmp_path / "report.docx", tmp_path / "photo.png"]
    for path in found:
        path.touch()
    return found


def test_documents_open_in_windows_and_the_rest_go_back(tmp_path, monkeypatch):
    report, photo = found = dropped_files(tmp_path)

    answer, opened = drop(
        tmp_path, monkeypatch, found, {"names": ["report.docx", "photo.png"]}
    )

    assert opened == [report]
    assert answer == {"paths": [str(photo)]}


def test_a_dropped_file_out_of_reach_is_said_and_not_opened(tmp_path, monkeypatch):
    """A Flatpak's drag names files outside what its sandbox sees. Opened, the
    document read as damaged; inserted, the picture did nothing at all."""
    here = tmp_path / "here.png"
    here.touch()
    told: list[tuple[str, str]] = []
    said = threading.Event()
    opened: list[Path] = []

    def tell(heading: str, detail: str) -> None:
        told.append((heading, detail))
        said.set()

    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            take_dropped=lambda _names: [
                tmp_path / "gone.docx",
                tmp_path / "gone.png",
                here,
            ],
            open_window=lambda document, _app=None: opened.append(document),
            tell=tell,
        ),
    )
    asking = Session(payload=tmp_path / "payload", work=tmp_path / "1")

    answer = opening.take_drop(Request(asking, body=b'{"names": null}'))

    assert said.wait(5)
    assert "gone.docx, gone.png" in told[0][0]
    assert opened == []
    assert json.loads(answer.body) == {"paths": [str(here)]}
    assert asking.offered == {here}


def test_a_body_that_is_not_a_list_of_names_is_refused(tmp_path, monkeypatch):
    with pytest.raises(Refused, match="names"):
        drop(tmp_path, monkeypatch, [], {"names": "photo.png"})


def test_only_a_dropped_file_can_be_copied_in(tmp_path, monkeypatch):
    """GET media/<name> serves what media-import copied in, so a path of the
    page's own choosing read any file the user can, from any script in our
    origin. The drop is what puts a path in the page's hands."""
    picture = tmp_path / "photo.png"
    picture.write_bytes(b"\x89PNG picture")
    secret = tmp_path / "passwords.txt"
    secret.write_text("hunter2", encoding="utf-8")
    monkeypatch.setattr(
        hooks, "shell", ScriptedShell(take_dropped=lambda _names: [picture])
    )
    asking = Session(payload=tmp_path / "payload", work=tmp_path / "1")

    def ask(path: Path) -> Request:
        return Request(asking, body=json.dumps({"path": str(path)}).encode())

    opening.take_drop(Request(asking, body=b'{"names": ["photo.png"]}'))
    copied = json.loads(document.import_media(ask(picture)).body)["name"]

    assert (asking.media / copied).read_bytes() == b"\x89PNG picture"
    with pytest.raises(Refused) as refused:
        document.import_media(ask(secret))
    assert refused.value.status == 403
    assert sorted(f.name for f in asking.media.iterdir()) == [copied]


def test_a_page_told_no_names_takes_all_that_was_recorded(record):
    """WebKitGTK tells a page neither files nor names."""
    record["paths"] += [("a.png", "/x/a.png"), ("b.docx", "/x/b.docx")]

    assert window.take_dropped(None) == [Path("/x/a.png"), Path("/x/b.docx")]
    assert record["paths"] == []


def test_a_drop_with_no_names_opens_what_the_drag_carried(tmp_path, monkeypatch):
    report, photo = found = dropped_files(tmp_path)

    answer, opened = drop(tmp_path, monkeypatch, found, {"names": None})

    assert opened == [report]
    assert answer == {"paths": [str(photo)]}


def test_pywebview_still_has_the_handler_gtk_replaces():
    """Replacing a method it no longer has would do nothing, silently."""
    backend = pytest.importorskip("webview.platforms.gtk", exc_type=ImportError)

    assert callable(backend.BrowserView.on_drag_data)


class Dragged:
    """What GTK hands a drag's handler, for one target."""

    def __init__(self, target: str, uris: list[str] | None) -> None:
        self.target, self.uris = target, uris

    def get_target(self) -> Dragged:
        return self

    def name(self) -> str:
        return self.target

    def get_uris(self) -> list[str] | None:
        return self.uris


def record_drag(data: Dragged) -> None:
    gtk._record_drag(None, None, None, 0, 0, data, 0, 0)


def test_gtk_records_a_uri_list_with_its_escapes_undone(record):
    record_drag(Dragged("text/uri-list", ["file:///x/a%20b%20%C3%A9.png"]))

    assert record["paths"] == [("a b é.png", "/x/a b é.png")]


def test_gtk_keeps_only_local_files():
    uris = ["file:///x/a.png", "https://example.org/b.png", "sftp://host/c.png"]

    assert gtk.files_in_uri_list(uris) == [("a.png", "/x/a.png")]


def test_gtk_keeps_a_file_name_that_is_not_text():
    ((name, path),) = gtk.files_in_uri_list(["file:///x/caf%E9.png"])

    assert os.fsencode(name) == b"caf\xe9.png"
    assert os.fsencode(path) == b"/x/caf\xe9.png"


def test_each_drag_replaces_the_last(record):
    """One that crossed a window and went on must not open with the next."""
    record_drag(Dragged("text/uri-list", ["file:///x/crossed.docx"]))
    record_drag(Dragged("text/uri-list", ["file:///x/dropped.docx"]))

    assert record["paths"] == [("dropped.docx", "/x/dropped.docx")]


def test_another_form_of_a_drag_leaves_its_files_recorded(record):
    record_drag(Dragged("text/uri-list", ["file:///x/a.png"]))
    record_drag(Dragged("text/plain", None))

    assert record["paths"] == [("a.png", "/x/a.png")]


def test_a_link_clears_the_drag_before_it(record):
    record_drag(Dragged("text/uri-list", ["file:///x/crossed.docx"]))
    record_drag(Dragged("text/uri-list", ["https://example.org/"]))

    assert record["paths"] == []
