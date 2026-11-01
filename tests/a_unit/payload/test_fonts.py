"""The index of the machine's fonts, without allfontsgen: what the editor is
handed, what the server will serve from it, and when it is stale.

What allfontsgen makes of a real machine is b_integration's.
"""

from __future__ import annotations

import base64
import os
import struct
import threading
import time
from typing import TYPE_CHECKING

import pytest

from libera.host.server.api import Refused, Request
from libera.host.server.payload_files import serve_file, serve_font
from libera.host.session import Session, configure, create_session
from libera.payload import PayloadError, fonts, installer, locate

if TYPE_CHECKING:
    import pathlib

ALL_FONTS = """window["__all_fonts_js_version__"] = 3;

window["__fonts_files"] = [
"{a}",
"{b}"
];

window["__fonts_infos"] = [
["Alpha", 0, 0, -1, -1, -1, -1, -1, -1]
];
"""


@pytest.fixture
def index(tmp_path) -> pathlib.Path:
    """An index of two fonts that lie outside it, as installed ones do."""
    elsewhere = tmp_path / "system"
    elsewhere.mkdir()
    for name in ("a.ttf", "b.otf"):
        (elsewhere / name).write_bytes(f"the font {name}".encode())
    made = tmp_path / "index"
    (made / fonts.THUMBNAILS).mkdir(parents=True)
    (made / "AllFonts.js").write_text(
        ALL_FONTS.format(a=elsewhere / "a.ttf", b=elsewhere / "b.otf"),
        encoding="utf-8",
    )
    fonts.write_web_all_fonts(made / "AllFonts.js", made / fonts.WEB_ALL_FONTS)
    (made / fonts.THUMBNAILS / "fonts_thumbnail@2x.png").write_bytes(b"pictures")
    return made


def test_the_editor_gets_numbers_where_x2t_gets_paths(index):
    web = (index / fonts.WEB_ALL_FONTS).read_text(encoding="utf-8")
    assert 'window["__fonts_files"] = [\n"0",\n"1"\n];' in web
    assert "system" not in web
    # Everything else is x2t's, as allfontsgen's own web list would be.
    assert web.endswith(
        (index / "AllFonts.js").read_text(encoding="utf-8").split("];", 1)[1]
    )


def font(index: pathlib.Path, number: str):
    session = Session(payload=index.parent / "payload", work=index.parent, fonts=index)
    return serve_font(Request(session, path=number))


def test_a_font_is_served_by_its_number_from_where_it_lies(index):
    answer = font(index, "1")
    assert answer.file is not None
    assert answer.file.read_bytes() == b"the font b.otf"


@pytest.mark.parametrize(
    "number",
    [
        "2",
        "-1",
        "01x",
        "",
        "../index/AllFonts.js",
        "\N{ARABIC-INDIC DIGIT ONE}",
        "a.ttf",
    ],
)
def test_nothing_but_a_number_in_the_list_is_served(index, number):
    """Arabic-Indic one is a digit to isdigit(), and int() reads it as 1."""
    with pytest.raises(Refused) as refused:
        font(index, number)
    assert refused.value.status == 404


