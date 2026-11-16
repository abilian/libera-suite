"""Office 2016's extended charts (`cx:chartSpace`), in the form Word writes.

A sunburst, its data inline, linked by a `chartEx` relationship with the
`chartex+xml` content type: Word's own form, which Libera draws. The form
ElixirOffice's #76 filed, a plain chart relationship, is another matter.
"""

from __future__ import annotations

import re
import zipfile
from typing import TYPE_CHECKING

from libera.host import apps
from support.make_sample_docx import solid_png
from support.pictures import Drawing, drawing_docx

if TYPE_CHECKING:
    import pathlib

CHARTEX = "http://schemas.microsoft.com/office/drawing/2014/chartex"
CHARTEX_REL = "http://schemas.microsoft.com/office/2014/relationships/chartEx"
CHARTEX_TYPE = "application/vnd.ms-office.chartex+xml"

LEAVES = (
    ("North", "Coast", 22),
    ("North", "Hills", 12),
    ("South", "Coast", 18),
    ("South", "Plain", 30),
)


def sunburst(title: str, sheet: str | None = None) -> str:
    """A sunburst of LEAVES under `title`, whose run properties are empty, as
    Word leaves them when the chart's style decides. With `sheet`, its data is
    read from that sheet's columns A to C, rows 2 on, as Excel writes it."""
    count = len(LEAVES)
    last = count + 1

    def formula(ref: str) -> str:
        return f"<cx:f>{sheet}!{ref}</cx:f>" if sheet else ""

    def level(values) -> str:
        points = "".join(f'<cx:pt idx="{i}">{v}</cx:pt>' for i, v in enumerate(values))
        return f'<cx:lvl ptCount="{count}">{points}</cx:lvl>'

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cx:chartSpace xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        f' xmlns:cx="{CHARTEX}">'
        '<cx:chartData><cx:data id="0"><cx:strDim type="cat">'
        + formula(f"$A$2:$B${last}")
        + level(leaf for _, leaf, _ in LEAVES)
        + level(branch for branch, _, _ in LEAVES)
        + '</cx:strDim><cx:numDim type="size">'
        + formula(f"$C$2:$C${last}")
        + level(size for _, _, size in LEAVES).replace(
            "<cx:lvl ", '<cx:lvl formatCode="General" '
        )
        + "</cx:numDim></cx:data></cx:chartData>"
        '<cx:chart><cx:title pos="t" align="ctr" overlay="0"><cx:tx><cx:rich>'
        '<a:bodyPr/><a:lstStyle/><a:p><a:pPr algn="ctr"><a:defRPr/></a:pPr>'
        f'<a:r><a:rPr lang="en-US"/><a:t>{title}</a:t></a:r></a:p>'
        "</cx:rich></cx:tx></cx:title>"
        '<cx:plotArea><cx:plotAreaRegion><cx:series layoutId="sunburst">'
        '<cx:dataId val="0"/></cx:series></cx:plotAreaRegion></cx:plotArea>'
        "</cx:chart></cx:chartSpace>"
    )


def sunburst_docx(payload: pathlib.Path, path: pathlib.Path, title: str) -> None:
    """The blank, holding one sunburst chart titled `title`."""
    part = "word/charts/chartEx1.xml"
    drawing_docx(
        payload,
        path,
        Drawing(
            graphic=(
                f'<a:graphicData uri="{CHARTEX}"><cx:chart xmlns:cx="{CHARTEX}"'
                ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
                ' r:id="rIdChartEx"/></a:graphicData>'
            ),
            rels=(
                f'<Relationship Id="rIdChartEx" Type="{CHARTEX_REL}"'
                ' Target="charts/chartEx1.xml"/>'
            ),
            parts={part: sunburst(title).encode()},
            types=f'<Override PartName="/{part}" ContentType="{CHARTEX_TYPE}"/>',
            size=(5486400, 3200400),
        ),
    )


