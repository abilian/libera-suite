"""five-minutes.sh for Windows, where the installed application is frozen and
has no Python to run the gui tier's driver in.

    uv run --with websocket-client python five-minutes-windows.py DRIVER WORK

So the driver's steps run from outside instead, through the DevTools protocol:
WebView2 opens a debugging port when WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
asks it to, and `driver.Page` takes anything with `evaluate_js`. The window,
WebView2, the host and the payload are the installed Libera.exe's; nothing
in the product changes. Each window is started in the desktop session by a
scheduled task, as released-gui.ps1 starts its own (ssh's session has none),
with a LOCALAPPDATA of its own, so no window finds another's state, and then
killed: a window ended that way leaves its session behind, and the next
launch, with the same state directory, would offer to recover it.

In Words, Tables and Slides: a blank (out of the installed payload) opened, a
line entered and saved, the line looked for in the file, the file opened in
a new window and its page photographed (Page.captureScreenshot). It prints
FIVE_<EXT>=ok or the reason, and SHOT_<EXT>=bytes, as five-minutes.sh does.

Run on a builder, which has nothing of its own open: it ends every Libera.exe.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile

import websocket  # websocket-client, which `uv run --with` brings

MARK = "Five minutes with Libera Suite"
APP = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Libera Suite"
TASK = "libera-five-minutes"
PAGE_BUDGET = 120


class DevTools:
    """One page over the DevTools protocol, with pywebview's `evaluate_js`."""

    def __init__(self, url: str) -> None:
        self.socket = websocket.create_connection(url, timeout=60)
        self.last = 0

    def call(self, method: str, **params: object) -> dict:
        self.last += 1
        self.socket.send(
            json.dumps({"id": self.last, "method": method, "params": params})
        )
        while True:
            answer = json.loads(self.socket.recv())
            if answer.get("id") == self.last:
                return answer.get("result", {})

    def evaluate_js(self, expression: str) -> object:
        result = self.call(
            "Runtime.evaluate", expression=expression, returnByValue=True
        )
        return result.get("result", {}).get("value")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def end_every_window() -> None:
    subprocess.run(
        ["taskkill", "/F", "/T", "/IM", "Libera.exe"], capture_output=True, check=False
    )
    time.sleep(2)


def launch(document: pathlib.Path, work: pathlib.Path, name: str) -> DevTools:
    """Libera.exe on `document`, in the desktop session, with a debugging
    port; its editor's page once it is there."""
    port = free_port()
    state = work / f"local-{name}"
    state.mkdir(parents=True, exist_ok=True)
    cmd = work / f"{name}.cmd"
    cmd.write_text(
        "@echo off\r\n"
        f"set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port={port}\r\n"
        f"set LOCALAPPDATA={state}\r\n"
        f'start "" "{APP / "Libera.exe"}" "{document}"\r\n',
        encoding="ascii",
    )
    subprocess.run(
        [
            "schtasks",
            "/create",
            "/tn",
            TASK,
            "/tr",
            str(cmd),
            "/sc",
            "once",
            "/st",
            "23:59",
            "/it",
            "/f",
        ],
        capture_output=True,
        check=True,
    )
    subprocess.run(["schtasks", "/run", "/tn", TASK], capture_output=True, check=True)
    deadline = time.monotonic() + PAGE_BUDGET
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=5
            ) as r:
                pages = json.load(r)
        except OSError:
            pages = []
        for page in pages:
            if page.get("type") == "page" and "/documents/index.html" in page.get(
                "url", ""
            ):
                return DevTools(page["webSocketDebuggerUrl"])
        time.sleep(1)
    msg = f"no editor page on port {port} in {PAGE_BUDGET} s"
    raise AssertionError(msg)


def holds(document: pathlib.Path, text: str) -> bool:
    with zipfile.ZipFile(document) as z:
        return any(
            text.encode() in z.read(n) for n in z.namelist() if n.endswith(".xml")
        )


def blanks_into(work: pathlib.Path) -> None:
    """The blanks of the payload the installed application reports."""
    said = subprocess.run(
        [str(APP / "libera-cli.exe"), "--payload-status"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    root = next(
        (
            pathlib.Path(line.split(":", 1)[1].strip())
            for line in said.splitlines()
            if line.startswith("payload:")
        ),
        None,
    )
    if root is None:
        msg = f"the installed application names no payload: {said}"
        raise AssertionError(msg)
    for ext in ("docx", "xlsx", "pptx"):
        (work / f"five.{ext}").write_bytes((root / "empty" / f"new.{ext}").read_bytes())


def one_editor(driver, work: pathlib.Path, ext: str) -> str:
    """ok, or what went wrong."""
    document = work / f"five.{ext}"
    try:
        page = driver.Page(launch(document, work, f"typed-{ext}"))
        page.open_with([])
        driver.do_type_and_save(page, document, MARK, "")
    except (AssertionError, OSError, websocket.WebSocketException) as e:
        return f"typing and saving: {e}"
    finally:
        end_every_window()
        # The lock the killed window left beside the document. Its profile is
        # that window's LOCALAPPDATA, not the next one's, so the next would
        # find it someone else's and open the file read-only; after a real
        # crash, with one state directory, it is taken over (host/locking.py).
        document.with_name(f".~lock.{document.name}#").unlink(missing_ok=True)
    if not holds(document, MARK):
        return "saved, and the text is not in the file"
    try:
        tools = launch(document, work, f"reopened-{ext}")
        driver.Page(tools).open_with([])
        time.sleep(2)  # onDocumentContentReady fires before the first paint settles
        png = tools.call("Page.captureScreenshot", format="png")["data"]
        (work / f"five-{ext}.png").write_bytes(base64.b64decode(png))
    except (AssertionError, OSError, KeyError, websocket.WebSocketException) as e:
        return f"opening it again: {e}"
    finally:
        end_every_window()
    return "ok"


def main() -> None:
    spec = importlib.util.spec_from_file_location("driver", sys.argv[1])
    driver = importlib.util.module_from_spec(spec)
    sys.modules["driver"] = driver  # its dataclass looks itself up there
    spec.loader.exec_module(driver)
    work = pathlib.Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)
    end_every_window()
    try:
        blanks_into(work)
    except (AssertionError, OSError) as e:
        print(f"FIVE=no blanks: {e}")
        return
    try:
        for ext in ("docx", "xlsx", "pptx"):
            said = one_editor(driver, work, ext)
            print(f"FIVE_{ext.upper()}={said}", flush=True)
            if said == "ok":
                print(
                    f"SHOT_{ext.upper()}={(work / f'five-{ext}.png').stat().st_size}",
                    flush=True,
                )
    finally:
        subprocess.run(
            ["schtasks", "/delete", "/tn", TASK, "/f"], capture_output=True, check=False
        )


if __name__ == "__main__":
    main()
