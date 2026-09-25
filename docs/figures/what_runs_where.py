#!/usr/bin/env python3
"""One window, one loopback server, one converter: what each piece is."""

from __future__ import annotations

from pathlib import Path

from svg_plus import Doc, Frame, Row, Stack, Text, tint
from theme import FIGURE, SUITE


def node(label: str, detail: str, *, key: str, fill: str = "page") -> Frame:
    return Frame(
        Stack(
            Text(label, size=11.0, weight=700, align="center", wrap=False),
            *[
                Text(part, size=8.8, fill="muted", align="center")
                for part in detail.split("\n")
            ],
            gap=3.5,
        ),
        pad=10.0,
        fill=fill,
        key=key,
    )


def group(title: str, *children, key: str) -> Frame:
    return Frame(
        Stack(
            Text(
                title.upper(),
                size=8.5,
                weight=700,
                fill=SUITE,
                tracking=0.9,
                wrap=False,
            ),
            *children,
            gap=9.0,
        ),
        fill=tint(SUITE, 0.965),
        stroke=SUITE,
        radius=8.0,
        key=key,
    )


def build() -> Doc:
    doc = Doc(680, theme=FIGURE, pad=18)
    doc.add(
        group(
            "a window on your machine",
            Row(
                node(
                    "The editor",
                    "upstream's web application,\nserved from your own disk",
                    key="editor",
                ),
                node(
                    "The bridge",
                    "window.AscDesktopEditor,\nthree small JavaScript files",
                    key="bridge",
                ),
                gap=16.0,
            ),
            key="window",
        ),
        node(
            "The host",
            "Python, answering on 127.0.0.1",
            key="host",
            fill="surface",
        ),
        Row(
            node("x2t", "the converter", key="x2t"),
            node("Your documents", "files on your own disk", key="files"),
            gap=16.0,
        ),
        Text(
            "The editor is ordinary web content. Everything it cannot do in a "
            "browser, it asks the bridge, and the bridge asks the host.",
            size=9.5,
            fill="muted",
            align="center",
        ),
    )
    # No label: a horizontal run between side-by-side boxes has only the
    # gutter to put one in, and the caption says it once for both arrows.
    doc.connect("editor", "bridge")
    doc.connect("window", "host", label="HTTP", color=SUITE)
    doc.connect("host", "x2t", label="runs")
    doc.connect("x2t", "files", heads="<->")
    return doc.describe(
        "What runs where in Libera Suite",
        "The editor and an injected bridge run as web content in a window; the "
        "bridge talks over loopback HTTP to a Python host, which runs the x2t "
        "converter against files on your disk.",
    )


OUTPUT = "what-runs-where.svg"

if __name__ == "__main__":
    print(build().save(Path(__file__).resolve().parents[1] / "src" / "assets" / OUTPUT))
