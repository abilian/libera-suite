"""The fonts installed on this machine, indexed beside the payload's own.

The payload's index (`generate`) lists the fonts it ships and nothing else.
This one adds the machine's: allfontsgen's `--use-system`, plus the per-user
folders it does not read on Linux. It lives in the state folder, one folder
per fingerprint of the font folders, never in the payload; and nothing is
copied, because the server serves each font from where it lies, by its number
in the list. See notes/23-installed-fonts.md.

Each window keeps the list it was opened with, for the editor and for x2t
alike, and a window opened after a newer index is built uses that one. The
first is built when the payload is installed, where the first start waits
anyway; a change to the machine's fonts is noticed as a window opens, and
built behind it.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import logging
import os
import re
import shutil
import struct
import sys
import tempfile
import threading
import time
from pathlib import Path

from libera.payload import generate, locate
from libera.payload.locate import PayloadError

logger = logging.getLogger(__name__)

# `installed_fonts = false` in config.toml, or this at 0, keeps to the
# payload's fonts: the same document then lays out the same on every machine,
# which the render checks and the reproduction of a report both need.
SWITCH = "LIBERA_INSTALLED_FONTS"

# What an index folder holds besides allfontsgen's AllFonts.js (x2t's, of
# paths) and font_selection.bin: the editor's AllFonts.js, of numbers, and the
# font menu's pictures.
WEB_ALL_FONTS = "AllFonts.web.js"
THUMBNAILS = "Images"

# Held while an index is built, and released by the thread building it.
BUILDING = threading.Lock()

FONT_FILES = re.compile(r'window\["__fonts_files"\] = \[(.*?)\];', re.DOTALL)
_INT = struct.Struct(
    "<i"
)  # allfontsgen's INT, little-endian on every platform we build
SELECTION = re.compile(r'(window\["g_fonts_selection_bin"\] = ")([^"]*)(")')

# The metric-compatible floor: each font we ship with the widths of a Windows
# font, under that font's name. A machine without the Windows font would
# otherwise substitute whatever scores best, and on a Mac Calibri went to Lato,
# not Carlito, so a conversion's page count depended on what was installed.
# Neither engine's list of look-alikes pairs Calibri with Carlito (sdkjs
# map.js, core ApplicationFonts.h); both match a font's other names exactly.
FLOOR = {
    "Calibri": "Carlito",
    "Cambria": "Caladea",
    "Arial": "Liberation Sans",
    "Times New Roman": "Liberation Serif",
    "Courier New": "Liberation Mono",
}
# Part of every fingerprint: an index made before the floor was named has the
# same font folders, and would otherwise be used as it is.
PROCESSING = "floor-names-1"


def is_wanted() -> bool:
    """Unless the switch is off, in the environment or in config.toml."""
    said = os.environ.get(SWITCH)
    if said is not None:
        return said != "0"
    return locate.read_config_bool("installed_fonts") is not False


def get_index_dir(layout: locate.Layout) -> Path:
    """Where the index of this machine's fonts as they are now belongs."""
    return locate.get_state_dir() / "fonts" / make_fingerprint(layout)


def choose(layout: locate.Layout) -> Path | None:
    """A new window's index, or None for the payload's fonts alone.

    The index of the fonts as they are now; or, while that one is still to be
    built, the newest earlier one whose fonts are all still there. A font
    installed since is missing from it until a window opens after the build;
    a font it lists and the server cannot find would leave the editor loading
    forever.
    """
    if not is_wanted():
        return None
    index = get_index_dir(layout)
    if index.is_dir():
        return index
    earlier = [d for d in index.parent.glob("[!.]*") if d.is_dir()]
    for found in sorted(earlier, key=_read_mtime, reverse=True):
        if all(f.is_file() for f in read_font_files(found / "AllFonts.js")):
            return found
    return None


def build_behind(
    layout: locate.Layout, using: set[Path | None]
) -> threading.Thread | None:
    """Build the index of the fonts as they are now, in a thread, if it is
    missing, and return that thread.

    Every other index goes first, finished or not, but those the open
    windows are `using`. Nothing goes while a build runs, its own folder
    among them: one process runs at a time (instance.py), and a second build
    is not started.
    """
    if not is_wanted() or not BUILDING.acquire(blocking=False):
        return None
    try:
        building = _sweep_and_start(layout, using)
    except BaseException:
        BUILDING.release()
        raise
    if building is None:
        BUILDING.release()
    return building


