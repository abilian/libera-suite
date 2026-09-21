"""The libera command line.

    commands   one function per thing libera can be asked to do
    dispatch   the argument parser, and which command each spelling reaches

`main` is the console script named in pyproject.toml, so it is re-exported
here and `libera.cli.main` still resolves.
"""

from __future__ import annotations

from libera.cli.dispatch import main

__all__ = ["main"]
