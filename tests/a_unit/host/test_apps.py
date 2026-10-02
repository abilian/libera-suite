"""Which editor opens what, and what each one claims it can do."""

from __future__ import annotations

from pathlib import Path

import pytest

from libera.host import apps


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.docx", "words"),
        ("report.ODT", "words"),
        ("budget.xlsx", "tables"),
        ("budget.csv", "tables"),
        ("deck.pptx", "slides"),
        ("deck.odp", "slides"),
        ("plan.vsdx", "diags"),
        ("notes", "words"),
        ("archive.tar.gz", "words"),
    ],
)
def test_the_extension_decides_which_editor_opens_it(name: str, expected: str):
    """Words is the fallback: an unknown file is a document far more often."""
    assert apps.choose_for(Path(name)).name == expected


def test_no_extension_lands_in_two_editors():
    """Two claims on one extension would make dispatch depend on list order."""
    seen: dict[str, str] = {}
    for app in apps.ALL:
        for ext in app.opens:
            assert ext not in seen, (
                f".{ext} is claimed by {seen.get(ext)} and {app.name}"
            )
            seen[ext] = app.name


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_an_editor_opens_everything_it_saves_except_pdf(app: apps.App):
    """Offering to write a format the editor cannot read back is a trap.

    PDF is the deliberate exception, the way it is in every office suite: it
    is an export, and reopening one is pdfeditor's job, which nothing here
    routes to yet.
    """
    written = {ext for _, ext in app.save_formats} - {"pdf"}
    assert written <= app.opens


@pytest.mark.parametrize("app", apps.ALL, ids=lambda a: a.name)
def test_a_viewer_has_no_blank_and_an_editor_does(app: apps.App):
    """The two halves of "can this editor make a new document" must agree."""
    assert (app.blank is not None) == app.editable


@pytest.mark.parametrize(
    "app", [a for a in apps.ALL if a.editable], ids=lambda a: a.name
)
def test_recent_id_is_the_id_its_own_extension_is_written_with(app):
    """Two tables naming one number: they must not drift apart."""
    assert app.recent_id == app.ids_by_ext[app.ext]
