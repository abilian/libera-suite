"""Word for Mac and Libera read each other's protected files.

These start Word, and stop it after each script, so they skip while it is open. The
first run has macOS ask leave for Terminal to control it. Whether Word calls a
signature valid is not here, since its scripting on a Mac has no signatures: Office on
Windows answers, in test_office_signatures.py.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

import pytest
from support.protected import SECRET, SENTENCE, is_encrypted, make_protected

from libera.host import apps

from .conftest import signed_document

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .driver import Run

WORD = pathlib.Path("/Applications/Microsoft Word.app")
# Word is sandboxed: anywhere else, opening a file puts up a dialog asking for access.
# Read here, before a test's home takes the place of the real one.
WORD_FOLDER = (
    pathlib.Path.home() / "Library/Containers/com.microsoft.Word/Data/libera-check"
)
WORD_PASSWORD = "zqx-Word-Pass-7"
WORD_SENTENCE = "Word wrote this sentence, zqx-word-sentence."
MARK = "zqx-typed-4471"

pytestmark = pytest.mark.skipif(not WORD.is_dir(), reason="no Word for Mac here")


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


@pytest.fixture
def word_folder() -> Iterator[pathlib.Path]:
    if word_is_running():
        pytest.skip("Word is open, and these stop it")
    WORD_FOLDER.mkdir(parents=True, exist_ok=True)
    yield WORD_FOLDER
    if not word_is_running():
        shutil.rmtree(WORD_FOLDER, ignore_errors=True)


def test_a_file_word_protected_is_edited_here_and_read_back(
    run: Run, word_folder: pathlib.Path
) -> None:
    made = word_folder / "encrypted-by-word.docx"
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


def test_word_reads_a_file_protected_here(run: Run, word_folder: pathlib.Path) -> None:
    ours = make_protected(apps.WORDS, "docx", run.work / "for-word")
    copy = word_folder / "encrypted-by-libera.docx"
    shutil.copyfile(ours, copy)
    shown = word_reads(copy, SECRET)
    assert SENTENCE in shown, f"Word read: {shown!r}"
    assert word_refuses(copy, "not it"), "Word opened it with a wrong password"


def test_word_reads_a_file_signed_here(run: Run, word_folder: pathlib.Path) -> None:
    signed = signed_document(run, "signed-for-word")
    copy = word_folder / "signed-by-libera.docx"
    shutil.copyfile(signed, copy)
    shown = word_reads(copy)
    assert SENTENCE in shown, f"Word read: {shown!r}"
