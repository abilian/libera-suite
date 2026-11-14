"""A Word document holding one picture, made from the payload's blank."""

from __future__ import annotations

import re
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
