"""How long Libera takes to put a document on screen, stage by stage.

    lb bench [DOC...] [--runs N] [--app PATH/Libera.app]

Starts the real application (its window, its webview) on each document, and
reads the stages it reaches from the trace LIBERA_STARTUP_TRACE asks it to
write (src/libera/timeline.py):

    python         the interpreter is up and `libera` imported
    host           the GUI host's modules imported, run() started
    converted      x2t has made Editor.bin
    window         the first window exists
    gui-loop       the toolkit's event loop runs
    first-request  the webview asked the server for something
    editor-ready   the editor says the document is laid out
    settled        the window last changed on screen (macOS)

Then, the application still running, a copy of the document is opened in it
the way a double-click does, by a second `libera` that hands it over, and
timed from that moment: the second launcher's own start (`python`), its
window, its conversion, the editor ready and the window settled. Once the
application is open, that is the usual way a document opens.

`settled` is the one to read. At `editor-ready` the window still says
"Loading document", and the text, the working toolbar and the styles gallery
follow over the next second or so. build/macos/watch-window.py captures the
window and notes each change; a run ends once the editor is ready and the
window has not changed for QUIET seconds. Then it quits by Cmd-Q, as a person
does. Elsewhere a run ends at `editor-ready` and is terminated, which leaves
the document's lock file behind.

Each document runs in a home directory of its own, so nothing touches your
sessions or a Libera you have open. The index of the machine's fonts is built
there before the first run, as a user's launch finds it: left to the first
run, it was built beside the editor's load, and went on into the runs after,
since allfontsgen outlives a quit. Not with --app, whose payload is its own.

A scratch home does not empty WebKit's cache, which macOS keeps under the real
home whatever HOME says, by bundle ID: for this checkout's interpreter,
~/Library/Caches/org.python.python/WebKit, shared with every `libera` run from
a terminal. So these are usual launches, cache warm.

Runs back to back are not usual launches in another way: the converter's
libraries stay in memory between them, where a launch after a while without
one finds them gone (0.6 s more for x2t to start, measured). --idle N waits N
seconds before each run.

Without DOCs: the blank Words document and the test sample with a picture.
With --app, the bundle's own executable instead of this checkout's
interpreter, and its own payload. See notes/21-startup-and-size.md.
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from libera import payload
from libera_build.repo import REPO

if TYPE_CHECKING:
    from collections.abc import Callable

STAGES = (
    "python",
    "host",
    "converted",
    "window",
    "gui-loop",
    "first-request",
    "editor-ready",
    "settled",
)
# Long enough for a cold first launch on a slow machine; a run that takes it is
# reported, not hidden.
TIMEOUT = 90.0
# What a document opened in the running application goes through.
AGAIN = ("python", "window", "converted", "editor-ready", "settled")
# How long the window has to stay as it is, once the editor is ready, for the
# document to count as on screen.
QUIET = 2.0
WATCHER = REPO / "build" / "macos" / "watch-window.py"


def make_default_documents(into: Path) -> list[Path]:
    blank = into / "blank.docx"
    shutil.copy(payload.resolve().root / "empty" / "new.docx", blank)
    sample = into / "sample-with-picture.docx"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tests/support/make_sample_docx.py"),
            str(sample),
            "--image",
        ],
        check=True,
    )
    return [blank, sample]


def build_font_index(home: Path) -> None:
    """The index of the machine's fonts, in a scratch home, built now."""
    script = (
        "from libera import payload\n"
        "from libera.payload import fonts, locate\n"
        "layout = locate.Layout(payload.resolve().root)\n"
        "if fonts.is_wanted():\n"
        "    fonts.build(layout, fonts.get_index_dir(layout))\n"
    )
    env = {**os.environ, "HOME": str(home)}
    subprocess.run([sys.executable, "-c", script], env=env, check=True)


