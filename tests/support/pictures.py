"""A Word document holding one drawing, made from the payload's blank."""

from __future__ import annotations

import functools
import operator
import re
import struct
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera.host import apps
from support.make_sample_docx import solid_png

if TYPE_CHECKING:
    import pathlib

IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

MIME_TYPES = {"png": "image/png", "svg": "image/svg+xml", "wmf": "image/x-wmf"}


def picture_docx(
    payload: pathlib.Path, path: pathlib.Path, blip: str, rels: str, media: dict
) -> None:
    """The blank with one picture, drawn by `blip`, whose relationships are
    `rels`, and `media` added to the package."""
    graphic = (
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="901" name="p"/><pic:cNvPicPr/></pic:nvPicPr>'
        f"<pic:blipFill>{blip}<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/>'
        '</a:xfrm><a:prstGeom prst="rect"/></pic:spPr>'
        "</pic:pic></a:graphicData>"
    )
    types = "".join(
        f'<Default Extension="{ext}" ContentType="{mime}"/>'
        for ext, mime in MIME_TYPES.items()
    )
    drawing_docx(payload, path, Drawing(graphic, rels, media, types))


@dataclass(frozen=True)
class Drawing:
    """An inline drawing: its `a:graphic` content, its relationships, the
    parts it adds to the package and their content types, and its size in
    EMU."""

    graphic: str
    rels: str
    parts: dict[str, bytes]
    types: str
    size: tuple[int, int] = (914400, 914400)


def drawing_docx(payload: pathlib.Path, path: pathlib.Path, it: Drawing) -> None:
    """The blank with `it` in its first paragraph; each content type is added
    unless the blank already has it."""
    with zipfile.ZipFile(payload / "empty" / apps.WORDS.blank) as z:
        package = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    cx, cy = it.size
    drawing = (
        "<w:p><w:r><w:drawing><wp:inline>"
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="901" name="p"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f"{it.graphic}</a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )
    document, n = re.subn(
        r"(<w:body>)", lambda m: m[1] + drawing, package["word/document.xml"].decode()
    )
    assert n == 1
    package["word/document.xml"] = document.encode()
    relations = package["word/_rels/document.xml.rels"].decode()
    package["word/_rels/document.xml.rels"] = relations.replace(
        "</Relationships>", it.rels + "</Relationships>"
    ).encode()
    content_types = package["[Content_Types].xml"].decode()
    for entry in re.findall(r"<[^>]+/>", it.types):
        key = re.search(r'(?:Extension|PartName)="[^"]+"', entry)
        assert key is not None
        if key[0] not in content_types:
            content_types = content_types.replace("</Types>", entry + "</Types>")
    package["[Content_Types].xml"] = content_types.encode()
    package.update(it.parts)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in package.items():
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


PIC_BULLET_NUMBERING = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    ' xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
    '<w:numPicBullet w:numPicBulletId="0"><w:pict><v:shape id="_x0000_i1025"'
    ' type="#_x0000_t75" style="width:12pt;height:12pt" o:bullet="t">'
    '<v:imagedata r:id="rIdBullet" o:title=""/></v:shape></w:pict></w:numPicBullet>'
    '<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/>'
    '<w:numFmt w:val="bullet"/><w:lvlText w:val=""/><w:lvlPicBulletId w:val="0"/>'
    '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>'
    '<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr>'
    '</w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
    "</w:numbering>"
)
RELATIONSHIPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def write_pic_bullet_docx(payload: pathlib.Path, path: pathlib.Path) -> None:
    """Three list items whose bullet is a red square picture, as Word writes
    one: w:numPicBullet with a VML picture, w:lvlPicBulletId on the level."""
    blank = payload / "empty" / apps.WORDS.blank
    item = (
        '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
        "</w:pPr><w:r><w:t>Item</w:t></w:r></w:p>"
    )
    with zipfile.ZipFile(blank) as src, zipfile.ZipFile(path, "w") as dst:
        for entry in src.infolist():
            data = src.read(entry)
            if entry.filename == "word/document.xml":
                data = re.sub(
                    rb"<w:body>.*?(<w:sectPr)",
                    b"<w:body>" + (item * 3).encode() + rb"\1",
                    data,
                    flags=re.DOTALL,
                )
            elif entry.filename == "word/_rels/document.xml.rels":
                data = data.replace(
                    b"</Relationships>",
                    f'<Relationship Id="rIdNumbering" Type="{RELATIONSHIPS}/numbering"'
                    ' Target="numbering.xml"/></Relationships>'.encode(),
                )
            elif entry.filename == "[Content_Types].xml":
                data = data.replace(
                    b"</Types>",
                    b'<Default Extension="png" ContentType="image/png"/>'
                    b'<Override PartName="/word/numbering.xml" ContentType="application/'
                    b'vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
                    b"</Types>",
                )
            dst.writestr(entry, data)
        dst.writestr("word/numbering.xml", PIC_BULLET_NUMBERING)
        dst.writestr(
            "word/_rels/numbering.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships'
            ' xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rIdBullet" Type="{RELATIONSHIPS}/image"'
            ' Target="media/bullet.png"/></Relationships>',
        )
        dst.writestr("word/media/bullet.png", solid_png(16, 16, (220, 0, 0)))
