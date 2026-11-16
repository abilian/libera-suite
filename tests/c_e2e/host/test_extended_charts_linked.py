"""An extended chart linked as a classic chart, through an edit and a save.

Apache POI writes an Office 2016 chart's part with the classic chart's
relationship and content type. x2t read it as a classic chart, found none,
and a save wrote an empty chart in its place (ElixirOffice's #76, core 0209).
"""

from __future__ import annotations

import zipfile

from support.blank import DOCUMENT, edited_and_saved
from support.charts import linked_as_chart_docx

from libera import payload as payload_mod
from libera.host.session import SESSIONS


def test_the_chart_is_kept(editor_with, tmp_path):
    document = tmp_path / "linked.docx"
    linked_as_chart_docx(payload_mod.resolve().root, document, "Sales by region")

    edited_and_saved(editor_with, document, DOCUMENT)

    with zipfile.ZipFile(SESSIONS["0"].document) as saved:
        charts = [
            saved.read(n).decode()
            for n in saved.namelist()
            if n.startswith("word/charts/") and n.endswith(".xml")
        ]
    assert any("<cx:chartSpace" in c and "Sales by region" in c for c in charts)
