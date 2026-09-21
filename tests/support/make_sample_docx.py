#!/usr/bin/env python3
"""Build the POC's test .docx.

Starts from Euro-Office's own empty template (which carries styles.xml,
theme1.xml, fontTable.xml -- a hand-rolled minimal package does not, and the
font engine falls over resolving a default font) and drops some content into
it, so the POC never has to touch the user's own documents.

    make_sample_docx.py out.docx            text only
    make_sample_docx.py out.docx --image    text plus one embedded PNG

The --image variant is the regression check for document media: it is the only
thing that exercises the file:// image path the host has to redirect.
"""

from __future__ import annotations

import os
import pathlib
import re
import struct
import sys
import zipfile
import zlib


def find_template() -> pathlib.Path:
    """The blank this document is built on.

    LIBERA_BLANK when set -- build/smoke.sh points it at the pinned
    document-templates checkout, because it runs before there is a payload.
    Otherwise the installed payload's own blank, which is the one `libera
    words` starts from.

    Never core/Common/empty/*.bin: it carries a default underline and quarter
    leading, so everything built on it renders struck through and piled up.
    """
    env = os.environ.get("LIBERA_BLANK")
    if env:
        return pathlib.Path(env)
    # Imported here so that LIBERA_BLANK makes this script usable on its own,
    # without the package installed -- which is how the build runs it.
    from libera import payload

    return payload.resolve().root / "empty" / "new.docx"


PARAGRAPHS = [
    "Words — POC 0",
    (
        "If you can read this in the editor, the offline Euro-Office stack boots "
        "against a Python-served payload and a stubbed AscDesktopEditor bridge."
    ),
    "Second paragraph, to check line breaking and text layout.",
]

EMU_PER_PX = 9525
IMG_W, IMG_H = 120, 60
IMG_REL_ID = "rIdImg1"


def paragraph(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def solid_png(w: int, h: int, rgb: tuple[int, int, int]) -> bytes:
    """A minimal single-colour PNG, so the POC needs no image library."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def drawing() -> str:
    cx, cy = IMG_W * EMU_PER_PX, IMG_H * EMU_PER_PX
    return (
        '<w:p><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="p1"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="1" name="p1"/><pic:cNvPicPr/></pic:nvPicPr>'
        "<pic:blipFill><a:blip "
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        f'r:embed="{IMG_REL_ID}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )


def add_image(parts: dict[str, bytes]) -> str:
    """Add the image part, its relationship and content type; return body XML."""
    parts["word/media/image1.png"] = solid_png(IMG_W, IMG_H, (200, 60, 60))

    rels = parts["word/_rels/document.xml.rels"].decode()
    parts["word/_rels/document.xml.rels"] = rels.replace(
        "</Relationships>",
        f'<Relationship Id="{IMG_REL_ID}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/image" Target="media/image1.png"/>'
        "</Relationships>",
    ).encode()

    ct = parts["[Content_Types].xml"].decode()
    if 'Extension="png"' not in ct:
        ct = ct.replace(
            "</Types>", '<Default Extension="png" ContentType="image/png"/></Types>'
        )
    parts["[Content_Types].xml"] = ct.encode()

    return paragraph("Image below:") + drawing()


def main(out: str, *, with_image: bool = False) -> None:
    template = find_template()
    if not template.exists():
        sys.exit(f"missing template: {template}")

    with zipfile.ZipFile(template) as z:
        parts = {n: z.read(n) for n in z.namelist()}

    body = "".join(paragraph(t) for t in PARAGRAPHS)
    if with_image:
        body += add_image(parts)

    # Keep the template's <w:sectPr> (page size, margins); replace the rest of
    # the body with our content.
    doc, n = re.subn(
        r"(<w:body>).*?(<w:sectPr\b)",
        lambda m: m.group(1) + body + m.group(2),
        parts["word/document.xml"].decode(),
        flags=re.DOTALL,
    )
    if n != 1:
        sys.exit("template body/sectPr not found — template layout changed")
    parts["word/document.xml"] = doc.encode()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    print(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    positional = [a for a in args if not a.startswith("--")]
    main(positional[0] if positional else "sample.docx", with_image="--image" in args)
