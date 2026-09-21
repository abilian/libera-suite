"""Does the editor actually come up, and does it show the document?

Everything here reads one headless run. Bridge traffic says what was asked
for; the screenshot says what was drawn, and the two disagree more often than
you would think -- a document whose styles collapsed the leading rendered as
overlapping struck-through lines while every call still arrived.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from support import render

if TYPE_CHECKING:
    from c_e2e.conftest import Editor

# asc_onError is the editor telling the user something went wrong. It is not a
# JS exception, so it has to be listed by name.
LOUD = ("error", "reject", "asc_onError")


def test_the_editor_finishes_loading_the_document(editor: Editor):
    assert "onDocumentContentReady" in editor.calls


def test_nothing_went_wrong_out_loud(editor: Editor):
    loud = [
        f"[{e['frame']}] {e['kind']}: {e['text'].splitlines()[0][:140]}"
        for e in editor.report["errors"]
        if e["kind"] in LOUD
    ]
    assert loud == []


def test_the_bridge_answered_the_editor(editor: Editor):
    """A floor, not a count: the exact number moves whenever the editor does.

    Far fewer than this and the bridge failed to install, which otherwise looks
    like a slow load rather than a broken one.
    """
    assert len(editor.calls) > 10


def test_the_editor_asked_the_host_to_spell_check(editor: Editor):
    """Spell checking fails silently: it asks, gets nothing, underlines nothing.

    A broken worker raises and is caught above; this catches the wiring being
    gone altogether, which nothing else here would notice.
    """
    assert "SpellCheck" in editor.calls


def test_every_picture_in_the_document_was_served(illustrated_editor: Editor):
    """Media the host fails to redirect never reaches the network at all.

    No request, no console error, just a missing picture -- so compare what the
    document holds against what was actually asked for.
    """
    report = illustrated_editor.report
    expected = set(report["media_expected"])
    assert expected, "the sample carries no pictures; this assertion proved nothing"
    assert expected <= set(report["media_served"])


def test_what_was_drawn_looks_like_laid_out_text(editor: Editor):
    """Rows of ink, grouped into bands, spaced the way lines of text are."""
    assert editor.shot.is_file(), "the page never posted its own render"
    assert render.check(str(editor.shot)) == []


# --- the other editors ------------------------------------------------------


def test_every_editor_comes_up(blank_editor: Editor):
    """Tables and Slides, each loaded through the doctype in its own URL.

    api.js's appMap turns doctype into an editor directory, so getting it wrong
    silently serves Words a spreadsheet -- or serves nothing at all.
    """
    assert "onDocumentContentReady" in blank_editor.calls


def test_no_editor_reports_anything_out_loud(blank_editor: Editor):
    loud = [
        f"[{e['frame']}] {e['kind']}: {e['text'].splitlines()[0][:140]}"
        for e in blank_editor.report["errors"]
        if e["kind"] in LOUD
    ]
    assert loud == []


def test_each_editor_answers_through_the_same_bridge(blank_editor: Editor):
    """Same floor as Words: far fewer means the bridge never installed."""
    assert len(blank_editor.calls) > 10


# --- what the editor asked for and did not get ------------------------------

# Everything else is a missing payload asset, which is the quietest failure
# this project has: no error, no broken request, the feature simply is not
# there. Slides had no theme gallery for as long as nobody read the log.
#
#   favicon.ico   the browser asks unprompted; not the application
#   plugins.json  we ship no plugins
#   Contents.json upstream's manual, 84 MB in eight languages, deliberately
#                 stripped -- see notes/04-plan.md
EXPECTED_404 = ("/favicon.ico", "/plugins.json", "/help/en/Contents.json")


def unexpected(report: dict) -> list[str]:
    return [
        path
        for path in report["not_found"]
        if not any(path.endswith(known) for known in EXPECTED_404)
    ]


def test_words_asks_for_nothing_the_payload_does_not_have(editor: Editor):
    assert unexpected(editor.report) == []


def test_no_editor_asks_for_anything_the_payload_does_not_have(
    blank_editor: Editor,
):
    assert unexpected(blank_editor.report) == []
