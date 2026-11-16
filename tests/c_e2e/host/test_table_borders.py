"""A Slides table set to "No Border", through a save and a reopen.

The table panel's "no border" sets each edge to border type nil (0), which the
writer did not take for "none": it wrote a black line half a point wide, and
the table came back ruled (sdkjs 0015, after ElixirOffice 0.9.0). Their fix
also reads an `a:noFill` edge as none; ours already did.
"""

from __future__ import annotations

import re
import shutil
import time
import zipfile
from typing import TYPE_CHECKING

from libera import payload as payload_mod
from libera.host import apps
from libera.host.saving import SaveRequest, save_document
from libera.host.session import SESSIONS

if TYPE_CHECKING:
    import pathlib

NO_BORDER = """() => {
  const api = Asc.editor;
  api.put_Table(2, 2);
  const borders = new Asc.CBorders();
  for (const side of ["Left", "Top", "Right", "Bottom", "InsideV", "InsideH"]) {
    const edge = new Asc.asc_CTextBorder();
    edge.put_Value(0);
    borders["put_" + side](edge);
  }
  const props = new Asc.CTableProp();
  props.put_CellBorders(borders);
  props.put_CellSelect(true);
  api.tblApply(props);
}"""

# Each cell's four edges as the editor holds them: the border type, -1 none.
EDGES = """() => {
  const slide = Asc.editor.WordControl.m_oLogicDocument.Slides[0];
  const frame = slide.cSld.spTree.find((o) => o.graphicObject);
  const table = frame.graphicObject;
  const found = [];
  for (const row of table.Content)
    for (const cell of row.Content) {
      const b = cell.Get_Borders();
      found.push(b.Left.Value, b.Top.Value, b.Right.Value, b.Bottom.Value);
    }
  return found;
}"""

EDGE = re.compile(r"<a:ln[LRTB]\b[^>]*>.*?</a:ln[LRTB]>")


def saved(session) -> str:
    log = session.change_log.path
    deadline = time.monotonic() + 30
    while not (log.exists() and log.stat().st_size) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert save_document(session, SaveRequest())["error"] == 0
    with zipfile.ZipFile(session.document) as deck:
        return deck.read("ppt/slides/slide1.xml").decode("utf-8")


def test_a_table_with_no_border_is_saved_and_reopened_without_one(
    editor_with, tmp_path: pathlib.Path
):
    deck = tmp_path / "deck.pptx"
    shutil.copyfile(payload_mod.resolve().root / "empty" / apps.SLIDES.blank, deck)
    editor = editor_with([], deck)
    editor.frame.evaluate(NO_BORDER)
    # The new table's first cell is the selection, as the panel would have it:
    # its edges are nil (0), the others the table style's single lines (1).
    before = editor.frame.evaluate(EDGES)
    assert 0 in before

    slide = saved(SESSIONS["0"])

    edges = EDGE.findall(slide)
    assert edges
    assert [e for e in edges if "<a:noFill/>" not in e] == []

    reopened = editor_with([], deck)
    # Each "no border" comes back as none (-1), and every other edge as it was.
    assert reopened.frame.evaluate(EDGES) == [-1 if e == 0 else e for e in before]
