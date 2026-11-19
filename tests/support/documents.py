"""Documents the tests open, each built from the payload's own blank, and
shared by every tier that checks the same thing: x2t's PDF in the integration
tests, the editor in the end-to-end ones, the engine in Node (tests/engine/).

`SAMPLES` names the ones the engine's Node tests open, with the editor each is
for; the pytest bridge converts each to the editor's format and hands Node
the folder (tests/b_integration/payload/test_engine.py).
"""

from __future__ import annotations

import shutil
import zipfile
from typing import TYPE_CHECKING

from libera import payload as payload_mod
from libera.host import apps
from support import make_sample_docx
from support.blank import with_body

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable

# Three words, the second at the centre of the text area and the third at its
# right edge, by positional tabs (`w:ptab`, sdkjs 0017).
PTABS = (
    "<w:p><w:r><w:t>Left</w:t></w:r>"
    '<w:r><w:ptab w:relativeTo="margin" w:alignment="center" w:leader="none"/>'
    "<w:t>Mid</w:t></w:r>"
    '<w:r><w:ptab w:relativeTo="margin" w:alignment="right" w:leader="none"/>'
    "<w:t>End</w:t></w:r></w:p>"
)

# A SET field holding its last result, as Word writes one (sdkjs 0018).
SET_FIELD = (
    '<w:p><w:r><w:t xml:space="preserve">Before </w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> SET year "2001" </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    "<w:r><w:t>2001</w:t></w:r>"
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    "<w:r><w:t>after</w:t></w:r></w:p>"
)

# A built-in style and a custom one based on it, each with its id, and a
# paragraph in each (sdkjs 0022).
STYLES = (
    '<w:style w:type="paragraph" w:customStyle="1" w:styleId="MyQuote">'
    '<w:name w:val="My Quote"/><w:basedOn w:val="Heading1"/><w:qFormat/>'
    "<w:rPr><w:i/></w:rPr></w:style>"
    '<w:style w:type="paragraph" w:styleId="Heading1">'
    '<w:name w:val="heading 1"/><w:qFormat/><w:rPr><w:b/></w:rPr></w:style>'
)
STYLED_BODY = (
    '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title</w:t></w:r></w:p>'
    '<w:p><w:pPr><w:pStyle w:val="MyQuote"/></w:pPr><w:r><w:t>Quoted</w:t></w:r></w:p>'
)


def with_styles(document: pathlib.Path, styles: str) -> pathlib.Path:
    """`document` with `styles` added at the end of its styles part."""
    with zipfile.ZipFile(document) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    parts["word/styles.xml"] = parts["word/styles.xml"].replace(
        b"</w:styles>", styles.encode() + b"</w:styles>"
    )
    with zipfile.ZipFile(document, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return document


def blank_of(app: apps.App, path: pathlib.Path) -> pathlib.Path:
    shutil.copyfile(payload_mod.resolve().root / "empty" / app.blank, path)
    return path


def _sample_docx(folder: pathlib.Path) -> pathlib.Path:
    document = folder / "sample.docx"
    make_sample_docx.main(str(document))
    return document


# name: the editor it opens in, and how to build it in an empty folder.
SAMPLES: dict[str, tuple[apps.App, Callable[[pathlib.Path], pathlib.Path]]] = {
    "sample": (apps.WORDS, _sample_docx),
    "blank-table": (apps.TABLES, lambda f: blank_of(apps.TABLES, f / "blank.xlsx")),
    "blank-deck": (apps.SLIDES, lambda f: blank_of(apps.SLIDES, f / "blank.pptx")),
    "ptabs": (apps.WORDS, lambda f: with_body(f, PTABS)),
    "set-field": (apps.WORDS, lambda f: with_body(f, SET_FIELD)),
    "style-ids": (apps.WORDS, lambda f: with_styles(with_body(f, STYLED_BODY), STYLES)),
}
