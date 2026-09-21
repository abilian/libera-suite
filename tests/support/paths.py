"""Where things are, found rather than counted."""

from __future__ import annotations

import pathlib


def repo_root() -> pathlib.Path:
    """The checkout.

    `Path(__file__).parents[2]` is a guess about how deeply the file that asks
    is nested, and it was wrong the moment the tests were grouped into
    per-package folders: six files broke at once. Walking up to the
    pyproject.toml cannot be wrong about that, and does not care where the
    caller sits.
    """
    here = pathlib.Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    msg = f"no pyproject.toml above {here}"
    raise RuntimeError(msg)
