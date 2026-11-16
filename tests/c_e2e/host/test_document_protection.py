"""A document's editing protection, through an edit and a save.

The editor sends the document's protection back with every save, an empty
record when there is none, and x2t wrote that as `<w:documentProtection />`:
every document edited here came back with an element Word never writes. Seen
in ElixirOffice's 0.7.3, whose fix is the same guard in core.
"""

from __future__ import annotations

import re

from support.settings import blank, edited_and_saved

PROTECTION = re.compile(r"<w:documentProtection\b[^>]*>")
READ_ONLY = '<w:documentProtection w:edit="readOnly" w:enforcement="0"/>'


def test_a_document_without_protection_is_saved_without_one(editor_with, tmp_path):
    settings = edited_and_saved(editor_with, blank(tmp_path))

    assert PROTECTION.findall(settings) == []


def test_a_documents_protection_is_kept(editor_with, tmp_path):
    settings = edited_and_saved(editor_with, blank(tmp_path, READ_ONLY))

    (found,) = PROTECTION.findall(settings)
    assert 'w:edit="readOnly"' in found
