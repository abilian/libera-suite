"""The render check in tests/support/render.py.

It is the only thing in the suite that looks at what the editor drew, so it has
to actually discriminate: a page of properly spaced lines passes, and the two
shapes of the collapsed-leading regression fail.
"""

from __future__ import annotations

import struct
import zlib
from typing import TYPE_CHECKING

import pytest
from support import render as render_mod

if TYPE_CHECKING:
    from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\x0a"
WIDTH, HEIGHT = 60, 140
MARGIN = 5


def write_png(path: Path, bars: list[tuple[int, int]], *, alpha: bool = False) -> None:
    """A blank image with black bars, each given as (top, height).

    With alpha=True the background is *transparent black* rather than white,
    which is what a canvas captured by toDataURL looks like outside the page.
    """
    ink = b"\x00\x00\x00\xff" if alpha else b"\x00\x00\x00"
    blank = b"\x00\x00\x00\x00" if alpha else b"\xff\xff\xff"
    rows = []
    for y in range(HEIGHT):
        inked = any(top <= y < top + height for top, height in bars)
        rows.append(b"\x00" + (ink if inked else blank) * WIDTH)  # filter 0 (None)

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6 if alpha else 2, 0, 0, 0)
    path.write_bytes(
        PNG_MAGIC
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def render(monkeypatch):
    """The real module, with the page inset narrowed to fit these tiny PNGs."""
    monkeypatch.setattr(render_mod, "MARGIN", MARGIN)
    return render_mod


def test_evenly_spaced_lines_pass(render, tmp_path: Path) -> None:
    png = tmp_path / "good.png"
    write_png(png, [(20, 10), (50, 10), (80, 10)])
    assert render.check(str(png)) == []


def test_overlapping_lines_fail(render, tmp_path: Path) -> None:
    # Three bars 5px apart: the collapsed-leading shape.
    png = tmp_path / "overlap.png"
    write_png(png, [(20, 4), (25, 4), (30, 4)])
    problems = render.check(str(png))
    assert any("on top of each other" in p for p in problems)


def test_hairline_rule_fails(render, tmp_path: Path) -> None:
    # Well-spaced text, but with a 1px rule: an unwanted underline.
    png = tmp_path / "rule.png"
    write_png(png, [(20, 10), (50, 10), (80, 10), (95, 1)])
    problems = render.check(str(png))
    assert any("hairline" in p for p in problems)


def test_blank_page_fails(render, tmp_path: Path) -> None:
    png = tmp_path / "blank.png"
    write_png(png, [])
    problems = render.check(str(png))
    assert any("line(s) of text drawn" in p for p in problems)


def test_transparent_background_is_not_ink(render, tmp_path: Path) -> None:
    """A canvas capture is RGBA, and outside the page it is transparent black.

    Reading only the colour channels counts every one of those pixels as ink and
    paints the whole image as a single enormous line of text.
    """
    png = tmp_path / "rgba.png"
    write_png(png, [(20, 10), (50, 10), (80, 10)], alpha=True)
    assert render.check(str(png)) == []


def test_rejects_a_non_png(render, tmp_path: Path) -> None:
    bad = tmp_path / "not.png"
    bad.write_bytes(b"definitely not a png")
    with pytest.raises(render.UnsupportedPNGError):
        render.check(str(bad))
