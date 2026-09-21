"""x2t, run out of the payload for real.

The unit tests can check what job file we write; only this can check that x2t
accepts it. Every conversion here starts from the Editor.bin the `opened`
fixture produced, which is the same thing a save does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from libera.host import apps, hooks, session as sessions
from libera.host.convert import export, save_document
from libera.host.session import Host

if TYPE_CHECKING:
    import pathlib


def test_opening_a_document_produces_an_editor_bin(opened: Host):
    assert opened.editor_bin.stat().st_size > 0


OFFERED = [
    (app, ext) for app in apps.ALL if app.editable for _, ext in app.save_formats
]


@pytest.mark.parametrize(
    ("app", "ext"), OFFERED, ids=[f"{a.name}-{e}" for a, e in OFFERED]
)
def test_every_format_every_editor_offers_is_one_x2t_writes(
    open_blank, tmp_path: pathlib.Path, app: apps.App, ext: str
):
    """The Save As popup promises these, for each editor in turn.

    x2t refuses a fair few ids sitting right beside the ones it accepts -- xls
    (258), ppt (130), odg (140), every legacy binary and flat-XML format -- so
    the only way to know which is which is to ask it.
    """
    open_blank(app)
    out = tmp_path / f"out.{ext}"
    assert export(out, app.by_ext[ext]), f"x2t would not write .{ext} for {app.name}"
    assert out.stat().st_size > 0


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_no_editor_offers_a_format_its_converter_does_not_know(app: apps.App):
    assert {ext for _, ext in app.save_formats} <= set(app.by_ext)


def test_plain_save_overwrites_the_document_that_is_open(opened: Host):
    """fileType 0 means "whatever it already was", and no dialog is involved."""
    before = opened.document.stat().st_mtime_ns
    result = save_document({"fileType": 0})

    assert result == {"error": 0, "path": str(opened.document)}
    assert opened.document.stat().st_mtime_ns != before
    # Saved means nothing left to recover.
    assert not opened.unsaved.is_file()


def test_save_as_follows_the_extension_the_user_typed(
    opened: Host, tmp_path: pathlib.Path, monkeypatch
):
    """The chooser's suffix wins over the format the editor asked for.

    The popup and the typed name can disagree; the name is what the user sees,
    so it decides, and the format follows it.
    """
    chosen = tmp_path / "elsewhere.odt"
    monkeypatch.setattr(hooks, "SAVE_PATH_CHOOSER", lambda _name: str(chosen))

    result = save_document({"fileType": 65, "params": "saveas=true"})

    assert result == {"error": 0, "path": str(chosen)}
    assert chosen.read_bytes()[:2] == b"PK"  # an ODF package, not a docx
    # Save As moves the session onto the new file; a plain Save now goes there.
    assert opened.current.read_text() == str(chosen)


def test_a_cancelled_save_as_writes_nothing_and_says_nothing(opened: Host, monkeypatch):
    """Error 1 is DesktopOfflineAppDocumentEndSave's "stay quiet"."""
    monkeypatch.setattr(hooks, "SAVE_PATH_CHOOSER", lambda _name: "")
    before = opened.document.stat().st_mtime_ns

    assert save_document({"fileType": 65, "params": "saveas=true"}) == {"error": 1}
    assert opened.document.stat().st_mtime_ns == before


def test_printing_makes_a_pdf_beside_the_session_not_over_the_document(
    opened: Host, monkeypatch
):
    """Print is a PDF save with no destination: it must not touch the docx."""
    monkeypatch.setattr("libera.host.convert.open_externally", lambda _p: True)
    before = opened.document.stat().st_mtime_ns

    result = save_document({"fileType": 513, "isPrint": True})

    assert result["error"] == 0
    assert result["path"].endswith(f"{opened.document.stem}.pdf")
    assert opened.document.stat().st_mtime_ns == before


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_the_format_table_is_what_x2t_really_does(app: apps.App):
    """The tables are documented as measured, not copied out of the header."""
    for wanted, (ext, fmt) in app.formats.items():
        if wanted == 0:
            continue
        assert wanted == fmt, f"{ext} maps to a different id than it is asked for"


def test_a_viewer_refuses_to_save(opened: Host, tmp_path: pathlib.Path):
    """Diagrams has no format x2t will write, so saving stops at the door.

    Error 1 is DesktopOfflineAppDocumentEndSave's "not saved, say nothing".
    """
    sessions.configure(
        Host(
            payload=opened.payload,
            work=tmp_path / "viewer",
            document=opened.document,
            app=apps.DIAGRAMS,
        ),
        "viewer",
    )
    assert save_document({"fileType": 0}) == {"error": 1}
