#!/usr/bin/env python3
"""The screenshots on the documentation site, taken from the shipped CLI.

    uv run --with playwright docs/shots.py          # all of them
    uv run --with playwright docs/shots.py words    # one

`libera --serve` in a subprocess and Playwright pointed at the URL it prints,
which is the same path `tests/c_e2e/` drives. Nothing here reaches into the
package: a screenshot that came from a fixture would be a picture of the
fixture, and the whole point of these is to show what a user sees.

The wait is the report, never a timer. A page "loads" well before the document
has been laid out, and a screenshot taken then is of an empty canvas -- which
looks like a rendering bug rather than an impatient script.

Regenerate after anything that changes the chrome: the theme, the payload, the
start window. `make check` in docs/ does not look at images, so a stale one
will sit there indefinitely.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

from playwright.sync_api import sync_playwright

from libera import payload as payload_mod
from libera.host import apps, recents, session
from libera.host.session import Host

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "src" / "assets"
READY = 180  # seconds; a cold payload takes a while to lay out the first page
VIEWPORT = {"width": 1440, "height": 900}

# What the sample document says. Written as prose and parsed, rather than as a
# list of (style, text) pairs: the paragraphs are the point and they should be
# readable as paragraphs here too.
#
# The blank the payload ships carries obfuscated style ids (`a`, `a1`, `af5`)
# and no named heading styles, so the headings below are direct formatting --
# which is what the screenshot needs, and what a user typing into a blank
# document would get anyway.
SUITE = "B5462B"  # the Libera Suite terracotta, from the brand palette
SAMPLE = """\
# Libera Suite

A desktop office suite you can own.

## What it is

Four editors share one application: Words for documents, Tables for
spreadsheets, Slides for presentations, and Diagrams for reading Visio files.
The document picks the editor, so there is nothing to choose.

The editors are Euro-Office, an AGPL fork of ONLYOFFICE by Ascensio System
SIA, running locally and unmodified. The host around them is a few thousand
lines of Python.

## What leaves your machine

Nothing, except when you ask. There is no telemetry, no account and nowhere
for the application to phone. Your documents are read and written on your own
disk, by a converter on your own disk.
"""
RUNS = {  # w:sz is half-points
    "title": f'<w:b/><w:sz w:val="56"/><w:color w:val="{SUITE}"/>',
    "heading": '<w:b/><w:sz w:val="32"/>',
    "body": '<w:sz w:val="22"/>',
}
SPACING = {
    "title": '<w:spacing w:after="240"/>',
    "heading": '<w:spacing w:before="360" w:after="120"/>',
    "body": '<w:spacing w:after="160" w:line="276" w:lineRule="auto"/>',
}


def paragraphs(source: str) -> list[tuple[str, str]]:
    """(style, text) per blank-line-separated block, headings marked by #."""
    out = []
    for block in source.split("\n\n"):
        text = " ".join(block.split())
        if text.startswith("## "):
            out.append(("heading", text[3:]))
        elif text.startswith("# "):
            out.append(("title", text[2:]))
        elif text:
            out.append(("body", text))
    return out


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_until_laid_out(calls: str) -> None:
    """Poll the host's own report until the editor says the document is drawn."""
    deadline = time.monotonic() + READY
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(calls, timeout=10) as r:
                if "onDocumentContentReady" in json.load(r)["calls"]:
                    return
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(1)
    msg = f"the editor never finished loading within {READY}s"
    raise SystemExit(msg)


def shoot(document: Path, out: Path, *, work: Path, shot: Shot) -> None:
    """Serve one document, photograph the window, write `out`."""
    page_path, clip, viewport = shot.page_path, shot.clip, shot.viewport
    port = free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "libera",
            "--serve",
            str(document),
            "--port",
            str(port),
            "--work",
            str(work / "session"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        cwd=ROOT,
    )
    url = server.stdout.readline().strip()
    if not url:
        server.wait(timeout=10)
        msg = f"libera --serve exited with {server.returncode} instead of serving"
        raise SystemExit(msg)

    try:
        if page_path:
            url = f"http://127.0.0.1:{port}{page_path}"
        with sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page(
                viewport=viewport or VIEWPORT, device_scale_factor=2
            )
            page.goto(url, wait_until="commit")
            # Only now. Nothing loads a document until a browser asks for the
            # page, so waiting for the report first waits forever -- which is
            # exactly what the first version of this script did.
            if not page_path:
                wait_until_laid_out(f"http://127.0.0.1:{port}/__host__/calls")
            # The editor paints its rulers and status bar after the document,
            # and the start window fades its tiles in.
            page.wait_for_timeout(4000)
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out), clip=clip)
            browser.close()
    finally:
        server.kill()
        server.wait(timeout=10)
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


