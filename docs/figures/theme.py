"""The palette every figure on the site shares.

Brand colours, so a diagram sits beside a screenshot without arguing with it:
terracotta for Libera Suite, and the editors' own three where a figure needs to
tell them apart. Nothing here decides layout -- svg-plus measures and places.

The built-in Helvetica metrics are deliberate. These figures are read in a
browser at a few hundred pixels wide, where a percent of measurement error is
invisible, and needing a font file on disk would make the build machine part of
the answer.
"""

from __future__ import annotations

from svg_plus import Theme

SUITE = "#B5462B"  # Libera Suite
WORDS = "#6F6BAD"
TABLES = "#00877C"
SLIDES = "#A28137"
PAPER = "#F6F1E9"
INK = "#1E1A17"

FIGURE = Theme(
    size=11.0,
    ink=INK,
    muted="#6B6259",
    accent=SUITE,
    surface=PAPER,
    rule="#D9CFC0",
    page="#FFFFFF",
    radius=6.0,
    pad=13.0,
    gap=12.0,
)
