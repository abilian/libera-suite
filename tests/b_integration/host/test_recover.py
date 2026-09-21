"""Recovering from an editor that threw.

An uncaught exception leaves the editor's state a guess, and the window looks
alive while doing nothing. The host offers a reload; this is the half of that
which can lose work, so it is the half worth testing.

The editor works on Editor.bin plus a log of changes it streams as you type. A
reload hands it Editor.bin alone -- the document as it was opened -- so the
edits have to be folded into the base first, or reloading silently undoes
everything since the file was opened.
"""

from __future__ import annotations

import re
import zipfile
from typing import TYPE_CHECKING

from libera.host import server, window
from libera.host.convert import save_document

if TYPE_CHECKING:
    from libera.host.session import Host


def a_change(host: Host, raw: str) -> None:
    """What the editor streams as someone types."""
    log = host.doc / "changes" / "changes0.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f'"{raw}",')


def test_folding_with_nothing_to_fold_is_a_no_op(opened: Host):
    before = opened.editor_bin.read_bytes()
    assert window.fold_changes_in()
    assert opened.editor_bin.read_bytes() == before


def test_folding_rebuilds_editor_bin(opened: Host):
    """A log present means the base is rebuilt through the converter.

    This says the round trip ran and produced something, not that a particular
    edit survived it: the change records here are fabricated, and only the
    editor can make real ones. What a real edit survives is
    test_the_document_survives_the_round_trip below.
    """
    before = opened.editor_bin.read_bytes()
    a_change(opened, "AgAAAA==")

    assert window.fold_changes_in()

    assert opened.editor_bin.stat().st_size > 0
    assert opened.editor_bin.read_bytes() != before, "the base was not rebuilt"


def test_folding_empties_the_log_it_folded(opened: Host):
    """Otherwise the next save applies them twice."""
    a_change(opened, "AgAAAA==")
    assert window.fold_changes_in()

    log = opened.doc / "changes" / "changes0.json"
    assert not log.is_file() or log.stat().st_size == 0


def test_the_document_survives_the_round_trip(opened: Host):
    """Folding must not cost the document itself.

    Out through x2t and back in is two lossy-looking conversions in a row, on
    a document the user has not saved. If the text is not there afterwards,
    the recovery is worse than the fault it recovers from.
    """
    a_change(opened, "AgAAAA==")
    window.fold_changes_in()

    assert save_document({"fileType": 0})["error"] == 0

    text = re.sub(
        r"<[^>]+>",
        "",
        zipfile
        .ZipFile(opened.document)
        .read("word/document.xml")
        .decode("utf-8", "replace"),
    )
    assert "Second paragraph" in text, "the round trip lost the document"


def test_the_host_stays_quiet_when_the_editor_speaks(opened: Host, monkeypatch):
    """Two dialogs for one fault is what a user called confusing.

    asc_onError means the editor is already putting its own message up. File >
    Reload stays the way out, and it is always there.
    """
    offered: list[str] = []
    monkeypatch.setattr(server.post.hooks, "BROKEN", lambda _s, m: offered.append(m))
    server.OFFERED.clear()

    server.broken("TypeError: endReporter is not a function", quiet=True)

    assert offered == []


def test_an_uncaught_error_the_editor_says_nothing_about_is_offered(
    opened: Host, monkeypatch
):
    """Nothing else would tell the user anything at all."""
    offered: list[str] = []
    monkeypatch.setattr(server.post.hooks, "BROKEN", lambda _s, m: offered.append(m))
    server.OFFERED.clear()

    server.broken("TypeError: x is not a function")

    assert offered == ["TypeError: x is not a function"]


def test_an_uncaught_error_is_offered_once(opened: Host, monkeypatch):
    """An editor that throws once throws again; a dialog per repeat is worse
    than the fault."""
    seen: list[str] = []
    monkeypatch.setattr(server.post.hooks, "BROKEN", lambda _s, m: seen.append(m))
    server.OFFERED.clear()

    server.broken("TypeError: x is not a function")
    server.broken("TypeError: x is not a function")

    assert seen == ["TypeError: x is not a function"]


def test_nothing_is_offered_where_there_is_no_window(opened: Host, monkeypatch):
    """`libera --serve` and the harness have no way to ask, and must not
    block waiting to."""
    monkeypatch.setattr(server.post.hooks, "BROKEN", None)
    server.OFFERED.clear()

    server.broken("TypeError: x is not a function")  # must not raise