def test_the_font_list_and_pictures_come_from_the_index(index, tmp_path):
    payload = tmp_path / "payload"
    (payload / "sdkjs" / "common" / "Images").mkdir(parents=True)
    (payload / "sdkjs" / "common" / "AllFonts.js").write_text("the payload's")
    (payload / "sdkjs" / "common" / "Images" / "other.png").write_bytes(b"other")

    def served(path: str) -> bytes:
        answer = serve_file(payload, path, "", index)
        assert answer.file is not None
        return answer.file.read_bytes()

    assert b'"0",\n"1"' in served("sdkjs/common/AllFonts.js")
    assert served("sdkjs/common/Images/fonts_thumbnail@2x.png") == b"pictures"
    assert served("sdkjs/common/Images/other.png") == b"other"
    without = serve_file(payload, "sdkjs/common/AllFonts.js", "")
    assert without.file is not None
    assert without.file.read_bytes() == b"the payload's"


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A payload of one font, a system font folder, and a state folder."""
    shipped = tmp_path / "fonts-src"
    shipped.mkdir()
    (shipped / "ours.ttf").write_bytes(b"ours")
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "AllFonts.js").write_text(
        ALL_FONTS.format(a=shipped / "ours.ttf", b=shipped / "ours.ttf"),
        encoding="utf-8",
    )
    system = tmp_path / "system"
    (system / "family").mkdir(parents=True)
    # An hour back: Windows dates a folder by a clock that ticks every few
    # milliseconds, so a font added in the same tick changed nothing.
    hour_ago = time.time() - 3600
    for folder in (system, system / "family"):
        os.utime(folder, (hour_ago, hour_ago))
    monkeypatch.setattr(fonts, "_get_system_dirs", lambda: [system])
    monkeypatch.setattr(fonts, "_get_user_dirs", list)
    monkeypatch.setattr(locate, "get_state_dir", lambda: tmp_path / "state")
    monkeypatch.setenv(fonts.SWITCH, "1")
    return locate.Layout(payload), system


def test_a_font_installed_in_a_family_folder_makes_the_index_stale(machine):
    layout, system = machine
    before = fonts.get_index_dir(layout)
    (system / "family" / "new.ttf").write_bytes(b"new")
    assert fonts.get_index_dir(layout) != before


def test_an_index_is_used_once_it_exists_and_never_when_switched_off(
    machine, monkeypatch
):
    layout, _ = machine
    assert fonts.choose(layout) is None
    fonts.get_index_dir(layout).mkdir(parents=True)
    assert fonts.choose(layout) == fonts.get_index_dir(layout)
    monkeypatch.setenv(fonts.SWITCH, "0")
    assert fonts.choose(layout) is None


@pytest.fixture
def builds(monkeypatch) -> list[pathlib.Path]:
    """The indexes built, by a stand-in for allfontsgen that lists no font.
    Whole when it appears, as the real one's is: a window opening meanwhile
    took a bare folder for an earlier index and read its missing list."""
    made: list[pathlib.Path] = []

    def build(_layout, index):
        building = index.with_name(".building-stand-in")
        building.mkdir(parents=True)
        (building / "AllFonts.js").write_text(
            'window["__fonts_files"] = [];', encoding="utf-8"
        )
        building.rename(index)
        made.append(index)
        return 1

    monkeypatch.setattr(fonts, "build", build)
    return made


def build_behind(layout, using) -> None:
    building = fonts.build_behind(layout, using)
    if building is not None:
        building.join(5)


def test_building_behind_clears_every_other_index(machine, builds):
    layout, _ = machine
    current = fonts.get_index_dir(layout)
    current.mkdir(parents=True)
    stale = current.parent / "0123456789abcdef"
    stale.mkdir()
    half_built = current.parent / ".building-x"
    half_built.mkdir()
    build_behind(layout, {current})
    assert sorted(current.parent.iterdir()) == [current]
    assert builds == [], "the current index was built again"


def make_earlier_index(layout: locate.Layout, name: str, font: pathlib.Path):
    earlier = fonts.get_index_dir(layout).parent / name
    earlier.mkdir(parents=True)
    (earlier / "AllFonts.js").write_text(
        ALL_FONTS.format(a=font, b=font), encoding="utf-8"
    )
    return earlier


def test_a_window_opened_after_a_font_is_installed_gets_it(machine, builds):
    """Installing a font made the next start lose every installed one: its
    index was still to be built, and the run fell back to the payload's. The
    earlier index serves until the new one is built, for the windows already
    open, and the next window gets the new one."""
    layout, system = machine
    there = system / "kept.ttf"
    there.write_bytes(b"kept")
    earlier = make_earlier_index(layout, "0123456789abcdef", there)
    (system / "family" / "installed.ttf").write_bytes(b"new")
    assert fonts.choose(layout) == earlier

    build_behind(layout, {earlier})
    assert earlier.is_dir(), "the index in use was removed"
    assert builds == [fonts.get_index_dir(layout)]
    assert fonts.choose(layout) == fonts.get_index_dir(layout)


def test_one_build_at_a_time_and_nothing_swept_meanwhile(machine, monkeypatch):
    """Windows open while an index is built, and each asks for one."""
    layout, _ = machine
    started = threading.Event()
    release = threading.Event()
    asked: list[pathlib.Path] = []

    def slow_build(_layout, index):
        asked.append(index)
        index.parent.mkdir(parents=True, exist_ok=True)
        (index.parent / ".building-now").mkdir()
        started.set()
        release.wait(5)
        return 1

    monkeypatch.setattr(fonts, "build", slow_build)
    first = fonts.build_behind(layout, set())
    assert first is not None
    try:
        assert started.wait(5)
        assert fonts.build_behind(layout, set()) is None
        assert (fonts.get_index_dir(layout).parent / ".building-now").is_dir()
    finally:
        # Or the build holds fonts.BUILDING into the next test.
        release.set()
        first.join(5)
    assert len(asked) == 1
    assert not fonts.BUILDING.locked(), "a finished build kept the lock"


def test_an_earlier_index_listing_a_removed_font_is_not_used(machine, tmp_path):
    layout, _ = machine
    make_earlier_index(layout, "0123456789abcdef", tmp_path / "removed.ttf")
    assert fonts.choose(layout) is None


def test_a_new_window_gets_the_newest_index_not_the_first_windows(machine, builds):
    layout, _ = machine
    first = Session(payload=layout.root, work=layout.root.parent / "w" / "1")
    configure(first)
    assert first.fonts is None
    # The first window's list was still to be built: the second asks for it,
    # and the third, opened once it is there, has it.
    create_session()
    fonts.BUILDING.acquire(timeout=5)
    fonts.BUILDING.release()
    assert builds == [fonts.get_index_dir(layout)]
    assert create_session().fonts == fonts.get_index_dir(layout)
    assert first.fonts is None


def test_installing_the_payload_indexes_the_machines_fonts(machine, builds):
    layout, _ = machine
    said: list[str] = []
    installer._index_installed_fonts(layout, said.append)
    assert builds == [fonts.get_index_dir(layout)]
    assert said[-1] == "    1 fonts"


def test_an_index_that_fails_does_not_fail_the_install(machine, monkeypatch):
    layout, _ = machine

    def fails(_layout, _index):
        msg = "allfontsgen drew 2 of 10 font thumbnails"
        raise PayloadError(msg)

    monkeypatch.setattr(fonts, "build", fails)
    said: list[str] = []
    installer._index_installed_fonts(layout, said.append)
    assert said[-1] == "    not indexed: allfontsgen drew 2 of 10 font thumbnails"


def selection(*records: tuple[str, list[str]], after: bytes = b"ranges") -> bytes:
    """A font selection as allfontsgen writes it: a count, then per font its
    record's length (itself included), its name, its other names, and fields
    that stand here for the path, style and metrics; then the range table."""

    def string(text: str) -> bytes:
        return struct.pack("<i", len(text.encode())) + text.encode()

    out = struct.pack("<i", len(records))
    for name, others in records:
        body = string(name) + struct.pack("<i", len(others))
        body += b"".join(string(o) for o in others) + f"fields of {name}".encode()
        out += struct.pack("<i", 4 + len(body)) + body
    return out + after


def test_a_missing_windows_font_is_answered_by_the_floor():
    """Calibri went to the Lato installed on a Mac, not to Carlito, and a
    document took a page more than in Word."""
    got = fonts.add_floor_names(
        selection(("Lato", []), ("Carlito", ["Carlito Regular"]))
    )
    assert got == selection(("Lato", []), ("Carlito", ["Carlito Regular", "Calibri"]))


def test_a_windows_font_the_machine_has_keeps_its_name():
    machine = selection(("Calibri", []), ("Carlito", []), ("Liberation Sans", []))
    assert fonts.add_floor_names(machine) == selection(
        ("Calibri", []), ("Carlito", []), ("Liberation Sans", ["Arial"])
    )


def test_the_editor_and_x2t_get_the_same_floor(tmp_path):
    """x2t reads font_selection.bin; the editor, the same bytes in AllFonts.js."""
    bare = selection(("Carlito", []), after=b"")
    (tmp_path / "font_selection.bin").write_bytes(bare + b"ranges for x2t")
    encoded = base64.b64encode(bare).decode()
    (tmp_path / "AllFonts.js").write_text(
        f'window["__all_fonts_js_version__"] = 2;\n'
        f'window["g_fonts_selection_bin"] = "{encoded}";\n',
        encoding="utf-8",
    )
    fonts.put_floor_first(tmp_path)
    named = selection(("Carlito", ["Calibri"]), after=b"")
    assert (tmp_path / "font_selection.bin").read_bytes() == named + b"ranges for x2t"
    js = (tmp_path / "AllFonts.js").read_text(encoding="utf-8")
    assert f'"{base64.b64encode(named).decode()}"' in js
