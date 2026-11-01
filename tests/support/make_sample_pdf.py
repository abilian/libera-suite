"""A one-page PDF with a line of text, written by hand.

No PDF library to install, and no x2t: a PDF the converter wrote would test
the converter as much as the PDF editor. Helvetica is one of the fourteen fonts
every PDF reader carries, so nothing is embedded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"


def make_pdf(path: Path, text: str) -> None:
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    write_pdf(
        path,
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
                b" /Resources << /Font << /F1 5 0 R >> >> >>"
            ),
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            FONT,
        ],
    )


# What each page of make_nested_pdf inherits from its parent: MediaBox
# (width, height) and Rotate. Neither is on the page itself.
NESTED = ((200, 200, 0), (600, 400, 90), (300, 500, 180))


def make_nested_pdf(path: Path) -> None:
    """Three pages, each the only child of its own Pages node, from which it
    inherits its size and rotation; page N reads "Page N"."""
    count = len(NESTED)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (b" ".join(b"%d 0 R" % (4 + 3 * n) for n in range(count)), count),
        FONT,
    ]
    for n, (width, height, rotate) in enumerate(NESTED):
        node = 4 + 3 * n
        stream = f"BT /F1 24 Tf 20 20 Td (Page {n + 1}) Tj ET".encode()
        objects += [
            b"<< /Type /Pages /Parent 2 0 R /Kids [%d 0 R] /Count 1"
            b" /MediaBox [0 0 %d %d] /Rotate %d >>" % (node + 1, width, height, rotate),
            b"<< /Type /Page /Parent %d 0 R /Contents %d 0 R"
            b" /Resources << /Font << /F1 3 0 R >> >> >>" % (node, node + 2),
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        ]
    write_pdf(path, objects)


# The fields of make_form_pdf: (object number, name, rectangle).
FORM_FIELDS = ((6, "name", (150, 700, 400, 725)), (7, "city", (150, 660, 400, 685)))


def make_form_pdf(path: Path) -> None:
    """Two text fields, each named, under a parent field that holds an empty
    value, as Adobe's LiveCycle Designer writes its forms (Cerfas among
    them): what a field does not hold itself, it inherits from there."""
    stream = b"BT /F1 12 Tf 72 708 Td (Name) Tj 0 -40 Td (City) Tj ET"
    widgets = [
        b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (%s) /Parent 8 0 R /P 3 0 R"
        b" /Rect [%d %d %d %d] /DA (/F1 12 Tf 0 g) /F 4 >>" % (name.encode(), *rect)
        for _, name, rect in FORM_FIELDS
    ]
    write_pdf(
        path,
        [
            (
                b"<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [8 0 R]"
                b" /DA (/F1 12 Tf 0 g) /DR << /Font << /F1 5 0 R >> >> >> >>"
            ),
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
                b" /Resources << /Font << /F1 5 0 R >> >> /Annots [6 0 R 7 0 R] >>"
            ),
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            FONT,
            *widgets,
            b"<< /T (form) /V () /Kids [6 0 R 7 0 R] >>",
        ],
    )


def write_pdf(path: Path, objects: list[bytes]) -> None:
    """Object N is objects[N - 1]; the first is the catalogue."""
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    path.write_bytes(out)
