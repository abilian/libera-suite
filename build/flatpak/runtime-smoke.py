"""Convert a document inside the Flatpak sandbox, and check what came back.

x2t is compiled in one userland (Ubuntu 24.04) and runs in another
(org.gnome.Platform, a newer glibc). That is the forward direction and is
expected to work -- but "expected to work" is the phrase this project keeps
being wrong about, and no other check in the tree would notice if it stopped.

Runs in the builder container, against the bundle alone: the payload is inside
it, so this exercises what a user gets rather than one the test put there.
Three assertions, all on content:

- `libera --serve` prints a URL. serve runs opening.open_document --
  which runs x2t -- before it prints anything, and reports NotReadyError
  instead when that fails. A URL means the conversion happened in there.
- the page it serves carries all three bridge scripts. A 200 holding
  upstream's own HTML would mean the splice quietly stopped happening, which
  is the kind of failure that looks like success.
- a text file converted to docx holds the text, and that docx converted to
  PDF has an embedded font and text operators: the PDF is sdkjs running in
  V8, the part of the converter most likely to mind a different userland.

The blank comes out of the payload, so nothing here needs a source tree inside
the sandbox. Converting it is what File > New does.

Where that payload *is* comes from `libera --payload-status`, not from a path
written here. It used to read $XDG_DATA_HOME/libera/payload, which was true
while the bundle fetched its editors on first run and became a `find` over a
directory that does not exist when it stopped. The application knows; ask it.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
import urllib.request
import zipfile
import zlib
from pathlib import Path

APP_ID = "eu.liberasuite.Libera"
BRIDGE = ("bridge-runtime.js", "bridge-page.js", "bridge-desktop.js")
TIMEOUT = 180
TEXT = "Converted in the Flatpak sandbox"
# Under the home folder, which the bundle may write (--filesystem=home), so
# the files the sandbox writes are read here at the same path.
WORK = Path.home() / "flatpak-smoke"

IN_SANDBOX = """
set -eu
root=$(libera --payload-status | sed -n 's/^payload: *//p')
[ -n "$root" ] || { echo "libera --payload-status named no payload" >&2; exit 1; }
# The default (US English) blank, by name: `find | head -1` takes whichever
# locale the filesystem lists first, Galician on the arm64 builder.
blank="$root/empty/new.docx"
[ -f "$blank" ] || { echo "no $blank" >&2; exit 1; }
cp "$blank" "$HOME/smoke.docx"
exec libera --serve "$HOME/smoke.docx"
"""


CONVERT = f"""
set -eu
cd "$0"
printf '%s\\n' "{TEXT}" > convert.txt
libera --convert convert.txt -t docx
libera --convert convert.docx -t pdf
"""


def inflated(stream: bytes) -> bytes:
    try:
        return zlib.decompress(stream)
    except zlib.error:
        return b""


def pdf_shows_text(pdf: Path) -> bool:
    """smoke.sh's test: a page, an embedded font and text operators. A PDF of
    the right size with no glyphs in it is the failure that looks like success."""
    raw = pdf.read_bytes()
    streams = re.findall(rb"stream\r?\n(.*?)endstream", raw, re.DOTALL)
    body = b"".join(inflated(stream) for stream in streams)
    return bool(
        re.search(rb"/Type\s*/Page[^s]", raw)
        and b"/FontFile2" in raw
        and re.search(rb"\].*?TJ|\(.*?\)\s*Tj", body, re.DOTALL)
    )


def convert() -> int:
    WORK.mkdir(exist_ok=True)
    done = subprocess.run(
        ["flatpak", "run", "--command=sh", APP_ID, "-c", CONVERT, str(WORK)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )
    if done.returncode:
        return fail("libera --convert failed in the sandbox", done.stdout + done.stderr)
    with zipfile.ZipFile(WORK / "convert.docx") as docx:
        if TEXT not in docx.read("word/document.xml").decode("utf-8"):
            return fail("the docx converted in the sandbox lacks its text")
    if not pdf_shows_text(WORK / "convert.pdf"):
        return fail("the PDF converted in the sandbox shows no text")
    print("    text -> docx -> pdf in the sandbox, the text in each")
    return 0


def fail(message: str, log: str = "") -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    if log:
        print(log, file=sys.stderr)
    return 1


def main() -> int:
    log = Path("/tmp/serve.log")
    log.write_text("", encoding="utf-8")

    with log.open("w", encoding="utf-8") as sink:
        serving = subprocess.Popen(
            ["flatpak", "run", "--command=sh", APP_ID, "-c", IN_SANDBOX],
            stdout=sink,
            stderr=subprocess.STDOUT,
        )

    try:
        url = None
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            text = log.read_text(encoding="utf-8", errors="replace")
            found = re.search(r"https?://\S+", text)
            if found:
                url = found.group()
                break
            if serving.poll() is not None:
                return fail("--serve exited before printing a URL", text)
            time.sleep(1)
        else:
            text = log.read_text(encoding="utf-8", errors="replace")
            return fail(f"no URL in {TIMEOUT}s -- x2t did not convert", text)

        print(f"    x2t converted the blank in the sandbox; serving at {url}")

        page = urllib.request.urlopen(url, timeout=60).read()
        text = page.decode("utf-8", "replace")
        missing = [part for part in BRIDGE if part not in text]
        if missing:
            return fail(f"the served page does not carry {', '.join(missing)}")
        print(f"    the page carries all three bridge scripts ({len(page)} bytes)")
    finally:
        serving.terminate()
        try:
            serving.wait(timeout=15)
        except subprocess.TimeoutExpired:
            serving.kill()

    if status := convert():
        return status
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