def run_once(
    command: list[str], document: Path, home: Path
) -> tuple[dict[str, float], dict[str, float]]:
    """The stages one launch reaches, in seconds from its start, and those of
    a copy of the document then opened in it, from the moment it was asked."""
    trace, screen = home / "startup.trace", home / "again.trace"
    trace.unlink(missing_ok=True)
    screen.unlink(missing_ok=True)
    # Another path, so that it is another window, and the same name.
    copy = home / "again" / document.name
    copy.parent.mkdir(exist_ok=True)
    shutil.copy(document, copy)
    env = {**os.environ, "HOME": str(home), "LIBERA_STARTUP_TRACE": str(trace)}
    started = time.time()
    process = subprocess.Popen(
        [*command, str(document)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    watching = sys.platform == "darwin"
    watchers = [watch(process, trace)] if watching else []
    try:
        first = wait_for(lambda: read_trace(trace, started), started, watching)
        if watching:
            watchers.append(watch(process, screen, new=True))
            # It creates the file once it knows the windows already there.
            while not screen.exists():
                time.sleep(0.02)
        asked = time.time()
        subprocess.run(
            [*command, str(copy)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=True,
        )
        second = wait_for(lambda: read_again(trace, screen, asked), asked, watching)
    finally:
        if watching:
            quit_by_keyboard(process)
            for watcher in watchers:
                watcher.wait(timeout=10)
        else:
            process.terminate()
            process.wait(timeout=10)
    return first, second


def watch(
    process: subprocess.Popen, trace: Path, *, new: bool = False
) -> subprocess.Popen:
    """The watcher of the process's window; with `new`, of the next one."""
    return subprocess.Popen(
        [sys.executable, str(WATCHER), str(process.pid), str(trace)]
        + (["--new"] if new else [])
    )


def wait_for(
    read: Callable[[], dict[str, float]], started: float, watching: bool
) -> dict[str, float]:
    """What `read` says, once it is done or TIMEOUT has passed."""
    reached: dict[str, float] = {}
    while (now := time.time() - started) < TIMEOUT and not is_done(
        reached, now, watching=watching
    ):
        reached = read()
        time.sleep(0.02)
    return reached


def read_again(trace: Path, screen: Path, asked: float) -> dict[str, float]:
    """The stages of the document opened in the running application: the
    host's, written again since it was asked for, and the changes of its own
    window, which another watcher writes to `screen`."""
    reached = read_trace(trace, asked)
    reached.pop("settled", None)
    return reached | read_trace(screen, asked)


def read_trace(trace: Path, started: float) -> dict[str, float]:
    """Each stage the first time it was written since `started`, but for the
    window's changes, whose last is `settled`. The editor says it is ready
    twice in one window, the second time most of a second later."""
    reached: dict[str, float] = {}
    if not trace.exists():
        return reached
    for line in trace.read_text(encoding="utf-8").splitlines():
        at, stage = line.split(" ", 1)
        since = float(at) - started
        if stage == "screen":
            reached["settled"] = since
        elif since >= 0:
            reached.setdefault(stage, since)
    return reached


def is_done(reached: dict[str, float], now: float, *, watching: bool) -> bool:
    """Whether a run `now` seconds in has seen all it will: the editor ready,
    and when the window is watched, QUIET seconds without a change since."""
    if "editor-ready" not in reached:
        return False
    if not watching:
        return True
    last = max(reached.get("settled", 0.0), reached["editor-ready"])
    return now - last > QUIET


def quit_by_keyboard(process: subprocess.Popen) -> None:
    """Cmd-Q to the process, as a person quits, which releases the document's
    lock as terminating it does not. System Events needs Accessibility for the
    terminal; without it, or if the process does not end, it is terminated.

    Not timed: most of the time it takes is osascript's own start.
    """
    front = (
        'tell application "System Events" to set frontmost of '
        f"(first process whose unix id is {process.pid}) to true"
    )
    keys = 'tell application "System Events" to keystroke "q" using command down'
    subprocess.run(
        ["osascript", "-e", front, "-e", keys],
        capture_output=True,
        check=False,
    )
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=10)


def show(name: str, runs: list[dict[str, float]], stages: tuple[str, ...]) -> None:
    print(f"\n{name}")
    print(f"  {'':14}" + "".join(f"{'run ' + str(i + 1):>9}" for i in range(len(runs))))
    for stage in stages:
        cells = "".join(
            f"{r[stage]:8.2f}s" if stage in r else f"{'--':>9}" for r in runs
        )
        print(f"  {stage:14}{cells}")
    ready = [r["editor-ready"] for r in runs if "editor-ready" in r]
    missed = len(runs) - len(ready)
    settled = [r["settled"] for r in runs if "settled" in r]
    print(
        f"  editor ready, median {statistics.median(ready):.2f}s" if ready else "",
        f"({missed} run(s) not ready within {TIMEOUT:.0f}s)" if missed else "",
    )
    if settled:
        print(f"  on screen, median {statistics.median(settled):.2f}s")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("documents", nargs="*", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--app", type=Path, help="a built Libera.app")
    parser.add_argument(
        "--idle",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="wait before each run, so that it starts cold, like a launch",
    )
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="libera-bench-") as scratch_name:
        scratch = Path(scratch_name)
        documents = [d.resolve() for d in args.documents] or make_default_documents(
            scratch
        )
        if args.app:
            command = [str(args.app.resolve() / "Contents" / "MacOS" / "Libera")]
        else:
            command = [sys.executable, "-m", "libera"]
            # The scratch home hides the installed payload: name it.
            os.environ.setdefault("LIBERA_PAYLOAD", str(payload.resolve().root))
        for document in documents:
            home = scratch / f"home-{document.stem}"
            home.mkdir()
            if not args.app:
                build_font_index(home)
            runs = []
            for _ in range(args.runs):
                time.sleep(args.idle)
                runs.append(run_once(command, document, home))
            name = f"{document.name} ({document.stat().st_size // 1024} KB)"
            show(name, [first for first, _ in runs], STAGES)
            show(
                f"{name}, opened in the running application",
                [s for _, s in runs],
                AGAIN,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
