"""The bits of the host that talk to the desktop rather than the editor."""

from __future__ import annotations

import contextlib
import functools
import getpass
import logging
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
    cmd = [*opener(), url]
    proc = subprocess.Popen(cmd)  # our own argv; callers check the url
    try:
        status = proc.wait(timeout=OPEN_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.info("open-url -> %s (the opener is still running)", url)
        return True
    if status == 0:
        logger.info("open-url -> %s", url)
        return True
    logger.warning("open-url: %s exited %d for %s", cmd[0], status, url)
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
    did not have to be written.
    """
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
    if not full:
        with contextlib.suppress(Exception):
            import pwd

            # The gecos field is the full name on every Unix that sets one,
            # with optional comma-separated extras after it.
            full = pwd.getpwnam(login).pw_gecos.split(",")[0]
    return login, (full.strip() or login)
