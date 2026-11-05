"""A document someone else has open, opened in the editor.

The editor has a mode for it, which the host has to switch on before the
document is ready: it marks the document read-only and says so, then lets you
edit, and expects the host to send a plain Save to Save As, because the file
belongs to whoever holds the lock. Without it a document open in LibreOffice
opened here as if nobody else had it.
"""

from __future__ import annotations

LOCKED_TIP = "Document is locked for editing"
ADA = "Ada Lovelace, since 03.10.2026 20:20"


def editor_text(editor) -> str:
    return editor.frame.evaluate("() => document.body.innerText")


def test_a_locked_document_says_so(editor_with):
    editor = editor_with([], locked_by=ADA)

    editor.frame.wait_for_selector(f"text={LOCKED_TIP}", timeout=20_000)


def test_a_locked_document_says_so_behind_a_free_one(editor_with, second_window):
    """Each window is told about its own document, not the first window's: a
    document dropped on the start window opened as if nobody else had it."""
    second = second_window(editor_with([]), locked_by=ADA)

    second.frame.wait_for_selector(f"text={LOCKED_TIP}", timeout=20_000)


def test_a_free_document_does_not_behind_a_locked_one(editor_with, second_window):
    second = second_window(editor_with([], locked_by=ADA))
    second.wait_for_nothing()

    assert LOCKED_TIP not in editor_text(second)


def test_a_free_document_does_not(editor_with):
    editor = editor_with([])
    # The tip comes with the document: on a locked one it was already up when
    # the editor was ready, three runs of three (2026-10-11). Ready is the sync
    # point, so this only covers a tip a loaded machine shows a little late.
    editor.wait_for_nothing()

    assert LOCKED_TIP not in editor_text(editor)
