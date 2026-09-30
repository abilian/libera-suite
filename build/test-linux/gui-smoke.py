"""Open a real window on Linux, and prove something was drawn in it.

The pytest suite covers the host, the bridge and the editor -- but through
`libera --serve` and headless Chromium, which is not the thing that ships.
What ships on Linux is pywebview on GTK 3 and WebKitGTK, and no test anywhere
touches that: on the Mac it is WKWebView instead, and in a container there is
no display.

Xvfb supplies the display. What is left is the two failures that matter and
look identical from the outside -- a window that never appears, and a window
that appears empty because the editor did not load in it.

It takes **several documents**, and asserts a window for each. That is the
check a beta tester's report needed and nothing had: "impossible d'avoir deux
documents de types différents (texte et présentation) ouverts simultanément".
`app.py`'s `_open_rest` opens the second and later documents, and it waited on
`webview.windows` -- a list `create_window` fills before `start()` runs -- so it
returned at once and every later document raced the GUI loop. A harness that
opens one document cannot see that, whichever way the race falls.

Run under `xvfb-run`, with libera importable. Writes the screenshot it took
so a human can look at the thing rather than trust a colour count.

    gui-smoke.py DOCUMENT [DOCUMENT...] SHOT.png
"""

from __future__ import annotations

import re
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
# A document and a screenshot: the shortest call this takes. Everything between
# argv[1] and argv[-1] is another document.
MIN_ARGS = 3


def windows() -> str:
    return subprocess.run(
        ["xwininfo", "-root", "-tree"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout


# Every document gets a window of its own, titled by app.py's open_window as
# "<name> — <editor>". The name is the only per-document signal there is, and
# the old check accepted `"Libera" in tree` as an alternative to it -- which one
# window satisfies however many documents were asked for, so it could not have
# caught the bug this file now tests for.
def titles() -> list[str]:
    """Every window name X knows about.

    xwininfo quotes each name, and prints children as well as top-level
    windows: WebKit nests its own, and they carry the parent's name. So this
    answers "is there a window for this document", never "how many".
    """
    return re.findall(r'"([^"]*)"', windows())


def missing(documents: list[Path]) -> list[Path]:
    seen = titles()
    return [d for d in documents if not any(d.name in t for t in seen)]


def colours(shot: Path) -> int:
    from PIL import Image

    with Image.open(shot) as img:
        # getcolors returns None past maxcolors, which is itself the answer we
        # want -- plenty.
        found = img.convert("RGB").getcolors(maxcolors=1 << 16)
    return len(found) if found else 1 << 16


def main() -> int:
    if len(sys.argv) < MIN_ARGS:
        print(__doc__, file=sys.stderr)
        return 2
    documents = [Path(a) for a in sys.argv[1:-1]]
    shot = Path(sys.argv[-1])

    # Each document is a conversion and an editor load, and only the first
    # overlaps the application's own startup, so the budget grows per document
    # rather than being one number that was generous for one and tight for two.
    budget = TIMEOUT + 45 * (len(documents) - 1)
    deadline = time.time() + budget

    # stdout and stderr are inherited on purpose. The e2e harness sent a
    # browser's output to DEVNULL and the only symptom left was a stopwatch;
    # `-v` here is the narrative that says which document reached which stage.
    app = subprocess.Popen(["libera", "-v", *(str(d) for d in documents)])
    try:
        while time.time() < deadline:
            if app.poll() is not None:
                print(
                    f"FAIL: libera exited with {app.returncode} before"
                    f" {len(documents)} window(s)",
                    file=sys.stderr,
                )
                return 1
            absent = missing(documents)
            if not absent:
                break
            time.sleep(1)
        else:
            absent = missing(documents)
            print(
                f"FAIL: no window for {', '.join(d.name for d in absent)}"
                f" after {budget}s"
                f" ({len(documents) - len(absent)}/{len(documents)} opened)",
                file=sys.stderr,
            )
            print(windows(), file=sys.stderr)
            return 1
        print(
            f"    {len(documents)} window(s) open: "
            + ", ".join(d.name for d in documents)
        )

        # The window is mapped; the editor inside it is not necessarily
        # painted. This is the gap that would otherwise pass.
        time.sleep(10)
        # build/out is gitignored, so a fresh clone does not have it and scrot
        # fails with "No such file or directory" after everything this script
        # exists to check has already passed -- which reads as a GUI failure
        # and is a missing directory.
        shot.parent.mkdir(parents=True, exist_ok=True)
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
