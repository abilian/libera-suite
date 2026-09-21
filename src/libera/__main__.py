"""`python -m libera` -- the same entry point as the `libera` command.

Libera.app's launcher uses this rather than the console script: the script
lives in a virtualenv's bin directory, which is not where the bundle can be
sure to find it, while the interpreter path is baked into the launcher.
"""

from __future__ import annotations

import sys

from libera.cli import main

if __name__ == "__main__":
    sys.exit(main())
