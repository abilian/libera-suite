"""A workbook with an Office 2016 chart, in the editor and through a save.

x2t writes a sheet's drawing as one record holding the chart and, after it,
the picture or shape Excel keeps for a version that cannot draw it. The
editor read the chart and, when it could draw it, left the rest of that record
unread, so every record after it was read from the wrong place: a workbook
whose sunburst reads its data from another sheet opened with its first sheet
alone, and a save wrote that (sdkjs 0014, after ElixirOffice 0.9.1).
"""

from __future__ import annotations

import re
import time
import zipfile

from support.charts import sunburst_xlsx

from libera.host.saving import SaveRequest, save_document
from libera.host.session import SESSIONS

SHEETS = ("Chart", "Data", "Notes", "Totals")

NAMES = """() => {
  const book = Asc.editor.wbModel;
  const names = [];
  for (let i = 0; i < book.getWorksheetCount(); i++)
    names.push(book.getWorksheet(i).getName());
  return names;
}"""

CHARTS = "() => Asc.editor.wbModel.getWorksheet(0).Drawings.length"


def test_every_sheet_after_an_extended_chart_opens_and_is_saved(editor_with, tmp_path):
    book = tmp_path / "sunburst.xlsx"
    sunburst_xlsx(book, SHEETS)
    editor = editor_with([], book)

    assert editor.frame.evaluate(NAMES) == list(SHEETS)
    assert editor.frame.evaluate(CHARTS) == 1

    # An edit, so that the save converts: one with none copies the file. A1 is
    # selected, and the chart lies over the cells a click would reach.
    editor.frame.evaluate("() => Asc.editor.asc_setCellBold(true)")
    session = SESSIONS["0"]
    log = session.change_log.path
    deadline = time.monotonic() + 30
    while not (log.exists() and log.stat().st_size) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert save_document(session, SaveRequest())["error"] == 0
    with zipfile.ZipFile(session.document) as saved:
        workbook = saved.read("xl/workbook.xml").decode("utf-8")
    assert re.findall(r'<sheet [^>]*name="([^"]+)"', workbook) == list(SHEETS)
