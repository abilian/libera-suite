#!/usr/bin/env python3
"""Does the editor's screenshot actually look like laid-out text?

check.py watches bridge traffic and JS errors, which says nothing about what
was drawn. A document whose default styles carried an underline and a quarter
of the normal leading rendered as overlapping, struck-through lines for hours
while every run reported PASS -- so this measures the picture instead.

Deliberately crude: find rows of dark pixels inside the page area, group them
into bands, and complain if there are too few, if two are closer together than
a line of text can be, or if one is a hairline rule. That is the shape of the
failure it exists to catch, and it needs no image library.
"""

from __future__ import annotations

import pathlib
import struct
import sys
import zlib

# The image is the editor's document canvas and nothing else -- the bridge
# captures it from inside the page -- so there is no toolbar or dialog to crop
# around. The only inset needed is enough to clear the page's own border, which
# is a hairline and would otherwise read as a stray underline.
MARGIN = 40
DARK = 128  # a pixel is "ink" if every colour channel is below this
# ...and it is actually opaque. A canvas captured with toDataURL is RGBA, and
# everything outside the page is transparent black -- which reads as ink unless
# alpha is checked, painting the whole image as one enormous line of text.
OPAQUE = 128
MIN_INK_PER_ROW = 3  # ignore specks: cursors, antialiasing
MIN_BANDS = 3  # the sample has four lines of text
# Baseline-to-baseline distance. A line at 11pt/100% occupies ~15px, so two
# text bands closer than this are printed through each other. Measured: a good
# render has pitch [30, 17, 30] (17 being a wrapped pair inside one paragraph);
# the collapsed-leading regression had [12, 5, 23].
MIN_LINE_PITCH = 14
# A band this thin is a rule, not a glyph -- an underline where the sample has
# none. The sample is ours and carries no underlined text, so this is safe.
MIN_BAND_HEIGHT = 3

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SUPPORTED_DEPTH = 8
COLOUR_RGB, COLOUR_RGBA = 2, 6
CHANNELS_RGB, CHANNELS_RGBA = 3, 4
FILTER_NONE, FILTER_SUB, FILTER_UP, FILTER_AVERAGE, FILTER_PAETH = 0, 1, 2, 3, 4


class UnsupportedPNGError(ValueError):
    """The screenshot is not the plain 8-bit truecolour PNG Chromium writes."""


def parse_ihdr(body: bytes) -> tuple[int, int, int]:
    """(width, height, channels), rejecting anything but plain 8-bit truecolour."""
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", body)
    if depth != SUPPORTED_DEPTH or interlace or colour not in {COLOUR_RGB, COLOUR_RGBA}:
        msg = f"depth={depth} colour={colour} interlace={interlace}"
        raise UnsupportedPNGError(msg)
    return width, height, CHANNELS_RGB if colour == COLOUR_RGB else CHANNELS_RGBA


def read_png(path: str) -> tuple[int, int, int, bytes]:
    """Return (width, height, channels, filtered scanlines) for an 8-bit PNG."""
    data = pathlib.Path(path).read_bytes()
    if data[:8] != PNG_MAGIC:
        msg = f"{path} is not a PNG"
        raise UnsupportedPNGError(msg)
    pos, idat, width, height, channels = 8, [], 0, 0, 0
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length  # length + type + body + crc
        if kind == b"IHDR":
            width, height, channels = parse_ihdr(body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    return width, height, channels, zlib.decompress(b"".join(idat))


def unfilter(line: bytearray, prev: bytes, flt: int, channels: int) -> bytearray:
    """Undo one PNG scanline filter, in place."""
    if flt == FILTER_NONE:
        return line
    for i in range(len(line)):
        a = line[i - channels] if i >= channels else 0
        b = prev[i]
        c = prev[i - channels] if i >= channels else 0
        if flt == FILTER_SUB:
            line[i] = (line[i] + a) & 0xFF
        elif flt == FILTER_UP:
            line[i] = (line[i] + b) & 0xFF
        elif flt == FILTER_AVERAGE:
            line[i] = (line[i] + (a + b) // 2) & 0xFF
        elif flt == FILTER_PAETH:
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            line[i] = (line[i] + pred) & 0xFF
    return line


def ink_rows(path: str) -> list[int]:
    """Ink pixels per row, inside a MARGIN inset of the canvas."""
    width, height, channels, raw = read_png(path)
    stride = width * channels
    top, bottom = MARGIN, height - MARGIN
    left, right = MARGIN, width - MARGIN
    prev = bytearray(stride)
    counts: list[int] = []
    pos = 0
    # Filters chain, so every row down to the bottom of the region has to be
    # decoded -- but nothing below it does.
    for y in range(min(height, bottom)):
        # Every row must be unfiltered even when it is outside the region,
        # because each one may be defined against the row above it.
        row = bytearray(raw[pos + 1 : pos + 1 + stride])
        line = unfilter(row, prev, raw[pos], channels)
        pos += 1 + stride
        prev = line
        if top <= y < bottom:
            counts.append(
                sum(
                    1
                    for x in range(left, right)
                    if line[x * channels] < DARK
                    and line[x * channels + 1] < DARK
                    and line[x * channels + 2] < DARK
                    and (channels == CHANNELS_RGB or line[x * channels + 3] >= OPAQUE)
                )
            )
    return counts


def bands(counts: list[int]) -> list[tuple[int, int]]:
    """Runs of consecutive inked rows, as (start, height)."""
    out: list[tuple[int, int]] = []
    start = None
    for i, n in enumerate(counts):
        if n >= MIN_INK_PER_ROW and start is None:
            start = i
        elif n < MIN_INK_PER_ROW and start is not None:
            out.append((start, i - start))
            start = None
    if start is not None:
        out.append((start, len(counts) - start))
    return out


def check(path: str) -> list[str]:
    """Problems with what was drawn. Empty means the page looks like text."""
    found = bands(ink_rows(path))
    starts = [s for s, _ in found]
    pitch = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
    heights = [h for _, h in found]
    problems = []
    if len(found) < MIN_BANDS:
        problems.append(
            f"only {len(found)} line(s) of text drawn, expected {MIN_BANDS}+"
        )
    if pitch and min(pitch) < MIN_LINE_PITCH:
        problems.append(
            f"text lines {min(pitch)}px apart (expected {MIN_LINE_PITCH}+) "
            "- the lines are printed on top of each other"
        )
    if [h for h in heights if h < MIN_BAND_HEIGHT]:
        problems.append(
            "a hairline rule is drawn where the sample has no underlined text"
        )
    print(f"  render: {len(found)} bands, heights {heights}, pitch {pitch}")
    return problems


if __name__ == "__main__":
    for line in check(sys.argv[1]):
        print("  ERROR", line)
