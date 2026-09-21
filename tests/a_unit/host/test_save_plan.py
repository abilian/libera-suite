"""What a save request means, decided before anything touches the disk.

save_document used to work this out inline, mixed with making directories,
running x2t, copying files out and opening a PDF viewer -- sixty lines and
fourteen branches that could only be tested with a session, a dialog hook and
a converter. The rules are the interesting part and they are pure, so they
live in plan_save and are checked here.
"""

from __future__ import annotations

import pathlib

import pytest

from libera.host import apps
from libera.host.convert import plan_save

DOCX = pathlib.Path("/home/u/Rapport.docx")


def test_plain_save_overwrites_the_document_that_is_open():
    plan = plan_save({}, apps.WORDS, DOCX)

    assert plan.target == DOCX
    assert plan.ext == "docx"
    assert not plan.printing
    assert not plan.asks_where


def test_save_as_asks_even_though_the_format_matches():
    plan = plan_save({"params": "saveas=true"}, apps.WORDS, DOCX)

    assert plan.asks_where


def test_a_different_format_is_a_save_as_whatever_the_editor_called_it():
    """Asking for .odt from an open .docx must not overwrite the .docx."""
    odt = next(fid for fid, (ext, _) in apps.WORDS.formats.items() if ext == "odt")

    plan = plan_save({"fileType": odt}, apps.WORDS, DOCX)

    assert plan.ext == "odt"
    assert plan.target is None, "it would have written .odt over the open .docx"


def test_printing_has_no_destination():
    """The file is a means to an end: it goes to the session and then to a viewer."""
    plan = plan_save({"isPrint": True}, apps.WORDS, DOCX)

    assert plan.printing
    assert plan.target is None
    assert not plan.asks_where, "a print never asks where to put it"


def test_printing_wins_over_save_as():
    plan = plan_save({"isPrint": True, "params": "saveas=true"}, apps.WORDS, DOCX)

    assert not plan.asks_where


def test_an_untitled_document_has_nothing_to_overwrite():
    plan = plan_save({}, apps.WORDS, None)

    assert plan.target is None


@pytest.mark.parametrize("app", [apps.WORDS, apps.TABLES, apps.SLIDES])
def test_an_unknown_format_id_falls_back_to_the_editors_own(app):
    """fileType 0 is what the editor sends when it means "the usual"."""
    plan = plan_save({"fileType": 99999}, app, None)

    assert (plan.ext, plan.fmt) == app.formats[0]