def _sweep_and_start(
    layout: locate.Layout, using: set[Path | None]
) -> threading.Thread | None:
    index = get_index_dir(layout)
    for old in index.parent.glob("*"):
        if old != index and old not in using:
            shutil.rmtree(old, ignore_errors=True)
    if index.is_dir():
        return None
    building = threading.Thread(
        target=_build_and_say, args=(layout, index), daemon=True
    )
    building.start()
    return building


def _build_and_say(layout: locate.Layout, index: Path) -> None:
    started = time.monotonic()
    try:
        count = build(layout, index)
    except PayloadError as e:
        logger.warning("installed fonts: not indexed: %s", e)
        return
    finally:
        BUILDING.release()
    logger.info(
        "installed fonts: %d files indexed in %.1f s, used by the next window",
        count,
        time.monotonic() - started,
    )


def build(layout: locate.Layout, index: Path) -> int:
    """Index the payload's fonts and the machine's into `index`, and return
    how many font files it lists.

    Built aside and renamed into place, so an index is only ever whole: the
    thumbnails are drawn by position in the list, and a list without its
    pictures shows the wrong names in the font menu.
    """
    index.parent.mkdir(parents=True, exist_ok=True)
    building = Path(tempfile.mkdtemp(prefix=".building-", dir=index.parent))
    try:
        images = building / THUMBNAILS
        images.mkdir()
        inputs = [*_get_payload_font_dirs(layout), *_get_user_dirs()]
        generate.run_allfontsgen(
            layout,
            "--use-system=true",
            "--input=" + ";".join(str(d) for d in inputs if d.is_dir()),
            f"--allfonts={building / 'AllFonts.js'}",
            f"--images={images}",
            f"--selection={building / 'font_selection.bin'}",
        )
        # The counts, as generate checks them: exiting 0 proves nothing.
        count = len(read_font_files(building / "AllFonts.js"))
        if count < len(read_font_files(layout.all_fonts)):
            msg = f"allfontsgen listed {count} fonts, fewer than the payload's"
            raise PayloadError(msg)
        drawn = len(list(images.glob("fonts_thumbnail*.png")))
        if drawn < generate.THUMBNAILS:
            msg = f"allfontsgen drew {drawn} of {generate.THUMBNAILS} font thumbnails"
            raise PayloadError(msg)
        put_floor_first(building)
        write_web_all_fonts(building / "AllFonts.js", building / WEB_ALL_FONTS)
        building.rename(index)
    finally:
        shutil.rmtree(building, ignore_errors=True)
    return count


@functools.cache
def read_font_files(all_fonts: Path) -> list[Path]:
    """The font files an AllFonts.js of paths lists, in its order: a font's
    number in the editor's list is its place in this one."""
    found = FONT_FILES.search(all_fonts.read_text(encoding="utf-8"))
    if found is None:
        msg = f"no font list in {all_fonts}"
        raise PayloadError(msg)
    return [Path(p) for p in re.findall(r'"([^"]*)"', found.group(1))]


def write_web_all_fonts(all_fonts: Path, web: Path) -> None:
    """The editor's AllFonts.js: x2t's, with each path replaced by its number.

    What allfontsgen's --output-web writes, but without copying every font
    into a folder of its own to serve from: 1.6 GB on a Mac.
    """
    text = all_fonts.read_text(encoding="utf-8")
    found = FONT_FILES.search(text)
    if found is None:
        msg = f"no font list in {all_fonts}"
        raise PayloadError(msg)
    count = len(re.findall(r'"([^"]*)"', found.group(1)))
    numbers = ",\n".join(f'"{n}"' for n in range(count))
    web.write_text(
        text[: found.start(1)] + f"\n{numbers}\n" + text[found.end(1) :],
        encoding="utf-8",
        newline="\n",  # as allfontsgen writes it, on Windows too
    )


def put_floor_first(index: Path) -> None:
    """Name each font of the floor after the Windows font it stands in for,
    unless the machine has that font, in both copies of the selection: x2t's
    font_selection.bin and the editor's, inside AllFonts.js."""
    selection = index / "font_selection.bin"
    selection.write_bytes(add_floor_names(selection.read_bytes()))
    all_fonts = index / "AllFonts.js"
    text = all_fonts.read_text(encoding="utf-8")
    found = SELECTION.search(text)
    if found is None:
        msg = f"no font selection in {all_fonts}"
        raise PayloadError(msg)
    named = base64.b64encode(add_floor_names(base64.b64decode(found.group(2))))
    all_fonts.write_text(
        text[: found.start(2)] + named.decode() + text[found.end(2) :],
        encoding="utf-8",
        newline="\n",
    )


