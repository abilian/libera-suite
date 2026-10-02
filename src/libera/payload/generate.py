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


def generate(root: Path) -> int:
    """Produce the files that cannot be shipped, because they hold local paths.

    Runs allfontsgen over the font sources, then writes DoctRenderer.config
    beside x2t -- which is where x2t looks for it. Returns the font count,
    because allfontsgen exits 0 having found none and the caller reports it.
    """
    allfontsgen = root / "bin" / "tools" / f"allfontsgen{locate.EXE}"
    if not allfontsgen.is_file():
        msg = f"no allfontsgen at {allfontsgen}: the core artifact is incomplete"
        raise PayloadError(msg)

    fonts_src = root / "fonts-src"
    if not fonts_src.is_dir():
        msg = f"no font sources at {fonts_src}"
        raise PayloadError(msg)

    web = root / "fonts"
    images = root / "sdkjs" / "common" / "Images"
    # allfontsgen treats an existing AllFonts.js as an up-to-date cache and
    # exits 0 without writing anything, leaving an empty font directory behind.
    for stale in (root / "AllFonts.js", root / "sdkjs" / "common" / "AllFonts.js"):
        stale.unlink(missing_ok=True)
    # And it skips every thumbnail scale whose PNG exists, so a changed font set
    # would keep the pictures of the old one in the font menu.
    for stale in images.glob("fonts_thumbnail*"):
        stale.unlink()
    shutil.rmtree(web, ignore_errors=True)
    web.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)

    # Its output kept, and a failure turned into a PayloadError that says what
    # it said: check=True raised CalledProcessError, which nothing above
    # catches, and threw the reason away with the captured stderr.
    try:
        run = subprocess.run(
            [
                str(allfontsgen),
                f"--input={fonts_src}",
                f"--allfonts-web={root / 'sdkjs' / 'common' / 'AllFonts.js'}",
                f"--allfonts={root / 'AllFonts.js'}",
                f"--images={images}",
                f"--selection={root / 'sdkjs' / 'common' / 'font_selection.bin'}",
                f"--output-web={web}",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=locate.make_tool_env(root / "bin"),
            creationflags=locate.NO_WINDOW,
        )
    except OSError as e:
        msg = f"could not run {allfontsgen}: {e}"
        raise PayloadError(msg) from e
    if run.returncode != 0:
        said = (run.stderr or run.stdout).strip() or "nothing"
        msg = f"allfontsgen failed (exit {run.returncode}) and said: {said}"
        raise PayloadError(msg)
    # The count, not the exit code: allfontsgen exits 0 having found nothing when
    # its directory walk has no live branch, and writes a well-formed AllFonts.js
    # with an empty font list. An editor built on that renders every glyph as a box.
    found = len(list(web.iterdir()))
    if found == 0:
        msg = f"allfontsgen found no fonts in {fonts_src}"
        raise PayloadError(msg)

    xregexp = root / "web-apps" / "vendor" / "xregexp" / "xregexp-all-min.js"
    (root / "bin" / "DoctRenderer.config").write_text(
        "<Settings>\n"
        f"<file>{root / 'sdkjs' / 'common' / 'Native' / 'native.js'}</file>\n"
        f"<file>{root / 'sdkjs' / 'common' / 'Native' / 'jquery_native.js'}</file>\n"
        f"<allfonts>{root / 'AllFonts.js'}</allfonts>\n"
        f"<file>{xregexp}</file>\n"
        f"<sdkjs>{root / 'sdkjs'}</sdkjs>\n"
        "</Settings>\n",
        encoding="utf-8",
    )
    return found
