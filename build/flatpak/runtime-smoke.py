"""Convert a document inside the Flatpak sandbox, and check what came back.

x2t is compiled in one userland (Ubuntu 24.04) and runs in another
(org.gnome.Platform, a newer glibc). That is the forward direction and is
expected to work -- but "expected to work" is the phrase this project keeps
being wrong about, and no other check in the tree would notice if it stopped.

Runs in the builder container, against the bundle alone: the payload is inside
it, so this exercises what a user gets rather than one the test put there.
Two assertions, both on content:

- `libera --serve` prints a URL. cmd_serve runs opening.open_document --
  which runs x2t -- before it prints anything, and reports NotReadyError
  instead when that fails. A URL means the conversion happened in there.
- the page it serves carries all three bridge scripts. A 200 holding
  upstream's own HTML would mean the splice quietly stopped happening, which
  is the kind of failure that looks like success.

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
from pathlib import Path

APP_ID = "eu.liberasuite.Libera"
BRIDGE = ("bridge-runtime.js", "bridge-page.js", "bridge-desktop.js")
TIMEOUT = 180

IN_SANDBOX = """
set -eu
root=$(libera --payload-status | sed -n 's/^payload: *//p')
[ -n "$root" ] || { echo "libera --payload-status named no payload" >&2; exit 1; }
blank=$(find "$root" -name new.docx | head -1)
[ -n "$blank" ] || { echo "no new.docx under $root" >&2; exit 1; }
cp "$blank" "$HOME/smoke.docx"
exec libera --serve "$HOME/smoke.docx"
"""


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

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
