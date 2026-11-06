"""A real window, driven from inside the application's process.

Playwright cannot do this: its WebKit hangs on macOS 14 (tests/c_e2e/host/conftest.py),
and it is not any engine that ships in any case.

Each window is a process of this script, with a home of its own, that runs `app.run`
on its main thread as the CLI does and the steps on another, through pywebview's
`evaluate_js`. So the window, the engine, the bridge and the host are the real ones.
Two things are not:

- The file dialog of the signature panel is answered for (`choose_open_path`), since a
  script cannot pick a file in one. On a Mac it is first checked to come up, then
  cancelled.
- Text is entered through the editor's API, not typed, and a Save or File > Protect
  called as the menu item calls it.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from libera.host.session import Session

# Xvfb has no GPU. Without these WebKit takes an accelerated path and the
# window maps without ever painting -- which is the failure this tier exists
# to catch, so it would report a bug that is not one. On a real desktop they
# cost some compositing and change nothing else.
SOFTWARE_RENDERING = {
    "WEBKIT_DISABLE_COMPOSITING_MODE": "1",
    "LIBGL_ALWAYS_SOFTWARE": "1",
}

WINDOW_BUDGET = 180
READY = 120
SAVED = 60


def window_env(home: pathlib.Path, payload: pathlib.Path) -> dict[str, str]:
    """What a process needs set to keep to `home`. Every platform's state directory
    sits under one of these, so it neither finds the user's instance nor writes
    anything of theirs: see payload/locate.py, get_state_dir. And the payload, which
    an installed one would have it look for under the real home."""
    return {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "LIBERA_PAYLOAD": str(payload),
        **SOFTWARE_RENDERING,
    }


# --- the page ---------------------------------------------------------------


def inner(expression: str) -> str:
    """JavaScript for `expression` in the editor's frame, as `w` and `d`; null
    while there is no such frame yet."""
    return (
        "(() => { try { const w = document.querySelector('iframe').contentWindow;"
        f" const d = w.document; return ({expression}); }} catch (e) {{ return null; }}"
        " })()"
    )


# The field on screen: the editor keeps others in the page, for dialogs it has not
# opened.
PASSWORD_FIELD = (
    "[...d.querySelectorAll('input[type=password]')].find((i) => i.offsetParent)"
)


class Page:
    """One window's page, through anything with `evaluate_js`."""

    def __init__(self, window) -> None:
        self.window = window

    def js(self, expression: str):
        return self.window.evaluate_js(expression)

    def wait(self, expression: str, what: str, seconds: float = READY) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.js(expression):
                return
            time.sleep(0.25)
        msg = f"no {what} in {seconds} s"
        raise AssertionError(msg)

    def is_ready(self) -> bool:
        return bool(
            self.js(
                "!!(window.__libera_seen"
                " && window.__libera_seen.has('onDocumentContentReady'))"
            )
        )

    def asks_password(self) -> bool:
        return bool(self.js(inner(f"!!{PASSWORD_FIELD}")))

    def answer_password(self, password: str) -> None:
        """The editor's own dialog, as a person answers it."""
        self.js(
            inner(
                f"(() => {{ const i = {PASSWORD_FIELD};"
                f" i.value = {json.dumps(password)};"
                # Blur too: the control reads its value when the field loses the
                # focus, as a real click on OK makes it do and `click()` does not.
                " for (const type of ['input', 'change', 'blur'])"
                " i.dispatchEvent(new w.Event(type, {bubbles: true}));"
                " [...d.querySelectorAll('button')]"
                ".find((b) => b.offsetParent && b.textContent.trim() === 'OK').click();"
                " return true; })()"
            )
        )
        self.wait(inner(f"!{PASSWORD_FIELD}"), "answer to the password")

    def decline_password(self) -> None:
        """The dialog's "Close file": the window goes, with nothing to answer."""
        self.wait(inner(f"!!{PASSWORD_FIELD}"), "password dialog")
        self.js(
            inner(
                # Later, not now: GTK's evaluate_js never answers once the window
                # is gone, and the click closes it.
                "(() => { w.setTimeout(() => [...d.querySelectorAll("
                "'button[result=cancel]')].find((b) => b.offsetParent).click(), 200);"
                " return true; })()"
            )
        )
        assert self.window.events.closed.wait(20), "the window stayed open"

    def open_with(self, passwords: list[str]) -> None:
        """Until the document is ready, answering each password it must ask for:
        none at all when there are none."""
        for password in passwords:
            self.wait(
                f"({inner(f'!!{PASSWORD_FIELD}')})"
                " || window.__libera_seen?.has('onDocumentContentReady')",
                "password dialog or document",
            )
            assert self.asks_password(), "the document opened without asking"
            self.answer_password(password)
        deadline = time.monotonic() + READY
        while not self.is_ready():
            assert time.monotonic() < deadline, "the document never became ready"
            assert not self.asks_password(), "it asked for a password"
            time.sleep(0.25)

    def enter_text(self, text: str) -> None:
        self.js(
            inner(
                "(() => { w.Asc.editor.asc_enterText("
                f"[...{json.dumps(text)}].map((c) => c.codePointAt(0)));"
                " return true; })()"
            )
        )

    def editor(self, call: str) -> object:
        """A call on the editor's API."""
        return self.js(inner(f"w.Asc.editor.{call}"))

    def editor_does(self, call: str) -> None:
        """A call on the editor's API that answers nothing worth keeping, or
        something pywebview cannot carry over."""
        self.js(inner(f"(() => {{ w.Asc.editor.{call}; return true; }})()"))

    def open_signature_panel(self) -> None:
        """The bridge's panel, which is in the top page."""
        self.js(
            inner(
                "(() => { w.__chosen = null; w.Asc.editor.asc_registerCallback("
                "'on_signature_selectsertificate_ret', (c) => { w.__chosen = c; });"
                " w.AscDesktopEditor.SelectCertificate(); return true; })()"
            )
        )
        self.wait("!!document.querySelector('[data-choose=key]')", "signature panel")

    def click_choose_key(self) -> None:
        self.js("document.querySelector('[data-choose=key]').click(); true")

    def give_passphrase(self, passphrase: str) -> dict:
        """The certificate chosen, once the panel has the file and this."""
        self.js(
            "(() => { const i = document.querySelector("
            "'.libera-panel input[type=password]');"
            f" i.value = {json.dumps(passphrase)};"
            " i.dispatchEvent(new Event('input', {bubbles: true}));"
            " [...document.querySelectorAll('.libera-panel button')]"
            ".find((b) => b.textContent.trim() === 'OK').click();"
            " return true; })()"
        )
        self.wait(inner("w.__chosen !== null"), "certificate")
        return self.js(
            inner(
                "({id: w.__chosen.id || w.__chosen.asc_getId?.(),"
                " name: w.__chosen.name || w.__chosen.asc_getName?.()})"
            )
        )


