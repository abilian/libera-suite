"""The frozen application's entry point: Libera.exe, and libera-cli.exe beside it.

Two executables over one frozen tree, differing only in whether Windows gives
them a console. Libera.exe is what the Start menu, the desktop and a
double-clicked document run; libera-cli.exe is the same program for a
terminal, and what the installer runs to set up the payload so that its
output can be read.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import sys
from pathlib import Path

# The same identity the installer gives its shortcuts. Windows groups taskbar
# buttons, and decides what a pinned icon launches, by this string: without
# it, a window of ours would group under whichever process drew it, and a pin
# would point at that.
APP_ID = "eu.liberasuite.Libera"

# A log that grows on every launch has to stop somewhere.
LOG_LIMIT = 2 * 1024 * 1024


def _streams_for_a_windowed_process() -> None:
    """Give a process with no console somewhere to write.

    A windowed executable starts with sys.stdout and sys.stderr set to None,
    and the first print() -- or the logging handler the CLI installs on
    stderr -- then raises AttributeError, which with no console to show it in
    is a double-click that does nothing at all. So both go to a file the user
    can be pointed at.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Libera Suite"
    base.mkdir(parents=True, exist_ok=True)
    log = base / "libera.log"
    with contextlib.suppress(OSError):
        if log.stat().st_size > LOG_LIMIT:
            log.replace(log.with_suffix(".log.old"))
    stream = log.open("a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or stream
    sys.stderr = sys.stderr or stream


def _identify() -> None:
    with contextlib.suppress(Exception):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


if __name__ == "__main__":
    _streams_for_a_windowed_process()
    _identify()

    from libera import main

    sys.exit(main())
