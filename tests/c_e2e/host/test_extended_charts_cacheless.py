"""An extended chart whose data names no cells, through an edit and a save.

An Office 2016 chart's data may hold its values alone, with no formula naming
the cells they came from. A save builds each chart's workbook from those
values, and read every formula as a string: one with none crashed the editor's
writer, and x2t refused to save the document. Such a chart now keeps its
values and has no workbook, there being no cells to put them in (sdkjs 0023).
"""

from __future__ import annotations

import zipfile

from support.blank import DOCUMENT, edited_and_saved
from support.charts import sunburst_docx

from libera import payload as payload_mod
from libera.host.session import SESSIONS


def test_the_chart_is_saved(editor_with, tmp_path):
    document = tmp_path / "sunburst.docx"
    sunburst_docx(payload_mod.resolve().root, document, "Sales by region")

    edited_and_saved(editor_with, document, DOCUMENT)

    with zipfile.ZipFile(SESSIONS["0"].document) as saved:
        names = saved.namelist()
        charts = [
            saved.read(n).decode()
            for n in names
            if n.startswith("word/charts/") and n.endswith(".xml")
        ]
    assert any("<cx:chartSpace" in c and "Sales by region" in c for c in charts)
    assert not any(n.startswith("word/embeddings/") for n in names)
