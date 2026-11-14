"""A Word document holding one picture, made from the payload's blank."""

from __future__ import annotations

import functools
import operator
import re
import struct
import zipfile
from typing import TYPE_CHECKING

from libera.host import apps

if TYPE_CHECKING:
    import pathlib

IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

MIME_TYPES = {"png": "image/png", "svg": "image/svg+xml", "wmf": "image/x-wmf"}


def picture_docx(
    payload: pathlib.Path, path: pathlib.Path, blip: str, rels: str, media: dict
) -> None:
    """The blank with one picture, drawn by `blip`, whose relationships are
    `rels`, and `media` added to the package."""
    with zipfile.ZipFile(payload / "empty" / apps.WORDS.blank) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    drawing = (
        "<w:p><w:r><w:drawing><wp:inline>"
        '<wp:extent cx="914400" cy="914400"/><wp:docPr id="901" name="p"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="901" name="p"/><pic:cNvPicPr/></pic:nvPicPr>'
        f"<pic:blipFill>{blip}<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/>'
        '</a:xfrm><a:prstGeom prst="rect"/></pic:spPr>'
        "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )
    document, n = re.subn(
        r"(<w:body>)", lambda m: m[1] + drawing, parts["word/document.xml"].decode()
    )
    assert n == 1
    parts["word/document.xml"] = document.encode()
    relations = parts["word/_rels/document.xml.rels"].decode()
    parts["word/_rels/document.xml.rels"] = relations.replace(
        "</Relationships>", rels + "</Relationships>"
    ).encode()
    types = parts["[Content_Types].xml"].decode()
    for ext, mime in MIME_TYPES.items():
        if f'Extension="{ext}"' not in types:
            types = types.replace(
                "</Types>", f'<Default Extension="{ext}" ContentType="{mime}"/></Types>'
            )
    parts["[Content_Types].xml"] = types.encode()
    parts.update(media)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)


def thin_pen_wmf(pen_width: int = 1) -> bytes:
    """A metafile drawn the way CAD exports are: a logical window 32,000 units
    wide, and a pen `pen_width` units wide, a fiftieth of a pixel once the
    window is scaled to the picture for a width of 1. Two lines. A width of 0
    is GDI's cosmetic pen, one pixel at any scale."""

    def record(function: int, *words: int) -> bytes:
        return struct.pack("<IH", 3 + len(words), function) + struct.pack(
            f"<{len(words)}h", *words
        )

    body = b"".join([
        record(0x0103, 8),  # SETMAPMODE, MM_ANISOTROPIC
        record(0x020B, 0, 0),  # SETWINDOWORG
        record(0x020C, 14000, 32000),  # SETWINDOWEXT, y then x
        record(0x02FA, 0, pen_width, 0, 0, 0),  # CREATEPENINDIRECT: solid, black
        record(0x012D, 0),  # SELECTOBJECT
        record(0x0214, 2000, 2000),  # MOVETO
        record(0x0213, 2000, 30000),  # LINETO
        record(0x0214, 2000, 16000),
        record(0x0213, 12000, 16000),
        record(0x0000),  # EOF
    ])
    header = struct.pack("<HHHIHIH", 1, 9, 0x0300, (len(body) + 18) // 2, 1, 8, 0)
    # The placeable header: key, handle, bounds, units per inch, reserved, and
    # the XOR of its ten words before this one.
    placeable = struct.pack("<IHhhhhHI", 0x9AC6CDD7, 0, 0, 0, 32000, 14000, 4000, 0)
    checksum = functools.reduce(
        operator.xor, (w for (w,) in struct.iter_unpack("<H", placeable))
    )
    return placeable + struct.pack("<H", checksum) + header + body


def wmf_docx(payload: pathlib.Path, path: pathlib.Path, wmf: bytes) -> None:
    """The blank with one picture, the metafile `wmf`."""
    picture_docx(
        payload,
        path,
        '<a:blip r:embed="rIdWmf"/>',
        f'<Relationship Id="rIdWmf" Type="{IMAGE}" Target="media/drawing.wmf"/>',
        {"word/media/drawing.wmf": wmf},
    )
