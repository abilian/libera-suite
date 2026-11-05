"""The Mac's hand checks: real windows, in the engine that ships here, and Word.

    make check-mac                 all of it, about five minutes
    make check-mac ONLY=word       one of: document, declined, pdf, signature, word

Not in any test tier, because it takes over the screen: each step opens a real
window, and the Word steps start Word, which the first run has macOS ask leave for.
Playwright cannot do this: its WebKit hangs on macOS 14 (tests/c_e2e/host/conftest.py),
and it is not WKWebView in any case.

The page is driven from inside the application's process: each window is a process
of this script, with a home of its own, that runs `app.run` on its main thread as
the CLI does and the steps on another, through pywebview's `evaluate_js`. So the
window, the engine, the bridge and the host are the real ones. Three things are not:

- The file dialog of the signature panel is checked to come up, then cancelled, and
  the file answered for it (`choose_open_path`): a script cannot pick a file in one.
- Text is entered through the editor's API, not typed, and a Save or File > Protect
  called as the menu item calls it.
- Whether Word calls a signature valid: its scripting on a Mac has no signatures.
  Office on Windows answers, in tests/d_gui/test_office_signatures.py.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from libera.host.session import Session

# Run as a script, this is not the package it is in.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

WINDOW_BUDGET = 180
READY = 120
SAVED = 60
NEW = "zqx-New-Pass-9"
CHANGED = "zqx-Changed-Pass-3"
WORD_PASSWORD = "zqx-Word-Pass-7"
WORD_SENTENCE = "Word wrote this sentence, zqx-word-sentence."
MARK = "zqx-typed-4471"
REAL_HOME = pathlib.Path.home()
WORD = pathlib.Path("/Applications/Microsoft Word.app")
# Word is sandboxed: anywhere else, opening a file puts up a dialog asking for access.
WORD_FOLDER = REAL_HOME / "Library/Containers/com.microsoft.Word/Data/libera-check"


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


# --- the checks, from outside -------------------------------------------------


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
                [sys.executable, __file__, "--window", json.dumps(plan)],
                check=False,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=WINDOW_BUDGET,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "LIBERA_PAYLOAD": str(self.payload),
                },
            )
        if not result.is_file():
            tail = log.read_text(encoding="utf-8", errors="replace")[-600:]
            msg = f"the window died ({process.returncode}): {tail}"
            raise AssertionError(msg)
        said = json.loads(result.read_text(encoding="utf-8"))
        assert said["ok"], f"{document.name}: {said['said']}"


def check_document(run: Run) -> None:
    from libera.host import apps
    from support.protected import is_encrypted, make_protected

    plain = make_protected(apps.WORDS, "docx", run.work / "document", password="")
    run.window(plain, steps=(("protect", NEW),))
    assert is_encrypted(plain), "File > Protect left it in the clear"
    run.window(plain, passwords=("not it", NEW))
    run.window(plain, passwords=(NEW,), steps=(("protect", CHANGED),))
    run.window(plain, passwords=(NEW, CHANGED))
    run.window(plain, passwords=(CHANGED,), steps=(("unprotect", ""),))
    assert not is_encrypted(plain), "the password stayed"
    run.window(plain)


def check_declined(run: Run) -> None:
    from libera.host import apps
    from support.protected import make_protected

    protected = make_protected(apps.WORDS, "docx", run.work / "document")
    run.window(protected, decline=True)


def check_pdf(run: Run) -> None:
    from support.paths import repo_root
    from support.protected import pdf_opens_with

    pdf = run.work / "Protected.pdf"
    shutil.copyfile(repo_root() / "build/engine/smoke-pdf/protected.pdf", pdf)
    run.window(pdf, passwords=("not it", "secret"), steps=(("protect", NEW),))
    assert pdf_opens_with(pdf, NEW), "the new password does not open it"
    assert not pdf_opens_with(pdf, "secret"), "the old one still does"
    run.window(pdf, passwords=("secret", NEW))
    run.window(pdf, passwords=(NEW,), steps=(("unprotect", ""),))
    assert b"/Encrypt" not in pdf.read_bytes(), "the password stayed"
    run.window(pdf)
    run.window(pdf, steps=(("protect", NEW),))
    assert pdf_opens_with(pdf, NEW), "a password added does not open it"


def signed_document(run: Run, folder: str) -> pathlib.Path:
    from libera.host import apps, saving
    from support.keys import PASSPHRASE, make_pkcs12
    from support.protected import make_protected

    plain = make_protected(apps.WORDS, "docx", run.work / folder, password="")
    key = make_pkcs12(run.work / folder / "keys")
    run.window(plain, steps=(("sign", PASSPHRASE),), key=key)
    assert saving.is_signed(plain), "the file has no signature"
    return plain


def check_signature(run: Run) -> None:
    from libera.host import saving
    from support.keys import SIGNER

    signed = signed_document(run, "signature")
    run.window(signed, steps=(("shows-signature", SIGNER),))
    run.window(signed, steps=(("remove-signature", ""),))
    assert not saving.is_signed(signed), "the signature stayed in the file"


def stop_word() -> None:
    """Word 16.95 closes no document for a script, however asked (-1708), and quits
    only with none open ("User cancelled", -128), measured on 2026-11-05. So it is
    stopped, with nothing unsaved in it, read only or saved. Its error reporter then
    says so in a dialog, "A Force Quit was performed", whose OK starts Word again;
    stopping that too takes the dialog away and leaves Word gone."""
    subprocess.run(["pkill", "-TERM", "-x", "Microsoft Word"], check=False)
    deadline = time.monotonic() + 20
    # The reporter comes about three seconds after, and Word waits for it.
    settled = 0
    while settled < 12 and time.monotonic() < deadline:
        # By its path: `-x` reads a name cut to 16 characters, and this has 25.
        reporter = subprocess.run(
            ["pkill", "-TERM", "-f", "Microsoft Error Reporting.app"],
            check=False,
            capture_output=True,
        )
        settled = 0 if reporter.returncode == 0 or word_is_running() else settled + 1
        time.sleep(0.25)
    if word_is_running():
        # Stuck on a dialog, a Word does not hear the first: nothing of anyone's is in
        # it, since these only start when it is not running.
        subprocess.run(["pkill", "-KILL", "-x", "Microsoft Word"], check=False)
        time.sleep(2)
        subprocess.run(
            ["pkill", "-TERM", "-f", "Microsoft Error Reporting.app"],
            check=False,
            capture_output=True,
        )
    # What a Word that was stopped leaves beside each file, and which holds up the
    # next Word's opening it: it never answered a script again, on 2026-11-05.
    for lock in WORD_FOLDER.glob("~$*"):
        lock.unlink()


def word_script(script: str, *argv: str) -> subprocess.CompletedProcess[str]:
    """AppleScript for a Word that was not running, then stopped."""
    try:
        return subprocess.run(
            ["osascript", "-e", script, *argv],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
    finally:
        stop_word()


def word_is_running() -> bool:
    found = subprocess.run(
        ["pgrep", "-x", "Microsoft Word"], check=False, capture_output=True
    )
    return found.returncode == 0


WORD_ENCRYPTS = """
on run argv
    with timeout of 75 seconds
        tell application "Microsoft Word"
            set d to make new document
            insert text (item 3 of argv) at text object of d
            save as d file name (item 1 of argv) file format format document ¬
                password (item 2 of argv) add to recent files false
        end tell
    end timeout