def wait_until_changed(path: pathlib.Path, since: int) -> None:
    deadline = time.monotonic() + SAVED
    while path.stat().st_mtime_ns == since:
        assert time.monotonic() < deadline, f"{path.name} was not written"
        time.sleep(0.2)
    time.sleep(0.5)


# --- what a window does ------------------------------------------------------


def do_protect(page: Page, document: pathlib.Path, password: str, _key: str) -> None:
    before = document.stat().st_mtime_ns
    assert page.editor("asc_isProtectionSupport()"), "File > Protect is not offered"
    page.editor_does(f"asc_setCurrentPassword({json.dumps(password)})")
    wait_until_changed(document, before)


def do_unprotect(page: Page, document: pathlib.Path, _value: str, _key: str) -> None:
    before = document.stat().st_mtime_ns
    page.editor_does("asc_resetPassword()")
    wait_until_changed(document, before)


def do_type_and_save(page: Page, document: pathlib.Path, text: str, _key: str) -> None:
    before = document.stat().st_mtime_ns
    page.editor_does("asc_MoveCursorToEndPos?.()")
    page.enter_text(" " + text)
    time.sleep(1)
    page.editor_does("asc_Save()")
    wait_until_changed(document, before)


def see_the_real_file_dialog_and_cancel_it(page: Page) -> None:
    """It comes up, from a request's thread, and going away leaves the panel as it
    was. Picking a file in it is what this cannot do: a ⌘⇧G sent to AppKit from
    inside the process opened no Go to Folder, on 2026-11-05."""
    from AppKit import NSApplication, NSModalPanelRunLoopMode, NSOpenPanel

    def panels() -> list:
        return [
            window
            for window in NSApplication.sharedApplication().windows()
            if window.isKindOfClass_(NSOpenPanel) and window.isVisible()
        ]

    page.click_choose_key()
    deadline = time.monotonic() + 30
    while not panels():
        assert time.monotonic() < deadline, "the file dialog did not come up"
        time.sleep(0.2)
    time.sleep(0.5)
    panels()[0].performSelectorOnMainThread_withObject_waitUntilDone_modes_(
        "cancel:", None, False, [NSModalPanelRunLoopMode]
    )
    deadline = time.monotonic() + 30
    while panels():
        assert time.monotonic() < deadline, "the file dialog did not go away"
        time.sleep(0.2)
    time.sleep(1)  # choose-file answers that nothing was chosen.
    assert page.js("!!document.querySelector('[data-choose=key]')"), "the panel went"


def do_sign(page: Page, document: pathlib.Path, passphrase: str, key: str) -> None:
    from libera.host import hooks

    page.open_signature_panel()
    # Only AppKit's can be found and cancelled from inside the process.
    if sys.platform == "darwin":
        see_the_real_file_dialog_and_cancel_it(page)
    hooks.shell.choose_open_path = lambda _kind: key
    page.click_choose_key()
    time.sleep(1)  # choose-file answers, and the panel fills in the name.
    chosen = page.give_passphrase(passphrase)
    before = document.stat().st_mtime_ns
    page.editor_does(f"asc_Sign({json.dumps(chosen['id'])})")
    page.wait(inner("w.Asc.editor.asc_getSignatures().length === 1"), "signature")
    wait_until_changed(document, before)


