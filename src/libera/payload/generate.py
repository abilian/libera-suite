"""Building the parts of a payload that can only be built here.

Installing is not unpacking. `AllFonts.js` records absolute font paths and
`DoctRenderer.config` absolute payload paths, so both have to be produced on
this machine by running `allfontsgen` out of the payload just unpacked --
which is also why the artifacts ship font *sources* rather than the web set.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from libera.payload import locate
from libera.payload.locate import PayloadError

if TYPE_CHECKING:
    from pathlib import Path

# What allfontsgen reads, and the thumbnail scales it draws: five sizes, each
# for Latin and for East Asian names.
FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}
THUMBNAILS = 10

# The allfontsgen running now, for stop_allfontsgen.
_running: set[subprocess.Popen[str]] = set()


def generate(root: Path) -> int:
    """Produce the files that cannot be shipped, because they hold local paths.

    Runs allfontsgen over the font sources, then writes DoctRenderer.config
    beside x2t -- which is where x2t looks for it. Returns the font count,
    because allfontsgen exits 0 having found none and the caller reports it.
    """
    layout = locate.Layout(root)
    allfontsgen = layout.allfontsgen
    if not allfontsgen.is_file():
        msg = f"no allfontsgen at {allfontsgen}: the core artifact is incomplete"
        raise PayloadError(msg)

    fonts_src = layout.fonts_src
    if not fonts_src.is_dir():
        msg = f"no font sources at {fonts_src}"
        raise PayloadError(msg)

    web = layout.fonts
    images = layout.font_thumbnails
    # allfontsgen treats an existing AllFonts.js as an up-to-date cache and
    # exits 0 without writing anything, leaving an empty font directory behind.
    for stale in (layout.all_fonts, layout.web_all_fonts):
        stale.unlink(missing_ok=True)
    # And it skips every thumbnail scale whose PNG exists, so a changed font set
    # would keep the pictures of the old one in the font menu.
    for stale in images.glob("fonts_thumbnail*"):
        stale.unlink()
    shutil.rmtree(web, ignore_errors=True)
    web.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)

    run_allfontsgen(
        layout,
        f"--input={fonts_src}",
        f"--allfonts-web={layout.web_all_fonts}",
        f"--allfonts={layout.all_fonts}",
        f"--images={images}",
        f"--selection={layout.sdkjs_common / 'font_selection.bin'}",
        f"--output-web={web}",
    )
    # The counts, not the exit code: allfontsgen exits 0 having found nothing
    # when its directory walk has no live branch, and writes a well-formed
    # AllFonts.js with an empty font list. An editor built on that renders every
    # glyph as a box. The build checks the same two things (build/engine).
    found = len(list(web.iterdir()))
    sources = sum(1 for f in fonts_src.rglob("*") if f.suffix.lower() in FONT_SUFFIXES)
    # ponytail: nine in ten, because allfontsgen passes over a source it cannot
    # use (188 web fonts from 189 files, measured); a run that stopped partway
    # is far below that. An exact rule needs allfontsgen's own list.
    if found == 0 or found < sources * 9 // 10:
        msg = f"allfontsgen made {found} web fonts from {sources} in {fonts_src}"
        raise PayloadError(msg)
    # And the thumbnails, which it draws last: on Windows it once stopped at
    # the second, leaving blank names in the font menu.
    drawn = len(list(images.glob("fonts_thumbnail*.png")))
    if drawn < THUMBNAILS:
        msg = f"allfontsgen drew {drawn} of {THUMBNAILS} font thumbnails"
        raise PayloadError(msg)

    xregexp = layout.web_apps / "vendor" / "xregexp" / "xregexp-all-min.js"
    native = layout.sdkjs_common / "Native"
    layout.doctrenderer_config.write_text(
        "<Settings>\n"
        f"<file>{native / 'native.js'}</file>\n"
        f"<file>{native / 'jquery_native.js'}</file>\n"
        f"<allfonts>{layout.all_fonts}</allfonts>\n"
        f"<file>{xregexp}</file>\n"
        f"<sdkjs>{layout.sdkjs}</sdkjs>\n"
        "</Settings>\n",
        encoding="utf-8",
    )
    return found


def run_allfontsgen(layout: locate.Layout, *args: str) -> None:
    """Run the payload's allfontsgen, and raise what it said if it failed.

    Its output is kept, so a failure becomes a PayloadError that says what
    it said: check=True raised CalledProcessError, which nothing above
    catches, and threw the reason away with the captured stderr. Exiting 0
    is no proof it found anything: the caller counts what it wrote.
    """
    allfontsgen = layout.allfontsgen
    try:
        process = subprocess.Popen(
            [str(allfontsgen), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=locate.make_tool_env(layout.bin),
            creationflags=locate.NO_WINDOW,
        )
    except OSError as e:
        msg = f"could not run {allfontsgen}: {e}"
        raise PayloadError(msg) from e
    _running.add(process)
    try:
        stdout, stderr = process.communicate()
    finally:
        _running.discard(process)
    if process.returncode != 0:
        said = (stderr or stdout).strip() or "nothing"
        msg = f"allfontsgen failed (exit {process.returncode}) and said: {said}"
        raise PayloadError(msg)


def stop_allfontsgen() -> None:
    """End the allfontsgen still running, as the application quits.

    A font index builds on a daemon thread, which a quit ends; allfontsgen,
    its child, ran on, one per launch that quit before it finished: 42 were
    found at once after a benchmark. What it built was lost anyway, since
    only the thread renames it into place.
    """
    for process in list(_running):
        process.kill()
