"""The application itself, in a real window, on whichever platform runs this.

The e2e tier drives `libera --serve` with headless Chromium, which is the
editor and the bridge but not the window. What ships is pywebview on WKWebView
(macOS), WebKitGTK (Linux) or WebView2 (Windows), and a difference between
those engines has already reached a user: see
`tests/c_e2e/host/test_file_menu.py`, where the editor lost Save As in WebKit
and never in Chromium.

So this tier launches the shipped CLI, lets it open real windows, and reads
what each window's own page photographed of its canvas (`libera --shot`, armed
per session in `document.serve_current`). Measuring the picture that way needs no
screenshot utility and no screen-recording permission: the page posts it to
the host, which writes it where `--shot` said.

Two things make this safe to run on a machine somebody is using:

- Every launch gets a home of its own, so it cannot find the user's running
  Libera Suite and hand its documents to it (`instance.hand_off`), and leaves
  no state, no config and no Recent list behind.
- The tier is skipped unless a run asks for it by marker (the root conftest)
  and unless this platform can put a window on screen.

It takes the focus while it runs, which is the one cost of testing a window.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from support import render

from libera.payload import locate

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

# The first window is a conversion, an editor load and the application's own
# startup; every window after it is another conversion and another load, and
# a cold payload has been seen to take twenty seconds over the load alone.
FIRST_WINDOW = 120
PER_WINDOW = 45

# Xvfb has no GPU. Without these WebKit takes an accelerated path and the
# window maps without ever painting -- which is the failure this tier exists
# to catch, so it would report a bug that is not one. On a real desktop they
# cost some compositing and change nothing else.
SOFTWARE_RENDERING = {
    "WEBKIT_DISABLE_COMPOSITING_MODE": "1",
    "LIBGL_ALWAYS_SOFTWARE": "1",
}


def can_open_a_window() -> str | None:
    """None when a window can be put on screen here, else why not."""
    if sys.platform.startswith("linux"):
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return "no display: run it under xvfb-run, or `lb linux gui-test`"
        from libera import gui

        cannot = gui.explain_why_no_window()
        return cannot.splitlines()[0] if cannot else None
    # macOS and Windows need no packages for a window, but they do need a
    # session. Over ssh there is none, and the window never appears.
    if os.environ.get("SSH_CONNECTION"):
        return f"no window session: ssh into {platform.node()} has no desktop"
    return None


@dataclass
class Launch:
    """One `libera DOCUMENT...`: its process, and what its windows drew."""

    process: subprocess.Popen[bytes]
    shot: Path
    output: Path
    documents: list[Path]
    # The size each render was last seen at, so a file still being written is
    # not handed to a test that is about to parse it as a PNG.
    settling: dict[Path, int] = field(default_factory=dict)

    def shots(self) -> list[Path]:
        """The renders a window has posted and the host has finished writing."""
        done: list[Path] = []
        for png in sorted(self.shot.parent.glob(f"{self.shot.stem}*.png")):
            size = png.stat().st_size
            if size and self.settling.get(png) == size:
                done.append(png)
            self.settling[png] = size
        return done

    def said(self) -> str:
        """Everything the process printed: `-v` says which stage it reached."""
        return self.output.read_text(encoding="utf-8", errors="replace")

    def windows_that_painted(self, count: int) -> list[Path]:
        """Wait for `count` windows to post a render, or fail saying what came.

        The budget grows per window rather than being one number that is
        generous for one window and tight for three.
        """
        deadline = time.monotonic() + FIRST_WINDOW + PER_WINDOW * (count - 1)
        while time.monotonic() < deadline:
            if (code := self.process.poll()) is not None:
                pytest.fail(
                    f"libera exited with {code} before {count} window(s)"
                    f" painted\n{self.said()}"
                )
            painted = self.shots()
            if len(painted) >= count:
                return painted
            time.sleep(1)
        pytest.fail(
            f"{len(self.shots())}/{count} window(s) painted in the budget."
            f" A window that opens and never paints looks exactly like this."
            f"\n{self.said()}"
        )


def complaints(shot: Path) -> list[str]:
    """What the ink measurement says about one window's picture."""
    return render.check(str(shot))


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip the tier where no window can be put on screen.

    A hook rather than an autouse fixture, as in the root conftest: the answer
    is about the machine, not about anything a test asked for.
    """
    why_not = can_open_a_window()
    if why_not:
        pytest.skip(why_not)


@pytest.fixture(scope="session")
def payload_root() -> Path:
    """The payload this run found, named for the launches below.

    They cannot find it themselves: each gets a home of its own, and an
    installed payload lives under the real one. Resolved here, where the home
    is still the user's, and handed over as LIBERA_PAYLOAD.
    """
    return locate.resolve().root


@pytest.fixture
def launch(tmp_path: Path, payload_root: Path) -> Iterator[Callable[..., Launch]]:
    """Start the shipped CLI on some documents; close its windows afterwards."""
    home = tmp_path / "home"
    home.mkdir()
    shot = tmp_path / "shots" / "window.png"
    shot.parent.mkdir(parents=True)
    output = tmp_path / "libera.log"

    # A home of its own. Every platform's state directory sits under one of
    # these, so this launch neither finds the user's instance nor writes
    # anything of theirs: see payload/locate.py, get_state_dir.
    env = {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "LIBERA_PAYLOAD": str(payload_root),
        **SOFTWARE_RENDERING,
    }

    started: list[Launch] = []

    def start(*documents: Path) -> Launch:
        # `python -m libera` rather than the console script: the same entry
        # point, found without depending on what is on PATH. Output to a file
        # rather than DEVNULL, because a window that does not paint leaves
        # nothing else to read.
        with output.open("wb") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "libera",
                    "-v",
                    "--shot",
                    str(shot),
                    *(str(d) for d in documents),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
            )
        it = Launch(process, shot, output, list(documents))
        started.append(it)
        return it

    yield start

    for it in started:
        it.process.terminate()
        try:
            it.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            it.process.kill()


@pytest.fixture(scope="session")
def blank_presentation(
    tmp_path_factory: pytest.TempPathFactory, payload_root: Path
) -> Path:
    """A blank .pptx out of the payload: a second document, of another type."""
    target = tmp_path_factory.mktemp("doc") / "blank.pptx"
    shutil.copyfile(payload_root / "empty" / "new.pptx", target)
    return target