def add_floor_names(selection: bytes) -> bytes:
    """A font selection in which each font of the floor also answers to the
    name of the Windows font it stands in for, where no font has that name.

    The format is allfontsgen's, version 2 (core's ApplicationFonts.cpp,
    FromBuffer): a count, then a record per font, each its length (itself
    included), its name, a count of other names and those names, then fields
    this leaves alone. Strings are a length and UTF-8. Anything after the
    records, x2t's table of character ranges, is kept as it is.
    """
    count = _INT.unpack_from(selection)[0]
    records: list[tuple[str, list[str], bytes]] = []
    at = _INT.size
    for _ in range(count):
        length = _INT.unpack_from(selection, at)[0]
        name, cursor = _read_string(selection, at + _INT.size)
        others: list[str] = []
        named = _INT.unpack_from(selection, cursor)[0]
        cursor += _INT.size
        for _ in range(named):
            other, cursor = _read_string(selection, cursor)
            others.append(other)
        records.append((name, others, selection[cursor : at + length]))
        at += length
    present = {n for name, others, _ in records for n in (name, *others)}
    stands_in = {
        ours: windows for windows, ours in FLOOR.items() if windows not in present
    }
    out = [_INT.pack(count)]
    for name, others, rest in records:
        names = [*others, stands_in[name]] if name in stands_in else others
        body = (
            _pack_string(name)
            + _INT.pack(len(names))
            + b"".join(_pack_string(n) for n in names)
            + rest
        )
        out.append(_INT.pack(_INT.size + len(body)) + body)
    out.append(selection[at:])
    return b"".join(out)


def _read_string(data: bytes, at: int) -> tuple[str, int]:
    """The string whose length is at `at`, and where the next field starts."""
    length = _INT.unpack_from(data, at)[0]
    start = at + _INT.size
    return data[start : start + length].decode(), start + length


def _pack_string(text: str) -> bytes:
    encoded = text.encode()
    return _INT.pack(len(encoded)) + encoded


def find_served(index: Path, path: str) -> Path | None:
    """The index's own version of a payload file the editor fetches, if it has
    one: the font list, and the font menu's pictures."""
    if path == "sdkjs/common/AllFonts.js":
        return index / WEB_ALL_FONTS
    folder, _, name = path.rpartition("/")
    if folder == "sdkjs/common/Images" and name.startswith("fonts_thumbnail"):
        return index / THUMBNAILS / name
    return None


def make_fingerprint(layout: locate.Layout) -> str:
    """What the index depends on, hashed: how it is processed, the payload's
    font list, and the modification time of each folder of fonts, and of each
    folder in it.

    Installing or removing a font changes its folder's time. One level down
    as well, because Linux keeps a folder per family under /usr/share/fonts.
    A font replaced in place under the same name is not seen.
    """
    seen = [PROCESSING, f"{layout.all_fonts}|{_read_mtime(layout.all_fonts)}"]
    tops = [*_get_payload_font_dirs(layout), *_get_system_dirs(), *_get_user_dirs()]
    for top in tops:
        if not top.is_dir():
            continue
        for folder in [top, *(d for d in top.iterdir() if d.is_dir())]:
            seen.append(f"{folder}|{_read_mtime(folder)}")
    return hashlib.sha256("\n".join(seen).encode()).hexdigest()[:16]


def _read_mtime(path: Path) -> int:
    return path.stat().st_mtime_ns


def _get_payload_font_dirs(layout: locate.Layout) -> list[Path]:
    """Where the payload's own fonts are, as its index says: fonts-src in an
    installed payload, the core-fonts checkout in a build tree."""
    return sorted({f.parent for f in read_font_files(layout.all_fonts)})


def _get_system_dirs() -> list[Path]:
    """The folders allfontsgen's --use-system reads, as its source names them
    (core's ApplicationFonts.cpp, GetSetupFontFiles), for the fingerprint.
    On macOS it also asks CoreText, which adds ~/Library/Fonts."""
    if sys.platform == "darwin":
        return [
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ]
    if os.name == "nt":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return [windir / "Fonts", local / "Microsoft" / "Windows" / "Fonts"]
    return [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path("/run/host/fonts"),
    ]


def _get_user_dirs() -> list[Path]:
    """The per-user folders --use-system misses: on Linux, all of them."""
    if sys.platform == "darwin" or os.name == "nt":
        return []
    return [locate.get_xdg_data_home() / "fonts", Path.home() / ".fonts"]
