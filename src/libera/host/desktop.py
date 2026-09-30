"""The bits of the host that talk to the desktop rather than the editor."""

from __future__ import annotations

import contextlib
import functools
import getpass
import logging
import os
import pathlib
import subprocess
import sys

logger = logging.getLogger(__name__)

# Long enough to be sure a fast failure has happened (0.03s on the desktop this
# was measured on), short enough that a caller is not held up by a browser that
# will outlive it.
OPEN_TIMEOUT = 5.0


def opener() -> list[str]:
    """The command this desktop opens things with."""
    return ["/usr/bin/open"] if sys.platform == "darwin" else ["xdg-open"]


def open_url(url: str) -> bool:
    """Hand a URL to the desktop, and say whether the desktop took it.

    **Not `webbrowser.open`**, whose return value does not mean what it looks
    like. On Linux it ends in `BackgroundBrowser.open`, which spawns the
    command and returns `p.poll() is None` -- true whenever the process has not
    exited in the instant since it started, which is always. So it reported
    success for `xdg-open` exiting 3 with no handler, and Help appeared to do
    nothing at all rather than saying so.

    Waiting is the point, and it has to be a bounded wait. Measured on a Fedora
    desktop:

        nothing can open it   exit 3, in 0.03s
        it opens              never exits -- xdg-open stays attached to the
                              browser it started, still running at 25s

    So a plain `subprocess.run` blocks for as long as the browser lives, which
    is why the bridge's open-url endpoint used to hang its request thread. A
    short wait separates the two cleanly: a failure is immediate, and anything
    still running has been taken. The child is left alone on timeout, because
    killing it would close the browser that was just opened.
    """
    if sys.platform == "win32":
        return _start(url)
    cmd = [*opener(), url]
    proc = subprocess.Popen(cmd)  # our own argv; callers check the url
    try:
        status = proc.wait(timeout=OPEN_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.info("open-url -> %s (the opener is still running)", url)
        return True
    # In `else`, which is where code that needs the try to have succeeded goes.
    # It was after the block and just as correct, but pyrefly checking for
    # Windows, where all of this sits behind the early return above, reported
    # `status` as possibly unbound there and does not in `else`.
    else:
        if status == 0:
            logger.info("open-url -> %s", url)
            return True
        logger.warning("open-url: %s exited %d for %s", cmd[0], status, url)
        return False


def _start(target: str) -> bool:
    """Windows' own "open this": the registered handler, or an OSError.

    `os.startfile` is ShellExecute, which returns once the handler has been
    started and raises when there is none, so the answer the POSIX side waits
    five seconds for arrives here straight away. There is no command to spell
    either: `start` is a cmd builtin, not a program.
    """
    # The platform test is for the type checkers as much as for the runtime:
    # every caller already tests for win32, but a checker for another platform
    # cannot see a guard in the caller. It has to be a block and not an early
    # return, because pyrefly narrows on the first and not on the second, and
    # `make lint` runs all three checkers for all three platforms.
    if sys.platform == "win32":
        try:
            os.startfile(target)
        except OSError as e:
            logger.warning("open: nothing opened %s (%s)", target, e)
            return False
        logger.info("open -> %s", target)
        return True
    return False


def reveal(path: pathlib.Path) -> bool:
    """Show a file in the platform's file manager.

    The button is labelled "Open File Location", so that is what it does. Note
    the native app does *nothing* here for a local document: its go:folder
    handler is an empty block when the parameter is "offline", because the
    button is a relabelled "Go to Documents" that navigated to the cloud portal.

    Falls back to opening the containing folder when the file itself is not on
    disk yet -- a document that has never been saved has a name but no file.
    """
    if path.is_file():
        target, select = path, True
    elif path.parent.is_dir():
        target, select = path.parent, False
    else:
        return False

    if sys.platform == "win32":
        if not select:
            return _start(str(target))
        # One argument, comma included: Explorer parses its own command line,
        # and "/select," followed by the path as a separate word selects
        # nothing. It exits 1 whether or not it worked, so there is no status
        # worth reading.
        subprocess.run(["explorer", f"/select,{target}"], check=False)
        return True
    if sys.platform == "darwin":
        cmd = (
            ["/usr/bin/open", "-R", str(target)]
            if select
            else ["/usr/bin/open", str(target)]
        )
    else:
        cmd = ["xdg-open", str(target if not select else target.parent)]
    subprocess.run(cmd, check=False)
    return True


def open_externally(path: pathlib.Path) -> None:
    """Hand a file to whatever the desktop opens it with.

    Printing ends here. Upstream's host draws its own print preview; ours hands
    the PDF to Preview (or the Linux equivalent), which has a print dialog and
    did not have to be written. On Windows, to whatever opens PDFs -- Edge, on
    a machine nobody has changed.
    """
    if sys.platform == "win32":
        _start(str(path))
        return
    cmd = (
        ["/usr/bin/open", str(path)]
        if sys.platform == "darwin"
        else ["xdg-open", str(path)]
    )
    subprocess.run(cmd, check=False)
    logger.info("print -> %s", path)


@functools.cache
def local_user() -> tuple[str, str]:
    """Who the editor should say you are: (id, name).

    Without this the editor uses upstream's placeholder, "Chuk.Gek", and that
    is not only an odd face in the corner -- it is the author recorded against
    every tracked change, and it goes into the saved file. Measured: a docx
    saved after one tracked edit carries w:author="Chuk.Gek".

    The full name is what other people see, so prefer it; the login name is the
    stable identity behind it.
    """
    login = "user"
    with contextlib.suppress(Exception):
        login = getpass.getuser()

    full = ""
    if sys.platform == "darwin":
        with contextlib.suppress(Exception):
            import Foundation

            full = str(Foundation.NSFullUserName())
    if not full and sys.platform == "win32":
        full = _windows_full_name(login)
    # Not on Windows, and not only because the lookup would fail: `pwd` does not
    # exist there, so this used to run by way of a swallowed ModuleNotFoundError,
    # and a checker for win32 reports it as the unresolved attribute it is.
    if not full and sys.platform != "win32":
        with contextlib.suppress(Exception):
            import pwd

            # The gecos field is the full name on every Unix that sets one,
            # with optional comma-separated extras after it.
            full = pwd.getpwnam(login).pw_gecos.split(",")[0]
    return login, (full.strip() or login)


def _windows_full_name(login: str) -> str:
    """The display name Windows shows for this account, or "".

    Two sources, because each answers for one kind of account: GetUserNameExW
    with NameDisplay asks the domain, and fails with ERROR_NONE_MAPPED on a
    local account; NetUserGetInfo reads the local account database, which is
    where a home machine's "Full name" lives.
    """
    # For the type checkers as much as the runtime: every caller tests for
    # win32, and a checker for another platform cannot see that. A block and
    # not an early return, because pyrefly narrows on the first only. See
    # _start in desktop.py.
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        with contextlib.suppress(Exception):
            size = wintypes.ULONG(256)
            buf = ctypes.create_unicode_buffer(size.value)
            name_display = 3  # EXTENDED_NAME_FORMAT.NameDisplay
            found = ctypes.windll.secur32.GetUserNameExW(
                name_display, buf, ctypes.byref(size)
            )
            if found and buf.value.strip():
                return buf.value.strip()

        with contextlib.suppress(Exception):

            class UserInfo10(ctypes.Structure):
                _fields_ = [
                    ("name", wintypes.LPWSTR),
                    ("comment", wintypes.LPWSTR),
                    ("usr_comment", wintypes.LPWSTR),
                    ("full_name", wintypes.LPWSTR),
                ]

            info = ctypes.POINTER(UserInfo10)()
            netapi = ctypes.windll.netapi32
            if netapi.NetUserGetInfo(None, login, 10, ctypes.byref(info)) == 0:
                try:
                    return (info.contents.full_name or "").strip()
                finally:
                    netapi.NetApiBufferFree(info)
        return ""
    return ""
