"""An SVG picture in a document, its strokes thinner than a pixel.

A drawing scaled down to fit its frame scales its lines with it, and a browser
draws a stroke a tenth of a pixel wide as a faint grey, or nothing: the faint
pictures of ElixirOffice's #61. The editor now draws such a stroke a pixel
wide (sdkjs 0021, after their 0.8.0), as core 0200 already did for the SVGs
x2t makes of WMF and EMF. It reads the SVG's text to do it, with an
XMLHttpRequest the bridge redirects as it does a picture's address.
"""

from __future__ import annotations

import time

from support.pictures import IMAGE, picture_docx
from support.render import dark_pixels

from libera import payload as payload_mod

# Ten lines across a picture 96 pixels wide, each 1/1000 of it thick.
LINES = "".join(
    f'<line x1="0" y1="{y}" x2="1000" y2="{y}" stroke="#000" stroke-width="1"/>'
    for y in range(50, 1000, 100)
)
SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"'
    f' viewBox="0 0 1000 1000">{LINES}</svg>'
)
BLIP = (
    '<a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships" r:embed="rIdSvg"/>'
)
# The page, below the ruler, in the window the tests open.
PAGE = (240, 170, 1040, 690)


def test_an_svgs_hairlines_are_drawn_a_pixel_wide(editor_with, tmp_path):
    document = tmp_path / "hairlines.docx"
    picture_docx(
        payload_mod.resolve().root,
        document,
        BLIP,
        f'<Relationship Id="rIdSvg" Type="{IMAGE}" Target="media/lines.svg"/>',
        {"word/media/lines.svg": SVG.encode()},
    )

    editor = editor_with([], document)

    deadline = time.monotonic() + 10
    while True:
        shot = tmp_path / f"{time.monotonic_ns()}.png"
        editor.page.screenshot(path=str(shot))
        dark = dark_pixels(str(shot), PAGE)
        # Ten lines 96 pixels long; the text cursor alone is about 30.
        if dark > 10 * 80 or time.monotonic() > deadline:
            break
        time.sleep(0.5)
    assert dark > 10 * 80