end run
"""

WORD_READS = """
on run argv
    with timeout of 75 seconds
        tell application "Microsoft Word"
            if (count of argv) > 1 then
                open file name (item 1 of argv) password document (item 2 of argv) ¬
                    read only true add to recent files false
            else
                open file name (item 1 of argv) read only true add to recent files false
            end if
            return content of text object of active document
        end tell
    end timeout
end run
"""


def word_reads(path: pathlib.Path, *password: str) -> str:
    """What Word shows in a file, which has to be in its folder. It refusing is a
    failure here: `word_refuses` is for when it should."""
    done = word_script(WORD_READS, str(path), *password)
    assert done.returncode == 0, f"Word on {path.name}: {done.stderr.strip()}"
    return done.stdout


def word_refuses(path: pathlib.Path, password: str) -> bool:
    return word_script(WORD_READS, str(path), password).returncode != 0


def check_word(run: Run) -> None:
    from libera.host import apps
    from support.protected import SECRET, SENTENCE, is_encrypted, make_protected

    if not WORD.is_dir():
        msg = "Word is not installed"
        raise NotHereError(msg)
    if word_is_running():
        msg = "Word is running, and these stop it: close it and run this again"
        raise NotHereError(msg)
    WORD_FOLDER.mkdir(parents=True, exist_ok=True)
    try:
        made = WORD_FOLDER / "encrypted-by-word.docx"
        done = word_script(WORD_ENCRYPTS, str(made), WORD_PASSWORD, WORD_SENTENCE)
        assert made.is_file(), f"Word did not save: {done.stderr}"
        assert is_encrypted(made), "Word's file is not encrypted"
        run.window(
            made,
            passwords=("not it", WORD_PASSWORD),
            steps=(("type-and-save", MARK),),
        )
        assert is_encrypted(made), "the save took the password off"
        shown = word_reads(made, WORD_PASSWORD)
        assert WORD_SENTENCE in shown, f"Word read: {shown!r}"
        # Less its first letter: after a full stop the editor capitalises it.
        assert MARK[1:] in shown, f"Word read: {shown!r}"
        assert word_refuses(made, "not it"), "Word opened it with a wrong password"

        ours = make_protected(apps.WORDS, "docx", run.work / "for-word")
        copy = WORD_FOLDER / "encrypted-by-libera.docx"
        shutil.copyfile(ours, copy)
        shown = word_reads(copy, SECRET)
        assert SENTENCE in shown, f"Word read: {shown!r}"
        assert word_refuses(copy, "not it"), "Word opened it with a wrong password"

        signed = signed_document(run, "signed-for-word")
        copy = WORD_FOLDER / "signed-by-libera.docx"
        shutil.copyfile(signed, copy)
        shown = word_reads(copy)
        assert SENTENCE in shown, f"Word read: {shown!r}"
    finally:
        if not word_is_running():
            shutil.rmtree(WORD_FOLDER, ignore_errors=True)


class NotHereError(Exception):
    pass


CHECKS: dict[str, tuple[str, Callable[[Run], None]]] = {
    "document": ("File > Protect on a .docx: add, change, remove", check_document),
    "declined": ("Close file on a password dialog closes the window", check_declined),
    "pdf": ("File > Protect on a PDF: change, remove, add", check_pdf),
    "signature": ("Sign a .docx, see the signature, remove it", check_signature),
    "word": ("Word and Libera read each other's protected files", check_word),
}

BY_HAND = """
Still by hand:
  - picking a file in the signature panel's dialog, which this only opens and cancels;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", help=argparse.SUPPRESS)
    parser.add_argument("--only", choices=[*CHECKS, ""], default="")
    args = parser.parse_args()
    if args.window:
        run_window(json.loads(args.window))
        return 0
    if sys.platform != "darwin":
        print("These are the Mac's: `make test-gui` is the other platforms' tier.")
        return 2

    from libera.payload import locate

    # Before the home moves: an installed payload lives under the real one.
    payload = locate.resolve().root
    failed = 0
    print("This takes over the screen for a few minutes: windows open and close.\n")
    with tempfile.TemporaryDirectory(prefix="libera-mac-checks-") as work:
        root = pathlib.Path(work)
        # What this process opens, to make its documents, stays out of your Recent
        # list and your settings.
        os.environ["HOME"] = str(root / "home")
        (root / "home").mkdir()
        os.environ["LIBERA_PAYLOAD"] = str(payload)
        for name, (title, check) in CHECKS.items():
            if args.only and name != args.only:
                continue
            folder = root / name
            folder.mkdir()
            started = time.monotonic()
            run = Run(folder, payload)
            try:
                check(run)
            except NotHereError as e:
                print(f"SKIP  {title}: {e}")
            except (AssertionError, subprocess.TimeoutExpired) as e:
                failed += 1
                print(f"FAIL  {title}\n      {e}")
            else:
                took = time.monotonic() - started
                print(f"pass  {title} ({run.windows} windows, {took:.0f} s)")
            finally:
                from libera.host import session as sessions

                sessions.SESSIONS.clear()
    print(BY_HAND)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
