"""Where things are, found rather than counted."""

from __future__ import annotations

import os
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


def build_roots() -> list[pathlib.Path]:
    """Where a build tree might be, in `build/common.sh`'s own order.

    One definition, because two lists drift: the payload fallback in the root
    conftest and the dist lookup below both need it, and a fallback that fires
    on one machine only is worse than none -- it works on the box you tried it
    on and skips in silence on the other.
    """
    roots = [os.environ["BUILD_ROOT"]] if os.environ.get("BUILD_ROOT") else []
    roots += [
        "/Volumes/T7-EXT-2T/euro-office-build",
        str(pathlib.Path.home() / "euro-office-build"),
    ]
    return [pathlib.Path(r) for r in roots]


def built_dist(version: str | None = None) -> pathlib.Path | None:
    """The release artifacts `build/dist.sh` wrote, if this checkout has any.

    Found rather than declared. This used to want `LIBERA_DIST` pointing at
    `$BUILD_ROOT/out/dist/<version>`, so the one check that looks inside a
    shipping tarball skipped on every machine that had one -- including the
    only kind of machine it was written for, a Mac whose build tree lives on an
    external volume. A check nobody remembers to enable is a check that is not
    running.

    `LIBERA_DIST` still wins when it is set, for a dist somewhere unusual.
    Otherwise the version asked for, then the most recently written, so a stale
    older dist cannot shadow a fresh one.
    """
    explicit = os.environ.get("LIBERA_DIST")
    if explicit:
        chosen = pathlib.Path(explicit)
        return chosen if chosen.is_dir() else None

    for root in build_roots():
        dists = root / "out" / "dist"
        if not dists.is_dir():
            continue
        if version and (dists / version).is_dir():
            return dists / version
        built = sorted(
            (d for d in dists.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
        )
        if built:
            return built[-1]
    return None
