#!/usr/bin/env python3
"""The editor never writes a document: x2t converts in, x2t merges out."""

from __future__ import annotations

from pathlib import Path

from svg_plus import Doc, Frame, Row, Stack, Text
from theme import FIGURE, SUITE


def node(label: str, detail: str, *, key: str, fill: str = "page") -> Frame:
    return Frame(
        Stack(
            Text(label, size=11.5, weight=700, align="center", wrap=False),
            *[
                Text(part, size=9.0, fill="muted", align="center")
                for part in detail.split("\n")
            ],
            gap=4.0,
        ),
        pad=11.0,
        fill=fill,
        key=key,
    )


def build() -> Doc:
    doc = Doc(760, theme=FIGURE, pad=18)
    doc.add(
        Row(
            node(
                "Your document",
                ".docx, .xlsx, .pptx\non your own disk",
                key="doc",
            ),
            node(
                "The editor's working copy",
                "Editor.bin, and a log\nof every change you make",
                key="bin",
                fill="surface",
            ),
            node(
                "Your document, saved",
                "written back in the\nformat you opened",
                key="out",
            ),
            gap=58.0,
        ),
        Text(
            "The editor reads the working copy and appends to the log. It never "
            "writes a document, which is why closing a window can save without "
            "asking it anything, and why a crash leaves something recoverable "
            "on disk.",
            size=9.5,
            fill="muted",
            align="center",
        ),
    )
    doc.connect("doc", "bin", label="x2t", color=SUITE)
    doc.connect("bin", "out", label="x2t", color=SUITE)
    return doc.describe(
        "How a document moves through Libera Suite",
        "x2t converts the document into the editor's working format; the editor "
        "appends changes to a log; saving merges both back through x2t into a "
        "real document.",
    )


OUTPUT = "document-flow.svg"

if __name__ == "__main__":
    print(build().save(Path(__file__).resolve().parents[1] / "src" / "assets" / OUTPUT))
