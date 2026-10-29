"""A converted document cannot make x2t read a file or the network for it,
nor take it to gigabytes.

The converter's XML parser is libxml2 2.9.14, called with its default
options, which resolve no external entity; this holds it there. Measured on 2026-10-29,
notes/plans/converter-hardening.md (probe 1): neither a file nor a URL was
read, and the external DTD was not fetched.
"""

from __future__ import annotations

import hashlib
import http.server
import re
import shutil
import struct
import subprocess
import threading
import zipfile
import zlib

import pytest

from libera import cli
from libera.host import apps, convert

MARKER = "zqx-file-content-7731"


class Listener(http.server.BaseHTTPRequestHandler):
    asked: list[str]

    def do_GET(self):
        self.asked.append(self.path)
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_):
        pass


@pytest.fixture
def listener():
    """A web server on loopback that records every request made to it."""
    Listener.asked = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1], Listener.asked
    server.shutdown()


def test_external_entities_are_not_read(tmp_path, monkeypatch, live_payload, listener):
    port, asked = listener
    secret = tmp_path / "secret.txt"
    secret.write_text(MARKER)
    with zipfile.ZipFile(live_payload / "empty" / apps.WORDS.blank) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    declarations = (
        f'<!DOCTYPE w:document [<!ENTITY f SYSTEM "{secret.as_uri()}">'
        f'<!ENTITY h SYSTEM "http://127.0.0.1:{port}/entity">'
        f'<!ENTITY % p SYSTEM "http://127.0.0.1:{port}/dtd"> %p;]>'
    )
    body = "<w:p><w:r><w:t>file:&f; http:&h; end</w:t></w:r></w:p>"
    document = parts["word/document.xml"].decode()
    document = re.sub(r"(<\?xml[^>]*\?>)", lambda m: m[1] + declarations, document)
    document, n = re.subn(
        r"(<w:body>).*?(<w:sectPr\b)",
        lambda m: m[1] + body + m[2],
        document,
        flags=re.DOTALL,
    )
    assert n == 1
    assert "<!DOCTYPE" in document
    parts["word/document.xml"] = document.encode()
    with zipfile.ZipFile(tmp_path / "entities.docx", "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--convert", "entities.docx", "-t", "txt"]) == 0

    text = (tmp_path / "entities.txt").read_text(encoding="utf-8-sig")
    # The text around the entities came through, so the paragraph was read.
    assert "file:" in text
    assert "end" in text
    assert MARKER not in text
    assert asked == []


