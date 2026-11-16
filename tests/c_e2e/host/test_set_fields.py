"""A SET field, through an edit and a save.

The editor did not know SET: a simple one (`w:fldSimple`) was read as its
result alone, so a save wrote the text and lost the field (sdkjs 0018, after
ElixirOffice 0.7.3).
"""

from __future__ import annotations

from support.blank import DOCUMENT, edited_and_saved, with_body

FIELDS = (
    '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> SET first "2001" </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>2001</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    '<w:p><w:fldSimple w:instr=" SET second &quot;2002&quot; ">'
    "<w:r><w:t>2002</w:t></w:r></w:fldSimple></w:p>"
)


def test_set_fields_are_kept(editor_with, tmp_path):
    saved = edited_and_saved(editor_with, with_body(tmp_path, FIELDS), DOCUMENT)

    assert "SET first" in saved
    assert "SET second" in saved
