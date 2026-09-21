"""Open a real window on Linux, and prove something was drawn in it.

The pytest suite covers the host, the bridge and the editor -- but through
`libera --serve` and headless Chromium, which is not the thing that ships.
What ships on Linux is pywebview on GTK 3 and WebKitGTK, and no test anywhere
touches that: on the Mac it is WKWebView instead, and in a container there is
no display.

Xvfb supplies the display. What is left is the two failures that matter and
look identical from the outside -- a window that never appears, and a window
that appears empty because the editor did not load in it.

Run under `xvfb-run`, with libera importable. Writes the screenshot it took
so a human can look at the thing rather than trust a colour count.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# Long enough for x2t to convert the document and the editor to paint. The
# editor's own load is the slow half and has been seen to take twenty seconds
# on a cold payload.
TIMEOUT = 90
# Below this the window is a flat rectangle -- a failed load, or a WebKit that
# never painted. A loaded editor has a toolbar, a ruler and a page in it.
MIN_COLOURS = 24


def windows() -> str:
    return subprocess.run(
        ["xwininfo", "-root", "-tree"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout


def colours(shot: Path) -> int:
    from PIL import Image

    with Image.open(shot) as img:
        # getcolors returns None past maxcolors, which is itself the answer we
        # want -- plenty.
        found = img.convert("RGB").getcolors(maxcolors=1 << 16)
    return len(found) if found else 1 << 16


def main() -> int:
    document, shot = Path(sys.argv[1]), Path(sys.argv[2])

    app = subprocess.Popen(["libera", "-v", str(document)])
    try:
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            if app.poll() is not None:
                print(
                    f"FAIL: libera exited with {app.returncode} before a window",
                    file=sys.stderr,
                )
                return 1
            tree = windows()
            if document.stem in tree or "Libera" in tree:
                break
            time.sleep(1)
        else:
            print(
                f"FAIL: no window named {document.stem!r} after {TIMEOUT}s",
                file=sys.stderr,
            )
            print(windows(), file=sys.stderr)
            return 1

        # The window is mapped; the editor inside it is not necessarily
        # painted. This is the gap that would otherwise pass.
        time.sleep(10)
        subprocess.run(["scrot", "-o", str(shot)], check=True)
    finally:
        app.terminate()
        try:
            app.wait(timeout=15)
        except subprocess.TimeoutExpired:
            app.kill()

    n = colours(shot)
    print(f"    window opened, {n} colours in {shot}")
    if n < MIN_COLOURS:
        print(f"FAIL: only {n} colours -- the window opened empty", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