def test_nested_parameter_entities_cost_nothing(
    tmp_path, monkeypatch, live_payload, capsys
):
    """CVE-2021-3541: each parameter entity names the one before it twice,
    so the last is 2^40 references. libxml2 before 2.9.11 expands them, and
    took x2t to 3.9 GB on 6 KB (notes/plans/converter-hardening.md); 2.9.14
    stops early. The host's cap is lowered so that an x2t that still expands
    them is stopped, and says so, in a second or two."""
    monkeypatch.setattr(convert, "X2T_MEMORY", 500 << 20)
    with zipfile.ZipFile(live_payload / "empty" / apps.WORDS.blank) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    subset = '<!ENTITY % pe_1 "<!---->">' + "".join(
        f'<!ENTITY % pe_{i} "&#37;pe_{i - 1};<!---->&#37;pe_{i - 1};">'
        for i in range(2, 41)
    )
    document = parts["word/document.xml"].decode()
    document = re.sub(
        r"(<\?xml[^>]*\?>)",
        lambda m: m[1] + f"<!DOCTYPE w:document [{subset}%pe_40;]>",
        document,
    )
    assert "%pe_40;" in document
    parts["word/document.xml"] = document.encode()
    with zipfile.ZipFile(tmp_path / "laughs.docx", "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    monkeypatch.chdir(tmp_path)

    # Converted, or refused as malformed: either is the parser's call. Held
    # past the cap is the expansion running.
    cli.main(["--convert", "laughs.docx", "-t", "txt"])

    assert "held" not in capsys.readouterr().err


def test_a_part_larger_than_its_package_says_is_read_no_further(
    tmp_path, monkeypatch, live_payload, capsys
):
    """The host refuses a package by the sizes it declares (check_package),
    so one that understates them gets to x2t. x2t's unzip reads a part no
    further than its declared size: word/document.xml with 768 MB of spaces
    after it, declared at 1 MB, converts in a second in x2t's usual 220 MB
    (notes/plans/converter-hardening.md). Declared honestly, the same part
    took 465 MB at 384 MB, so the lowered cap stops an x2t that reads it all."""
    monkeypatch.setattr(convert, "X2T_MEMORY", 500 << 20)
    name = "word/document.xml"
    with zipfile.ZipFile(live_payload / "empty" / apps.WORDS.blank) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    document, n = re.subn(
        r"(<w:body>).*?(<w:sectPr\b)",
        lambda m: m[1] + "<w:p><w:r><w:t>kept</w:t></w:r></w:p>" + m[2],
        parts.pop(name).decode(),
        flags=re.DOTALL,
    )
    assert n == 1
    package = tmp_path / "understated.docx"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        for part, data in parts.items():
            z.writestr(part, data)
        with z.open(name, "w") as member:
            member.write(document.encode())
            for _ in range(12):
                member.write(b" " * (64 << 20))
    said = 1 << 20
    data = bytearray(package.read_bytes())
    # The size in the part's local header, then in the central directory.
    for signature, field, header in ((b"PK\x03\x04", 22, 30), (b"PK\x01\x02", 24, 46)):
        at = data.find(signature)
        while data[at + header : at + header + len(name)] != name.encode():
            at = data.find(signature, at + 4)
        struct.pack_into("<I", data, at + field, said)
    package.write_bytes(data)
    assert zipfile.ZipFile(package).getinfo(name).file_size == said
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--convert", package.name, "-t", "txt"]) == 0

    assert "held" not in capsys.readouterr().err
    assert "kept" in (tmp_path / "understated.txt").read_text(encoding="utf-8-sig")


IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
SVG_BLIP = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"


def png(size: int = 64, rgb: bytes = b"\0\0\xff") -> bytes:
    """A PNG of `size` x `size` pixels of one colour, blue by default: the
    picture on the user's disk."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\0" + rgb * size for _ in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def picture_docx(live_payload, path, blip: str, rels: str, media: dict) -> None:
    """The blank with one picture, drawn by `blip`, whose relationships are
    `rels`, and `media` added to the package."""
    with zipfile.ZipFile(live_payload / "empty" / apps.WORDS.blank) as z:
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
    for ext, mime in (("png", "image/png"), ("svg", "image/svg+xml")):
        if f'Extension="{ext}"' not in types:
            types = types.replace(
                "</Types>", f'<Default Extension="{ext}" ContentType="{mime}"/></Types>'
            )
    parts["[Content_Types].xml"] = types.encode()
    parts.update(media)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)


def blue_in_pdf(pdf) -> int:
    """How many pixels of the PDF's first page, drawn at 50 dpi, are blue. The pictures here are 1 inch square, about 2,500 of them; the
    page has none otherwise. A drawn picture is not always a picture in the
    PDF: x2t paints an SVG's into the page, so this looks at the page."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        pytest.skip("no pdftoppm to draw the PDF's page")
    page = subprocess.run(
        [pdftoppm, "-r", "50", "-f", "1", "-l", "1", str(pdf)],
        capture_output=True,
        check=True,
    ).stdout
    # P6, width, height, maximum value, then the pixels, three bytes each.
    _, width, height, _ = page.split(maxsplit=4)[:4]
    pixels = page[-int(width) * int(height) * 3 :]
    # Near blue, not exactly: drawn, 0 0 255 comes out 0 0 253.
    return sum(
        1
        for i in range(0, len(pixels), 3)
        if pixels[i] < 32 and pixels[i + 1] < 32 and pixels[i + 2] > 223
    )


def test_a_picture_linked_to_a_local_file_is_not_read(
    tmp_path, monkeypatch, live_payload
):
    """A picture whose relationship is external and names a path on the
    user's disk was copied into the .docx and .odt written from the
    document, byte for byte, and drawn into a PDF: opening it and sending it
    back sent the picture along. Core 0175 reads an external picture from a
    web address only (notes/plans/converter-hardening.md)."""
    secret = tmp_path / "private" / "photo.png"
    secret.parent.mkdir()
    secret.write_bytes(png())
    picture_docx(
        live_payload,
        tmp_path / "linked.docx",
        '<a:blip r:link="rIdLinked"/>',
        f'<Relationship Id="rIdLinked" Type="{IMAGE}" Target="{secret}"'
        ' TargetMode="External"/>',
        {},
    )
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--convert", "linked.docx", "-o", "out.docx"]) == 0
    assert cli.main(["--convert", "linked.docx", "-t", "pdf"]) == 0

    digest = hashlib.sha256(secret.read_bytes()).digest()
    with zipfile.ZipFile(tmp_path / "out.docx") as z:
        assert all(hashlib.sha256(z.read(n)).digest() != digest for n in z.namelist())
    assert blue_in_pdf(tmp_path / "linked.pdf") == 0


def test_an_svg_draws_no_file_it_names(tmp_path, monkeypatch, live_payload):
    """An SVG's <image> was read as a file relative to x2t's folder, ../
    included, and drawn into a PDF. Core 0174 draws only a picture the SVG
    carries. The fallback beside it, as Word stores one, is red."""
    secret = tmp_path / "photo.png"
    secret.write_bytes(png())
    up = "../" * 30 + str(secret).lstrip("/")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="100">'
        f'<image href="{up}" xlink:href="{up}" width="100" height="100"/></svg>'
    )
    picture_docx(
        live_payload,
        tmp_path / "svg.docx",
        '<a:blip r:embed="rIdPng"><a:extLst><a:ext uri="' + SVG_BLIP + '">'
        '<asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/'
        'SVG/main" r:embed="rIdSvg"/></a:ext></a:extLst></a:blip>',
        f'<Relationship Id="rIdPng" Type="{IMAGE}" Target="media/fallback.png"/>'
        f'<Relationship Id="rIdSvg" Type="{IMAGE}" Target="media/picture.svg"/>',
        {
            "word/media/fallback.png": png(1, b"\xff\0\0"),
            "word/media/picture.svg": svg.encode(),
        },
    )
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--convert", "svg.docx", "-t", "pdf"]) == 0

    assert blue_in_pdf(tmp_path / "svg.pdf") == 0
