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
