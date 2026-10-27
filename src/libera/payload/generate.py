"""Building the parts of a payload that are not shipped in it.

DoctRenderer.config, and running allfontsgen, whose AllFonts.js records
absolute font paths -- which is why the artifacts ship font *sources*. The
index it builds lives in the state folder (payload/fonts.py).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from libera.payload import locate
from libera.payload.locate import PayloadError

# What allfontsgen reads, and the thumbnail scales it draws: five sizes, each
# for Latin and for East Asian names.
FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}
THUMBNAILS = 10

# The allfontsgen running now, for stop_allfontsgen.
_running: set[subprocess.Popen[str]] = set()


def generate(root: Path) -> None:
    """Write DoctRenderer.config beside x2t, which is where x2t looks for it.

    Its paths are relative, which x2t resolves against the file's own folder
    (doctrenderer/config.h, private_GetFile), and `<sdkjs>` is taken that way
    when it starts with "./". It names no AllFonts.js: every conversion passes
    the index's own as m_sAllFontsPath, which x2t takes over the config's.
    """
    layout = locate.Layout.of(root)
    if not layout.x2t.is_file():
        msg = f"no x2t at {layout.x2t}: the core artifact is incomplete"
        raise PayloadError(msg)

    def relative(path: Path) -> str:
        return Path(os.path.relpath(path, layout.bin)).as_posix()

    xregexp = layout.web_apps / "vendor" / "xregexp" / "xregexp-all-min.js"
    native = layout.sdkjs_common / "Native"
    layout.doctrenderer_config.write_text(
        "<Settings>\n"
        f"<file>{relative(native / 'native.js')}</file>\n"
        f"<file>{relative(native / 'jquery_native.js')}</file>\n"
        f"<file>{relative(xregexp)}</file>\n"
        f"<sdkjs>./{relative(layout.sdkjs)}</sdkjs>\n"
        "</Settings>\n",
        encoding="utf-8",
    )


def make_code_cache_dir(layout: locate.Layout) -> Path:
    """The folder doctrenderer keeps V8's code cache in, made if need be: the
    compiled editor scripts, 8 MB each, which halve a PDF export.

    It wrote them beside the scripts, into the payload, until core patch 0034
    let DOCTRENDERER_CACHE_DIR name a folder. One folder per converter -- its
    version, where it is, and when its x2t was written -- because a cache is
    V8's, for one build of it. Made, it clears the others, which no
    converter in use reads.
    """
    x2t = layout.x2t
    key = f"{locate.PAYLOAD_VERSION}|{x2t}|{x2t.stat().st_mtime_ns}"
    folder = (
        locate.get_state_dir()
        / "code-cache"
        / hashlib.sha256(key.encode()).hexdigest()[:16]
    )
    if not folder.is_dir():
        folder.mkdir(parents=True)
        for other in folder.parent.iterdir():
            if other != folder:
                shutil.rmtree(other, ignore_errors=True)
    return folder


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
