"""A document's style ids, through an edit and a save.

The editor keys its styles by ids it makes up, and wrote those: a document
edited here came back with "670" for "Heading1", and every paragraph renamed
with it, where Word knows its built-in styles by their ids (sdkjs 0022, after
ElixirOffice 0.8.0). A style that has no id of the file's gets one made of
its name, as Word makes them.
"""

from __future__ import annotations

import re
import zipfile

from support.blank import DOCUMENT, edited_and_saved, with_body
from support.documents import STYLED_BODY, STYLES, with_styles

from libera.host.session import SESSIONS

REFERENCES = r'<w:(?:basedOn|next|link|pStyle|rStyle|tblStyle) w:val="([^"]+)"'


def test_a_documents_style_ids_are_kept(editor_with, tmp_path):
    document = with_styles(with_body(tmp_path, STYLED_BODY), STYLES)

    saved = edited_and_saved(editor_with, document, DOCUMENT)

    assert re.findall(r'<w:pStyle w:val="([^"]+)"', saved) == ["Heading1", "MyQuote"]
    with zipfile.ZipFile(SESSIONS["0"].document) as z:
        styles = z.read("word/styles.xml").decode()
    ids = re.findall(r'w:styleId="([^"]+)"', styles)
    assert len({i.lower() for i in ids}) == len(ids), ids
    referenced = set(re.findall(REFERENCES, styles + saved))
    assert referenced <= set(ids), referenced - set(ids)
