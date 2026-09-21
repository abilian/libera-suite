"""Building the parts of a payload that can only be built here.

Installing is not unpacking. `AllFonts.js` records absolute font paths and
`DoctRenderer.config` absolute payload paths, so both have to be produced on
this machine by running `allfontsgen` out of the payload just unpacked --
which is also why the artifacts ship font *sources* rather than the web set.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from libera.payload.locate import PayloadError

if TYPE_CHECKING:
    from pathlib import Path


def generate(root: Path, *, core_fonts: Path | None = None) -> int:
    """Produce the files that cannot be shipped, because they hold local paths.

    Runs allfontsgen over the font sources, then writes DoctRenderer.config
    beside x2t -- which is where x2t looks for it. Returns the font count,
    because allfontsgen exits 0 having found none and the caller reports it.
    """
    allfontsgen = root / "bin" / "tools" / "allfontsgen"
    if not allfontsgen.is_file():
        msg = f"no allfontsgen at {allfontsgen}: the core artifact is incomplete"
        raise PayloadError(msg)

    fonts_src = core_fonts or (root / "fonts-src")
    if not fonts_src.is_dir():
        msg = f"no font sources at {fonts_src}"
        raise PayloadError(msg)

    web = root / "fonts"
    images = root / "sdkjs" / "common" / "Images"
    # allfontsgen treats an existing AllFonts.js as an up-to-date cache and
    # exits 0 without writing anything, leaving an empty font directory behind.
    for stale in (root / "AllFonts.js", root / "sdkjs" / "common" / "AllFonts.js"):
        stale.unlink(missing_ok=True)
    shutil.rmtree(web, ignore_errors=True)
    web.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["DYLD_LIBRARY_PATH"] = str(root / "bin")
    env["LD_LIBRARY_PATH"] = str(root / "bin")
    subprocess.run(
        [
            str(allfontsgen),
            f"--input={fonts_src}",
            f"--allfonts-web={root / 'sdkjs' / 'common' / 'AllFonts.js'}",
            f"--allfonts={root / 'AllFonts.js'}",
            f"--images={images}",
            f"--selection={root / 'sdkjs' / 'common' / 'font_selection.bin'}",
            f"--output-web={web}",
        ],
        check=True,
        capture_output=True,
        env=env,
    )
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