def blank(kind: str, work: Path) -> Path:
    """A copy of the payload's own blank document of that kind."""
    app = {"cell": apps.TABLES, "slide": apps.SLIDES}[kind]
    document = work / f"Blank.{app.ext}"
    shutil.copyfile(payload_mod.resolve().root / "empty" / app.blank, document)
    return document


def sample(work: Path) -> Path:
    """The document Words is shown holding.

    Built on the payload's own blank, the way tests/support/make_sample_docx.py
    does and for the same reason: a hand-rolled package carries no styles.xml
    or fontTable.xml, and the font engine falls over resolving a default font.
    """
    blank = payload_mod.resolve().root / "empty" / "new.docx"
    body = "".join(
        f"<w:p><w:pPr>{SPACING[style]}<w:rPr>{RUNS[style]}</w:rPr></w:pPr>"
        f"<w:r><w:rPr>{RUNS[style]}</w:rPr>"
        f'<w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        for style, text in paragraphs(SAMPLE)
    )

    parts = {}
    with zipfile.ZipFile(blank) as z:
        for name in z.namelist():
            parts[name] = z.read(name)

    xml = parts["word/document.xml"].decode()
    head, _, rest = xml.partition("<w:body>")
    # Keep the section properties: page size, margins, the things the blank
    # was set up with. Everything before them is the blank's empty paragraph.
    tail = rest[rest.index("<w:sectPr") :] if "<w:sectPr" in rest else "</w:body>"
    parts["word/document.xml"] = f"{head}<w:body>{body}{tail}".encode()

    document = work / "Libera Suite.docx"
    with zipfile.ZipFile(document, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return document


def seed_recents(work: Path) -> None:
    """Three documents in the Recent list, so the start window has one.

    Written through `remember_recent` rather than by hand: the file has a
    shape, and a seed that guessed it wrong is how this script first produced
    a screenshot of an error message.

    `Host.recents` sits one directory above a session, which is why the
    sessions live under `work/session` and this writes beside them.
    """
    # Beside the work directory, never inside it: remember_recent refuses a
    # document under the recents file's own directory, because that subtree is
    # our plumbing rather than the user's documents.
    folder = work.parent / "Documents"
    folder.mkdir(parents=True, exist_ok=True)
    session.configure(Host(payload=work, work=work / "session"))
    for name in ("Quarterly report.docx", "Budget 2026.xlsx", "Team offsite.pptx"):
        document = folder / name
        document.write_bytes(b"seed")
        recents.remember_recent(document)


class Shot(NamedTuple):
    """One screenshot: what to open, where to point, and how to frame it."""

    label: str
    document: Callable[[Path], Path]
    page_path: str = ""
    clip: dict | None = None
    viewport: dict | None = None


# The start window has no max-width: its layout is whatever width the window
# is. At the editors' 1440 the three tiles stretch, Open becomes a full-width
# slab and every recent row pushes its directory to the far right, which made
# a 2880x940 letterbox next to three 2880x1800 screenshots. 920 is about what
# somebody would size the window to, and the page looks like itself in it.
START_VIEWPORT = {"width": 920, "height": 900}
# New, Open and Recent, and nothing below them. The payload block under those
# prints the resolved payload directory, which on the machine that takes these
# is under somebody's home -- and this file is published. seed_recents() keeps
# the Recent list out of $HOME for the same reason; the clip does it here.
START_CLIP = {"x": 0, "y": 0, "width": START_VIEWPORT["width"], "height": 468}

SHOTS = {
    "words": Shot("Words, holding a document", sample),
    "tables": Shot("Tables", lambda w: blank("cell", w)),
    "slides": Shot("Slides", lambda w: blank("slide", w)),
    "start": Shot(
        "The start window",
        sample,
        page_path="/__host__/start",
        clip=START_CLIP,
        viewport=START_VIEWPORT,
    ),
}


def main(argv: list[str]) -> int:
    wanted = argv[1:] or list(SHOTS)
    unknown = [name for name in wanted if name not in SHOTS]
    if unknown:
        print(f"unknown: {', '.join(unknown)}; have {', '.join(SHOTS)}")
        return 1

    # Not under the repository, and spelt out rather than asked of tempfile:
    # the start window prints each recent document's directory, so the work
    # root ends up in a published screenshot, and macOS answers gettempdir()
    # with /var/folders/s1/p081nm8s0fldt88n5wvm84hr0000gn/T.
    work_root = Path(os.environ.get("SHOTS_ROOT", "/tmp/libera-shots"))
    for name in wanted:
        shot = SHOTS[name]
        work = work_root / name
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        if shot.page_path:
            seed_recents(work)
        shoot(shot.document(work), ASSETS / f"{name}.png", work=work, shot=shot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
