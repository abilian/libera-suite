"""A positional tab (`w:ptab`), through an edit and a save.

x2t wrote nothing into the editor's format for one, so a document edited here
lost every positional tab (core 0207 and sdkjs 0017, after ElixirOffice
0.7.3).
"""

from __future__ import annotations

import re

from support.blank import DOCUMENT, edited_and_saved, with_body

PTAB = '<w:ptab w:relativeTo="indent" w:alignment="right" w:leader="dot"/>'


def test_a_positional_tab_is_kept(editor_with, tmp_path):
    body = f"<w:p><w:r><w:t>Name</w:t>{PTAB}<w:t>Page</w:t></w:r></w:p>"

    saved = edited_and_saved(editor_with, with_body(tmp_path, body), DOCUMENT)

    (found,) = re.findall(r"<w:ptab\b[^>]*>", saved)
    for attribute in re.findall(r'w:\w+="\w+"', PTAB):
        assert attribute in found
