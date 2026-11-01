"""The bits of the host that talk to the desktop: opener, file manager, account."""

from __future__ import annotations

import contextlib
import functools
import getpass
import logging
import os
import pathlib
import shutil
import subprocess
import sys

from libera.payload import locate

logger = logging.getLogger(__name__)

# Long enough to be sure a fast failure has happened (0.03s on the desktop this
# was measured on), short enough that a caller is not held up by a browser that
# will outlive it.
OPEN_TIMEOUT = 5.0


def choose_opener() -> list[str]:
    """The command this desktop opens things with."""
    return ["/usr/bin/open"] if sys.platform == "darwin" else ["xdg-open"]


def open_url(url: str) -> bool:
    """Hand a URL to the desktop, and say whether the desktop took it.

    **Not `webbrowser.open`**, whose return value does not mean what it looks
    like. On Linux it ends in `BackgroundBrowser.open`, which spawns the
    command and returns `p.poll() is None` -- true whenever the process has not
    exited in the instant since it started, which is always. So it reported
    success for `xdg-open` exiting 3 with no handler, while Help appeared to do
    nothing at all and said nothing about it.

    Waiting is the point, though the wait has to be bounded. Measured on a Fedora
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
    return _run_opener([*choose_opener(), url])


def _run_opener(cmd: list[str]) -> bool:
    """Run the desktop's opener on `cmd[-1]`, and say whether it took it.

    The bounded wait open_url describes, for every caller: a URL, a file to
    reveal, a PDF to print. Revealing and printing used `subprocess.run`
    and ignored the status, so on Linux either could hold its request
    thread for as long as the file manager or viewer stayed open, and both
    reported success whatever the opener said.
    """
    target = cmd[-1]
    proc = subprocess.Popen(cmd)  # our own argv; callers check the target
    try:
        status = proc.wait(timeout=OPEN_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.info("open -> %s (the opener is still running)", target)
        return True
    # In `else`, which is where code that needs the try to have succeeded goes.
    # It was after the block and just as correct, but pyrefly checking for
    # Windows, where all of this sits behind an early return, reported
    # `status` as possibly unbound there and does not in `else`.
    else:
        if status == 0:
            logger.info("open -> %s", target)
            return True
        logger.warning("open: %s exited %d for %s", cmd[0], status, target)
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
    disk yet: a document that has never been saved has a name and no file.
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
        # nothing. It exits 1 whether or not it worked, so its status means
        # nothing.
        subprocess.run(["explorer", f"/select,{target}"], check=False)
        return True
    if sys.platform == "darwin":
        select_flag = ["-R"] if select else []
        return _run_opener([*choose_opener(), *select_flag, str(target)])
    # xdg-open has no "select": the folder is the closest it comes.
    return _run_opener([*choose_opener(), str(target.parent if select else target)])


def open_externally(path: pathlib.Path) -> bool:
    """Hand a file to whatever the desktop opens it with, and say if it did.

    Printing ends here. Upstream's host draws its own print preview; ours hands
    the PDF to Preview (or the Linux equivalent), which has a print dialog and
    did not have to be written. On Windows, to whatever opens PDFs -- Edge, on
    a machine no one has changed.
    """
    if sys.platform == "win32":
        return _start(str(path))
    return _run_opener([*choose_opener(), str(path)])


def replace_file(new: pathlib.Path, target: pathlib.Path) -> None:
    """Put `new` in `target`'s place in one step, keeping what `target` was.

    A rename alone gives the document the new file's metadata: its Finder tags
    and other extended attributes gone, its permissions the new file's. Each
    system has a call for a safe save that keeps them, and this is the one
    place that knows which: NSFileManager's replaceItemAtURL on macOS, which
    is what NSDocument saves with, and ReplaceFileW on Windows. Linux has
    none, so the attributes are copied across before the rename. `new` must be
    on the same volume as `target`; it is gone afterwards.
    """
    if not target.exists():
        new.replace(target)
        return
    if sys.platform == "darwin":
        import Foundation

        replaced, _, error = (
            Foundation.NSFileManager.defaultManager().replaceItemAtURL_withItemAtURL_backupItemName_options_resultingItemURL_error_(
                Foundation.NSURL.fileURLWithPath_(str(target)),
                Foundation.NSURL.fileURLWithPath_(str(new)),
                None,
                0,
                None,
                None,
            )
        )
        if not replaced:
            msg = f"could not replace {target}: {error}"
            raise OSError(msg)
    elif sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ignore_merge_errors = 0x2  # REPLACEFILE_IGNORE_MERGE_ERRORS
        if not kernel32.ReplaceFileW(
            str(target), str(new), None, ignore_merge_errors, None, None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        shutil.copymode(target, new)
        if sys.platform == "linux":
            _copy_xattrs(target, new)
        new.replace(target)


def _copy_xattrs(source: pathlib.Path, dest: pathlib.Path) -> None:
    """The extended attributes `dest` can take, ACLs included, as shutil does
    for copystat: a file system without them has nothing to copy, and one the
    user may not set (security.*) is left behind."""
    if sys.platform == "linux":
        with contextlib.suppress(OSError):
            for name in os.listxattr(source):
                with contextlib.suppress(OSError):
                    os.setxattr(dest, name, os.getxattr(source, name))


@functools.cache
def lookup_local_user() -> tuple[str, str]:
    """Who the editor should say you are: (id, name).

    Without this the editor uses upstream's placeholder, "Chuk.Gek": an odd
    face in the corner, and also the author recorded against every tracked
    change, which goes into the saved file. Measured: a docx saved after one
    tracked edit contains w:author="Chuk.Gek".

    The full name is what other people see, so prefer it; the login name is the
    stable identity behind it. `user_name` in config.toml comes before both,
    for a document that has to go out under another name than the account's;
    the id stays the login, which is what a lock file is recognised by.
    """
    # Each lookup narrowed to how it says "no answer": a wider net would also
    # catch a typo here, and sign every tracked change "user".
    login = "user"
    # OSError since 3.13; KeyError and ImportError from its pwd fallback before.
    with contextlib.suppress(OSError, KeyError, ImportError):
        login = getpass.getuser()

    full = (locate.read_config_string("user_name") or "").strip()
    if full:
        return login, full
    if sys.platform == "darwin":
        with contextlib.suppress(ImportError):
            import Foundation

            full = str(Foundation.NSFullUserName())
    if not full and sys.platform == "win32":
        full = _lookup_windows_full_name(login)
    # Not on Windows, and not only because the lookup would fail: `pwd` does not
    # exist there, so this used to run by way of a swallowed ModuleNotFoundError;
    # a checker for win32 reports it as the unresolved attribute it is.
    if not full and sys.platform != "win32":
        with contextlib.suppress(KeyError):
            import pwd

            # The gecos field is the full name on every Unix that sets one,
            # with optional comma-separated extras after it.
            full = pwd.getpwnam(login).pw_gecos.split(",")[0]
    return login, (full.strip() or login)


def _lookup_windows_full_name(login: str) -> str:
    """The display name Windows shows for this account, or "".

    Two sources, because each answers for one kind of account: GetUserNameExW
    with NameDisplay asks the domain, and fails with ERROR_NONE_MAPPED on a
    local account; NetUserGetInfo reads the local account database, which is
    where a home machine's "Full name" lives.
    """
    # A block, not an early return: see _start.
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        # OSError for a DLL that will not load, AttributeError for a function
        # it does not export: how ctypes says either.
        with contextlib.suppress(OSError, AttributeError):
            size = wintypes.ULONG(256)
            buf = ctypes.create_unicode_buffer(size.value)
            name_display = 3  # EXTENDED_NAME_FORMAT.NameDisplay
            found = ctypes.windll.secur32.GetUserNameExW(
                name_display, buf, ctypes.byref(size)
            )
            if found and buf.value.strip():
                return buf.value.strip()

        with contextlib.suppress(OSError, AttributeError):

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
