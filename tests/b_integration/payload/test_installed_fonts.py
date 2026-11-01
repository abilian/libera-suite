"""The machine's fonts, indexed by the payload's allfontsgen and used by x2t.

Which fonts a machine has is the machine's business, so the font these use is
found, not named: the first of a few common families this machine has and the
payload does not.
"""

from __future__ import annotations

import re
import zipfile
from typing import TYPE_CHECKING

import pytest

from libera import payload as payload_mod
from libera.host import apps, opening, session as sessions
from libera.host.convert import export
from libera.host.session import Session
from libera.payload import fonts

if TYPE_CHECKING:
    import pathlib

# Installed with macOS, with Windows, or with most Linux desktops; none ships
# in the payload.
CANDIDATES = [
    "Hoefler Text",
    "Georgia",
    "Verdana",
    "DejaVu Sans",
    "Noto Sans",
    "Cantarell",
]


def read_families(all_fonts: pathlib.Path) -> set[str]:
    infos = all_fonts.read_text(encoding="utf-8").split('window["__fonts_infos"]')[1]
    return set(re.findall(r'\["([^"]+)", *-?\d', infos))


@pytest.fixture(scope="module")
def index(tmp_path_factory) -> pathlib.Path:
    """One index of this machine's fonts, for the module: 7 to 17 s."""
    made = tmp_path_factory.mktemp("fonts") / "index"
    fonts.build(payload_mod.resolve(), made)
    return made


@pytest.fixture(scope="module")
def machine_only(index) -> str:
    ours = read_families(payload_mod.resolve().all_fonts)
    theirs = read_families(index / "AllFonts.js")
    found = [f for f in CANDIDATES if f in theirs - ours]
    if not found:
        pytest.skip(f"none of {CANDIDATES} is installed here")
    return found[0]


def test_the_index_holds_the_payloads_fonts_and_the_machines(index):
    ours = read_families(payload_mod.resolve().all_fonts)
    theirs = read_families(index / "AllFonts.js")
    assert ours <= theirs
    assert len(theirs) > len(ours)
    listed = fonts.read_font_files(index / "AllFonts.js")
    assert all(f.is_file() for f in listed)
    assert not list(index.parent.glob(".building-*"))


def write_docx_in(family: str, path: pathlib.Path) -> None:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    package = "http://schemas.openxmlformats.org/package/2006"
    officedoc = "http://schemas.openxmlformats.org/officeDocument/2006"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            f'<Types xmlns="{package}/content-types">'
            '<Default Extension="rels" ContentType="application/'
            'vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            f'<Relationships xmlns="{package}/relationships">'
            f'<Relationship Id="rId1" Type="{officedoc}/relationships/'
            'officeDocument" Target="word/document.xml"/></Relationships>',
        )
        z.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{w}"><w:body><w:p><w:r><w:rPr>'
            f'<w:rFonts w:ascii="{family}" w:hAnsi="{family}"/></w:rPr>'
            f"<w:t>Set in {family}</w:t></w:r></w:p></w:body></w:document>",
        )


def read_pdf_fonts(
    index: pathlib.Path | None, family: str, tmp_path: pathlib.Path
) -> bytes:
    """A document set in `family`, opened and printed the way the host does."""
    document = tmp_path / "set.docx"
    write_docx_in(family, document)
    session = Session(
        payload=payload_mod.resolve().root,
        work=tmp_path / "session",
        document=document,
        fonts=index,
    )
    sessions.configure(session)
    opening.open_document(session, document)
    pdf = tmp_path / "set.pdf"
    export(session, pdf, apps.WORDS.ids_by_ext["pdf"], None)
    # x2t writes each font's name uncompressed: /BaseFont /BAAAAA+Hoefler#20Text
    return b" ".join(re.findall(rb"/BaseFont /\w{6}\+(\S+)", pdf.read_bytes()))


def test_a_machine_font_is_embedded_in_the_pdf(index, machine_only, tmp_path):
    embedded = read_pdf_fonts(index, machine_only, tmp_path)
    assert machine_only.replace(" ", "#20").encode() in embedded


def test_without_the_index_the_same_document_gets_a_substitute(machine_only, tmp_path):
    """The other half: what the test above sees is the index's doing."""
    embedded = read_pdf_fonts(None, machine_only, tmp_path)
    assert embedded
    assert machine_only.replace(" ", "#20").encode() not in embedded
