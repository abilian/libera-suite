"""The editors: what differs between Words, Tables, Slides and Diagrams.

Almost nothing does. The bridge, the server, the session, the change log and
the save path are the same code for all four. Five things are not, and they
are all here:

    doctype       what web-apps' api.js maps to an editor directory
    opens         the extensions that land in this editor
    blank         which template File > New starts from
    formats       the fileType ids x2t will write, by the id the editor sends
    save_formats  what the Save As popup offers, in order

Every id in `formats` was **measured**, by converting a blank of that kind to
it and checking a file came out -- the same way the Words table was built. x2t
refuses a fair few that sit right beside the ones it accepts: every legacy
binary format (doc 66, xls 258, ppt 130), the flat-XML ones (xlsx-flat 267,
odp-flat 137, odt-flat 78), Apple's (numbers 269, key 141), and odg (140).
This is what it writes, not what OfficeFileFormats.h declares.

Diagrams is a viewer. x2t refuses every DRAW id -- 16385 and its siblings all
come back rc=88 -- and `document-templates` ships no blank for one, so there
is nothing to save and nothing to create. It opens .vsdx and shows it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib


def _exts(names: str) -> frozenset[str]:
    """A readable extension list. Fourteen of them one per line is not."""
    return frozenset(names.split())


@dataclass(frozen=True)
class App:
    """One editor, and the handful of facts that make it that editor."""

    name: str
    title: str
    # What the thing is called, as against what the editor is called: the
    # start window offers a Spreadsheet, not a Tables.
    noun: str
    doctype: str
    ext: str
    opens: frozenset[str]
    formats: dict[int, tuple[str, int]]
    save_formats: tuple[tuple[str, str], ...]
    blank: str | None = None

    @property
    def editable(self) -> bool:
        """A viewer has nothing to save, so it offers no formats to save as."""
        return bool(self.save_formats)

    @property
    def by_ext(self) -> dict[str, int]:
        """Extension to the format id that writes it."""
        return dict(self.formats.values())


WORDS = App(
    name="words",
    title="Libera Words",
    noun="Document",
    doctype="word",
    ext="docx",
    opens=_exts("docx doc odt rtf txt html htm epub fb2 dotx dot ott md mht xml"),
    blank="new.docx",
    formats={
        0: ("docx", 65),
        65: ("docx", 65),
        67: ("odt", 67),
        68: ("rtf", 68),
        69: ("txt", 69),
        70: ("html", 70),
        72: ("epub", 72),
        73: ("fb2", 73),
        76: ("dotx", 76),
        79: ("ott", 79),
        92: ("md", 92),
        513: ("pdf", 513),
    },
    save_formats=(
        ("Word Document (.docx)", "docx"),
        ("Word Template (.dotx)", "dotx"),
        ("OpenDocument Text (.odt)", "odt"),
        ("OpenDocument Template (.ott)", "ott"),
        ("PDF (.pdf)", "pdf"),
        ("Rich Text Format (.rtf)", "rtf"),
        ("HTML (.html)", "html"),
        ("Markdown (.md)", "md"),
        ("EPUB (.epub)", "epub"),
        ("FictionBook (.fb2)", "fb2"),
        ("Plain Text (.txt)", "txt"),
    ),
)

TABLES = App(
    name="tables",
    title="Libera Tables",
    noun="Spreadsheet",
    doctype="cell",
    ext="xlsx",
    opens=_exts("xlsx xls ods csv tsv xlsm xlt xltm xltx fods ots xlsb numbers"),
    blank="new.xlsx",
    formats={
        0: ("xlsx", 257),
        257: ("xlsx", 257),
        259: ("ods", 259),
        260: ("csv", 260),
        261: ("xlsm", 261),
        262: ("xltx", 262),
        263: ("xltm", 263),
        264: ("xlsb", 264),
        266: ("ots", 266),
        276: ("tsv", 276),
        513: ("pdf", 513),
    },
    save_formats=(
        ("Excel Workbook (.xlsx)", "xlsx"),
        ("Excel Template (.xltx)", "xltx"),
        ("Excel Binary Workbook (.xlsb)", "xlsb"),
        ("OpenDocument Spreadsheet (.ods)", "ods"),
        ("OpenDocument Template (.ots)", "ots"),
        ("PDF (.pdf)", "pdf"),
        ("Comma-Separated Values (.csv)", "csv"),
        ("Tab-Separated Values (.tsv)", "tsv"),
    ),
)

SLIDES = App(
    name="slides",
    title="Libera Slides",
    noun="Presentation",
    doctype="slide",
    ext="pptx",
    opens=_exts("pptx ppt pps ppsx odp pot potm potx ppsm pptm fodp otp key odg"),
    blank="new.pptx",
    formats={
        0: ("pptx", 129),
        129: ("pptx", 129),
        131: ("odp", 131),
        132: ("ppsx", 132),
        133: ("pptm", 133),
        135: ("potx", 135),
        136: ("potm", 136),
        138: ("otp", 138),
        513: ("pdf", 513),
    },
    save_formats=(
        ("PowerPoint Presentation (.pptx)", "pptx"),
        ("PowerPoint Template (.potx)", "potx"),
        ("PowerPoint Show (.ppsx)", "ppsx"),
        ("OpenDocument Presentation (.odp)", "odp"),
        ("OpenDocument Template (.otp)", "otp"),
        ("PDF (.pdf)", "pdf"),
    ),
)

DIAGRAMS = App(
    name="diags",
    title="Libera Diagrams",
    noun="Diagram",
    doctype="diagram",
    ext="vsdx",
    opens=frozenset(["vsdx", "vssx", "vstx", "vsdm", "vssm", "vstm"]),
    # No blank, no formats, no save: see the module docstring.
    formats={},
    save_formats=(),
)

ALL = (WORDS, TABLES, SLIDES, DIAGRAMS)
BY_NAME = {app.name: app for app in ALL}


def for_document(document: pathlib.Path) -> App:
    """Which editor opens this file.

    Words is the fallback rather than an error: it is the one that reads plain
    text, and an unknown extension is far more often a document than a
    spreadsheet.
    """
    ext = document.suffix.lstrip(".").lower()
    return next((app for app in ALL if ext in app.opens), WORDS)
