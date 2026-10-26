"""What puts Libera Suite where the desktop looks for applications.

`libera --launcher-install` and `--launcher-remove`, for an install that gave
only a command: `pipx`, `uv tool`, `pip`, Homebrew. On Linux a desktop entry
(`desktop`), on macOS a `Libera.app` in ~/Applications (`macos`); Windows has
its installer and the Flatpak its own entry, and `explain_unsupported` says so.
The platform is chosen here, once; the rest of the program calls this module.
"""

from __future__ import annotations

import sys

if sys.platform == "darwin":
    from libera.launcher.macos import (
        explain_unsupported,
        get_entry_path,
        install,
        is_installed,
        remove,
    )
else:
    from libera.launcher.desktop import (
        explain_unsupported,
        get_entry_path,
        install,
        is_installed,
        remove,
    )

__all__ = [
    "explain_unsupported",
    "get_entry_path",
    "install",
    "is_installed",
    "remove",
]
