"""The editor, loaded for real in a browser, driven by the shipped CLI.

`libera --serve` in a subprocess and a headless Chromium pointed at it: no
fixture reaches into the package, so what is under test is what ships. Slow --
one browser, session-scoped, for the whole directory.

ponytail: raw Chromium, not Playwright. The editor photographs its own canvas
and posts it to the host, so nothing here needs to drive the page; add
Playwright the day we want to click a menu and assert what the host got.
"""

from __future__ import annotations

import contextlib
import functools
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from support import repo_root

from libera import payload as payload_mod
from libera.host import apps

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = repo_root()

# The payload is built and tested against Chromium: "it looked fine in my
# default browser" is not the same statement, so we name the browsers.
BROWSERS = (
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("chromium"),
    shutil.which("google-chrome"),
)

READY = 180  # seconds: a cold payload takes a while to lay out the first page


def _playwright_chromium() -> str | None:
    """The Chromium Playwright installs, which test_keyboard.py already drives.

    `uv run playwright install chromium` is a documented step, so a machine
    that can run one e2e file should run them all -- this one skipped fifteen
    tests on a box that had the browser, because it looked only for a system
    install. Asked of Playwright rather than globbed out of its cache: the
    revision is in that path (chromium-1234) and moves with the version.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            found = p.chromium.executable_path
    except (PlaywrightError, OSError):
        # No browsers installed yet, or no driver to ask. Not an error here:
        # the caller skips, and the skip message says how to fix it.
        return None
    return found if found and Path(found).is_file() else None


@functools.cache
def find_browser() -> str | None:
    """An explicit CHROMIUM wins outright, then the usual places, then Playwright's.

    Called at test time and cached, not at import: asking Playwright costs a
    driver process, and `pytest -m unit` imports this file too.
    """
    if env := os.environ.get("CHROMIUM"):
        return env
    system = next((b for b in BROWSERS if b and Path(b).is_file()), None)
    return system or _playwright_chromium()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def libera(*args: str, **kw) -> subprocess.CompletedProcess:
    """The CLI as a user runs it."""
    return subprocess.run(
        [sys.executable, "-m", "libera", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
        **kw,
    )


@dataclass
class Editor:
    """What one headless run of the editor left behind."""

    url: str
    report: dict
    shot: Path

    @property
    def calls(self) -> dict[str, int]:
        """Bridge methods the editor reached, and how often."""
        return self.report["calls"]


def wait_until_ready(calls: str) -> bool:
    """Poll the host's report until the editor says the document is laid out.

    Not a timer and not the screenshot file: the page "loads" well before the
    document has rendered, and reading the report then gives a half-finished
    picture of what the host was asked for.
    """
    deadline = time.monotonic() + READY
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(calls, timeout=10) as r:
                if "onDocumentContentReady" in json.load(r)["calls"]:
                    return True
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(1)
    return False


@contextlib.contextmanager
def running_editor(document: Path, work: Path) -> Iterator[Editor]:
    """Serve one document, load it in a headless browser, report what happened."""
    browser_exe = find_browser()
    if browser_exe is None:
        pytest.skip(
            "needs Chromium or Chrome: uv run playwright install chromium,"
            " or set CHROMIUM=/path/to/browser"
        )

    shot = work / "render.png"
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
            "--shot",
            str(shot),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        cwd=ROOT,
    )
    # serve prints the editor's address once it is listening, and nothing else.
    # Nothing means it gave up instead of starting, and pointing a browser at
    # an empty URL would look like a slow load for the next three minutes.
    url = server.stdout.readline().strip()
    if not url:
        server.wait(timeout=10)
        pytest.fail(
            f"libera --serve exited with {server.returncode} instead of serving"
        )

    # Chromium leaves helper processes behind when the parent is killed, and a
    # leftover editor starves the next run -- so the profile directory is
    # unique and the whole tree is torn down by it.
    profile = tempfile.mkdtemp(prefix="libera-e2e-")
    browser = subprocess.Popen(
        [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--user-data-dir={profile}",
            "--window-size=1400,900",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    calls = f"http://127.0.0.1:{port}/__host__/calls"
    try:
        if not wait_until_ready(calls):
            # What the host was asked for, before giving up. The stall is
            # intermittent -- roughly one launch in five -- so a failure that
            # says only "never finished" throws away the one run that had
            # something to show. How far it got is the whole question: no calls
            # at all is a page that never ran our bridge, and a long list
            # ending mid-load is the editor stopping partway.
            try:
                with urllib.request.urlopen(calls, timeout=10) as r:
                    got = json.load(r)
            except OSError as e:
                got = {"calls": {}, "errors": [f"could not read the report: {e}"]}
            pytest.fail(
                f"the editor never finished loading within {READY}s\n"
                f"  calls:     {got.get('calls', {})}\n"
                f"  routes:    {got.get('routes', {})}\n"
                f"  errors:    {got.get('errors', [])}\n"
                f"  not found: {got.get('not_found', [])}\n"
                f"  media:     wanted {got.get('media_expected', [])}, "
                f"served {got.get('media_served', [])}"
            )
        # The bridge captures 1.5s after the editor signals ready, and the last
        # report POST is in flight at the same moment.
        deadline = time.monotonic() + 30
        while not shot.exists() and time.monotonic() < deadline:
            time.sleep(1)
        time.sleep(2)
        with urllib.request.urlopen(calls, timeout=30) as r:
            yield Editor(url, json.load(r), shot)
    finally:
        browser.kill()
        subprocess.run(["/usr/bin/pkill", "-f", profile], check=False)
        server.kill()
        server.wait(timeout=10)
        shutil.rmtree(profile, ignore_errors=True)


@pytest.fixture(scope="session")
def editor(tmp_path_factory, sample_document) -> Iterator[Editor]:
    """The plain document, opened for real, to the point of being readable."""
    with running_editor(sample_document, tmp_path_factory.mktemp("e2e")) as e:
        yield e


@pytest.fixture(scope="session")
def illustrated_editor(tmp_path_factory, illustrated_document) -> Iterator[Editor]:
    """The same, for the one thing a document without a picture cannot show."""
    with running_editor(
        illustrated_document, tmp_path_factory.mktemp("e2e-media")
    ) as e:
        yield e


@pytest.fixture(
    scope="session",
    params=[apps.TABLES, apps.SLIDES],
    ids=lambda app: app.name,
)
def blank_editor(request, tmp_path_factory) -> Iterator[Editor]:
    """Tables and Slides in turn, each on the blank its own payload ships.

    Words has the plain sample above; these two only need to prove the second
    and third editors come up at all, which is the whole of what routing a
    doctype can get wrong.
    """
    app = request.param
    work = tmp_path_factory.mktemp(f"e2e-{app.name}")
    document = work / f"blank.{app.ext}"
    shutil.copyfile(payload_mod.resolve().root / "empty" / app.blank, document)
    with running_editor(document, work) as editor:
        yield editor
