"""A WMF line drawing in a real window, as the editor draws it.

The editor draws a WMF or EMF from the SVG x2t writes of it when the document
opens, and that SVG scaled a pen one logical unit wide with the drawing: in a
CAD export, a fiftieth of a pixel, so the picture looked empty (ElixirOffice's
#61, core 0200). tests/b_integration checks the SVG; this checks the window.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from support import render
from support.pictures import thin_pen_wmf, wmf_docx

if TYPE_CHECKING:
    from pathlib import Path


def ink(picture: Path) -> int:
    return sum(render.ink_rows(str(picture)))


def test_a_thin_metafile_line_is_drawn_as_a_cosmetic_one(
    launch, payload_root, tmp_path
):
    """The same two lines, drawn with a pen one unit wide and with GDI's
    cosmetic pen, width 0, which was always one pixel: the window has as much
    ink for both. The first document's window posts the plain name."""
    thin, cosmetic = tmp_path / "thin.docx", tmp_path / "cosmetic.docx"
    wmf_docx(payload_root, thin, thin_pen_wmf(1))
    wmf_docx(payload_root, cosmetic, thin_pen_wmf(0))

    app = launch(thin, cosmetic)
    painted = app.windows_that_painted(2)

    other = next(p for p in painted if p != app.shot)
    assert ink(other) > 50, "the cosmetic lines drew nothing to compare with"
    assert ink(app.shot) >= ink(other) - 10
