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

from libera.host.session import SESSIONS

STYLES = (
    '<w:style w:type="paragraph" w:customStyle="1" w:styleId="MyQuote">'
    '<w:name w:val="My Quote"/><w:basedOn w:val="Heading1"/><w:qFormat/>'
    "<w:rPr><w:i/></w:rPr></w:style>"
    '<w:style w:type="paragraph" w:styleId="Heading1">'
    '<w:name w:val="heading 1"/><w:qFormat/><w:rPr><w:b/></w:rPr></w:style>'
)
BODY = (
    '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title</w:t></w:r></w:p>'
    '<w:p><w:pPr><w:pStyle w:val="MyQuote"/></w:pPr><w:r><w:t>Quoted</w:t></w:r></w:p>'
)
REFERENCES = r'<w:(?:basedOn|next|link|pStyle|rStyle|tblStyle) w:val="([^"]+)"'


def test_a_documents_style_ids_are_kept(editor_with, tmp_path):
    document = with_body(tmp_path, BODY)
    with zipfile.ZipFile(document) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    parts["word/styles.xml"] = parts["word/styles.xml"].replace(
        b"</w:styles>", STYLES.encode() + b"</w:styles>"
    )
    with zipfile.ZipFile(document, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)

    saved = edited_and_saved(editor_with, document, DOCUMENT)

    assert re.findall(r'<w:pStyle w:val="([^"]+)"', saved) == ["Heading1", "MyQuote"]
    with zipfile.ZipFile(SESSIONS["0"].document) as z:
        styles = z.read("word/styles.xml").decode()
    ids = re.findall(r'w:styleId="([^"]+)"', styles)
    assert len({i.lower() for i in ids}) == len(ids), ids
    referenced = set(re.findall(REFERENCES, styles + saved))
    assert referenced <= set(ids), referenced - set(ids)