SHEET_NS = (
    'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SHEET_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml"


def sheet_xml(rows: list[list[str | int]], drawing: bool = False) -> str:
    def cell(ref: str, value: str | int) -> str:
        if isinstance(value, int):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'

    data = "".join(
        f'<row r="{r}">'
        + "".join(cell(f"{'ABC'[c]}{r}", v) for c, v in enumerate(row))
        + "</row>"
        for r, row in enumerate(rows, start=1)
    )
    return (
        f"<worksheet {SHEET_NS}><sheetData>{data}</sheetData>"
        + ('<drawing r:id="rIdDrawing"/>' if drawing else "")
        + "</worksheet>"
    )


def anchored_sunburst() -> str:
    """The drawing part: a sunburst in an mc:AlternateContent, with the
    shape Excel puts in its fallback for an Excel that cannot draw one."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<xdr:twoCellAnchor><xdr:from><xdr:col>1</xdr:col><xdr:colOff>0</xdr:colOff>"
        "<xdr:row>1</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>"
        "<xdr:to><xdr:col>8</xdr:col><xdr:colOff>0</xdr:colOff>"
        "<xdr:row>16</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>"
        '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
        '<mc:Choice xmlns:cx1="http://schemas.microsoft.com/office/drawing/2015/9/8/chartex"'
        ' Requires="cx1">'
        '<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="Chart 1"/>'
        "<xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>"
        '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>'
        f'<a:graphic><a:graphicData uri="{CHARTEX}"><cx:chart xmlns:cx="{CHARTEX}"'
        f' xmlns:r="{OFFICE_REL}" r:id="rIdChartEx"/></a:graphicData></a:graphic>'
        "</xdr:graphicFrame></mc:Choice><mc:Fallback>"
        '<xdr:sp macro="" textlink=""><xdr:nvSpPr><xdr:cNvPr id="2" name="Chart 1"/>'
        '<xdr:cNvSpPr><a:spLocks noTextEdit="1"/></xdr:cNvSpPr></xdr:nvSpPr>'
        '<xdr:spPr><a:xfrm><a:off x="609600" y="190500"/><a:ext cx="4267200" cy="2857500"/>'
        '</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
        "<xdr:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>"
        "This chart isn't available in your version of Excel.</a:t></a:r></a:p>"
        "</xdr:txBody></xdr:sp></mc:Fallback></mc:AlternateContent>"
        "<xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>"
    )


def sunburst_xlsx(path: pathlib.Path, sheets: tuple[str, ...]) -> None:
    """A workbook of `sheets`: the first holds a sunburst in Excel's own form,
    which reads its data from the second; the others hold their own name in
    A1, so a test can see each one survive."""
    chart, data, *rest = sheets
    rows: list[list[str | int]] = [["Branch", "Leaf", "Size"]]
    rows += [[branch, leaf, size] for branch, leaf, size in LEAVES]
    worksheets = [sheet_xml([[chart]], drawing=True), sheet_xml(rows)]
    worksheets += [sheet_xml([[name]]) for name in rest]
    parts = {
        "_rels/.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{OFFICE_REL}/officeDocument"'
            ' Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f"<workbook {SHEET_NS}><sheets>"
            + "".join(
                f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
                for i, name in enumerate(sheets, start=1)
            )
            + "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i}" Type="{OFFICE_REL}/worksheet"'
                f' Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Relationships>"
        ),
        "xl/worksheets/_rels/sheet1.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rIdDrawing" Type="{OFFICE_REL}/drawing"'
            ' Target="../drawings/drawing1.xml"/></Relationships>'
        ),
        "xl/drawings/drawing1.xml": anchored_sunburst(),
        "xl/drawings/_rels/drawing1.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rIdChartEx" Type="{CHARTEX_REL}"'
            ' Target="../charts/chartEx1.xml"/></Relationships>'
        ),
        "xl/charts/chartEx1.xml": sunburst("Sales by region", sheet=data),
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels"'
            ' ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml"'
            f' ContentType="{SHEET_TYPE}.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml"'
                f' ContentType="{SHEET_TYPE}.worksheet+xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + '<Override PartName="/xl/drawings/drawing1.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
            f'<Override PartName="/xl/charts/chartEx1.xml" ContentType="{CHARTEX_TYPE}"/>'
            "</Types>"
        ),
    }
    for i, sheet in enumerate(worksheets, start=1):
        parts[f"xl/worksheets/sheet{i}.xml"] = sheet
    with zipfile.ZipFile(path, "w") as z:
        for name, text in parts.items():
            z.writestr(name, text)


CHART_REL = f"{OFFICE_REL}/chart"
CHART_TYPE = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def linked_as_chart_docx(payload: pathlib.Path, path: pathlib.Path, title: str) -> None:
    """The blank holding a sunburst in the form of ElixirOffice's #76 (Apache
    POI writes it): the extended chart's part linked by the classic chart
    relationship and content type, its reference a `c:chart`, in an
    mc:AlternateContent whose fallback is a red picture."""
    with zipfile.ZipFile(payload / "empty" / apps.WORDS.blank) as z:
        package = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    extent = '<wp:extent cx="5486400" cy="3200400"/><wp:docPr id="901" name="Chart"/>'
    choice = (
        f"<w:drawing><wp:inline>{extent}"
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="{CHARTEX}">'
        '<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"'
        f' xmlns:r="{OFFICE_REL}" r:id="rIdChart"/>'
        "</a:graphicData></a:graphic></wp:inline></w:drawing>"
    )
    fallback = (
        f"<w:drawing><wp:inline>{extent}"
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="902" name="Fallback"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip xmlns:r="{OFFICE_REL}" r:embed="rIdFallback"/>'
        "<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5486400" cy="3200400"/>'
        '</a:xfrm><a:prstGeom prst="rect"/></pic:spPr></pic:pic>'
        "</a:graphicData></a:graphic></wp:inline></w:drawing>"
    )
    paragraph = (
        f'<w:p><w:r><mc:AlternateContent xmlns:mc="{MC}" xmlns:cx="{CHARTEX}">'
        f'<mc:Choice Requires="cx">{choice}</mc:Choice>'
        f"<mc:Fallback>{fallback}</mc:Fallback></mc:AlternateContent></w:r></w:p>"
    )
    document, n = re.subn(
        r"(<w:body>)", lambda m: m[1] + paragraph, package["word/document.xml"].decode()
    )
    assert n == 1
    package["word/document.xml"] = document.encode()
    package["word/_rels/document.xml.rels"] = (
        package["word/_rels/document.xml.rels"]
        .decode()
        .replace(
            "</Relationships>",
            f'<Relationship Id="rIdChart" Type="{CHART_REL}" Target="charts/chart1.xml"/>'
            f'<Relationship Id="rIdFallback" Type="{OFFICE_REL}/image"'
            ' Target="media/fallback.png"/></Relationships>',
        )
        .encode()
    )
    types = package["[Content_Types].xml"].decode()
    types = types.replace(
        "</Types>",
        f'<Override PartName="/word/charts/chart1.xml" ContentType="{CHART_TYPE}"/></Types>',
    )
    if 'Extension="png"' not in types:
        types = types.replace(
            "</Types>", '<Default Extension="png" ContentType="image/png"/></Types>'
        )
    package["[Content_Types].xml"] = types.encode()
    # Its data read from cells, as every chart Word or POI writes: the editor
    # cannot save an extended chart whose data names no cells.
    package["word/charts/chart1.xml"] = sunburst(title, sheet="Sheet1").encode()
    package["word/media/fallback.png"] = solid_png(40, 24, (220, 0, 0))
    with zipfile.ZipFile(path, "w") as z:
        for name, data in package.items():
            z.writestr(name, data)