def do_shows_signature(page: Page, _document: pathlib.Path, signer: str, _key: str):
    page.wait(inner("w.Asc.editor.asc_getSignatures().length === 1"), "signature")
    found = page.js(
        inner(
            "(() => { const s = w.Asc.editor.asc_getSignatures()[0];"
            " return [s.asc_getValid(), s.asc_getSigner1()]; })()"
        )
    )
    assert found == [0, signer], found
    assert page.editor("isRestrictionSignatures()"), "a signed document is read-only"


def do_remove_signature(page: Page, _document, _value: str, _key: str) -> None:
    page.wait(inner("w.Asc.editor.asc_getSignatures().length === 1"), "signature")
    page.editor_does("asc_RemoveAllSignatures()")
    page.wait(inner("w.Asc.editor.asc_getSignatures().length === 0"), "removal")
    assert not page.editor("isRestrictionSignatures()"), "still read-only"


STEPS: dict[str, Callable] = {
    "protect": do_protect,
    "unprotect": do_unprotect,
    "type-and-save": do_type_and_save,
    "sign": do_sign,
    "shows-signature": do_shows_signature,
    "remove-signature": do_remove_signature,
}


def wait_for_opening_password(session: Session, password: str) -> None:
    """A PDF: the editor reports what it opened it with, and only then can its
    password be changed (bridge-desktop, reportOpeningPassword)."""
    deadline = time.monotonic() + SAVED
    while session.opened_with != password:
        assert time.monotonic() < deadline, "the PDF's password never came back"
        time.sleep(0.2)


def run_window(plan: dict) -> None:
    """One window, in this process: the application on the main thread, as the
    CLI runs it, and the steps on this one."""
    import webview
    import webview.errors

    from libera.host import app, session as sessions
    from libera.payload import locate

    document = pathlib.Path(plan["document"])
    result = pathlib.Path(plan["result"])

    def drive() -> None:
        deadline = time.monotonic() + READY
        while not webview.windows:
            assert time.monotonic() < deadline, "no window"
            time.sleep(0.1)
        page = Page(webview.windows[0])
        if plan["decline"]:
            page.decline_password()
            return
        page.open_with(plan["passwords"])
        if document.suffix == ".pdf" and plan["passwords"]:
            session = next(iter(sessions.SESSIONS.values()))
            wait_for_opening_password(session, plan["passwords"][-1])
        for name, value in plan["steps"]:
            STEPS[name](page, document, value, plan.get("key", ""))

    def steps() -> None:
        outcome = {"ok": True, "said": ""}
        try:
            drive()
        except (AssertionError, webview.errors.JavascriptException) as e:
            outcome = {"ok": False, "said": f"{type(e).__name__}: {e}"}
        result.write_text(json.dumps(outcome), encoding="utf-8")
        # Its lock goes, as closing the window lets it go. A window closed in the
        # ordinary way is the gui tier's.
        app._let_go_of_everything()
        os._exit(0)

    driver = threading.Thread(target=steps, daemon=True)
    driver.start()
    app.run(
        locate.resolve().root,
        pathlib.Path(plan["home"]) / "sessions",
        [document],
    )
    # Off a Mac the last window's closing ends `run`, before `steps` has said so.
    driver.join()


# --- from outside ------------------------------------------------------------


@dataclass
class Run:
    work: pathlib.Path
    payload: pathlib.Path
    windows: int = 0

    def window(
        self,
        document: pathlib.Path,
        passwords: tuple[str, ...] = (),
        steps: tuple[tuple[str, str], ...] = (),
        key: pathlib.Path | None = None,
        decline: bool = False,
    ) -> None:
        """Open a real window on `document`, answer its passwords, do the steps."""
        self.windows += 1
        here = self.work / f"window-{self.windows}"
        home = here / "home"
        home.mkdir(parents=True)
        result = here / "result.json"
        plan = {
            "document": str(document),
            "passwords": list(passwords),
            "steps": list(steps),
            "result": str(result),
            "home": str(home),
            "key": str(key) if key else "",
            "decline": decline,
        }
        log = here / "libera.log"
        with log.open("wb") as output:
            process = subprocess.run(
                [sys.executable, __file__, json.dumps(plan)],
                check=False,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=WINDOW_BUDGET,
                env={**os.environ, **window_env(home, self.payload)},
            )
        if not result.is_file():
            tail = log.read_text(encoding="utf-8", errors="replace")[-600:]
            msg = f"the window died ({process.returncode}): {tail}"
            raise AssertionError(msg)
        said = json.loads(result.read_text(encoding="utf-8"))
        assert said["ok"], f"{document.name}: {said['said']}"


if __name__ == "__main__":
    run_window(json.loads(sys.argv[1]))
