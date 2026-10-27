"""Running allfontsgen, the one payload binary the host runs besides x2t, and
writing the converter's configuration.

allfontsgen is stood in for by a shell script, because what is checked is how
its two ways of failing are reported: exiting non-zero, which raised an error
nothing above caught and threw its stderr away, and exiting 0 having found no
fonts, which an editor then shows as a box for every glyph.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import TYPE_CHECKING

import pytest

from libera.payload import PayloadError, fonts, generate, locate

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="a shell script stands in for allfontsgen"
)


def make_payload_with_allfontsgen(tmp_path: Path, script: str) -> Path:
    root = tmp_path / "payload"
    tool = root / "bin" / "tools" / "allfontsgen"
    tool.parent.mkdir(parents=True)
    tool.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    tool.chmod(0o755)
    (root / "fonts-src").mkdir()
    return root


def build_shipped(root: Path) -> int:
    layout = locate.Layout.of(root)
    return fonts.build(layout, fonts.get_shipped_dir(layout), machine=False)


@pytest.fixture(name="state")
def state_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(locate, "get_state_dir", lambda: tmp_path / "state")
    return tmp_path / "state"


def test_a_failing_allfontsgen_says_what_it_said(tmp_path, state):
    root = make_payload_with_allfontsgen(
        tmp_path, 'echo "no such directory" >&2; exit 3'
    )

    with pytest.raises(PayloadError, match=r"exit 3.*no such directory"):
        build_shipped(root)


def test_finding_no_fonts_is_a_failure_whatever_it_exits(tmp_path, state):
    root = make_payload_with_allfontsgen(tmp_path, allfontsgen_making(0, 10))

    with pytest.raises(PayloadError, match="listed 0 fonts"):
        build_shipped(root)
    assert not any(state.rglob("AllFonts.js")), "a failed index was kept"


def allfontsgen_making(count: int, thumbnails: int) -> str:
    """A stand-in that lists `count` fonts and draws `thumbnails` pictures,
    with a font selection of no font, which is enough to name the floor in."""
    return rf"""
for a in "$@"; do
  case "$a" in
    --allfonts=*) all="${{a#*=}}" ;;
    --images=*) images="${{a#*=}}" ;;
    --selection=*) selection="${{a#*=}}" ;;
  esac
done
{{
  echo 'window["__fonts_files"] = ['
  i=0; while [ $i -lt {count} ]; do echo "\"/f$i.ttf\","; i=$((i+1)); done
  echo '];'
  echo 'window["g_fonts_selection_bin"] = "AAAAAA==";'
}} > "$all"
printf '\0\0\0\0' > "$selection"
i=0; while [ $i -lt {thumbnails} ]; do touch "$images/fonts_thumbnail$i.png"; i=$((i+1)); done
"""


def with_sources(root: Path, count: int) -> Path:
    for n in range(count):
        (root / "fonts-src" / f"face{n}.ttf").write_bytes(b"")
    return root


def test_a_font_for_each_source_and_every_thumbnail_is_an_index(tmp_path, state):
    root = with_sources(
        make_payload_with_allfontsgen(tmp_path, allfontsgen_making(32, 10)), 32
    )

    assert build_shipped(root) == 32
    index = fonts.get_shipped_dir(locate.Layout.of(root))
    assert index.is_relative_to(state), "the index was written into the payload"
    assert (index / fonts.WEB_ALL_FONTS).is_file()


def test_a_run_that_stopped_partway_through_the_fonts_is_a_failure(tmp_path, state):
    root = with_sources(
        make_payload_with_allfontsgen(tmp_path, allfontsgen_making(5, 10)), 32
    )

    with pytest.raises(PayloadError, match="listed 5 fonts from 32"):
        build_shipped(root)


def test_a_run_that_stopped_partway_through_the_thumbnails_is_a_failure(
    tmp_path, state
):
    """On Windows it stopped at the second, and exited 0."""
    root = with_sources(
        make_payload_with_allfontsgen(tmp_path, allfontsgen_making(32, 1)), 32
    )

    with pytest.raises(PayloadError, match="drew 1 of 10"):
        build_shipped(root)


def test_the_converter_configuration_names_the_payload_relatively(tmp_path):
    """x2t resolves each path against the configuration's own folder, so the
    payload can move, and be installed read-only, without writing it again."""
    root = make_payload_with_allfontsgen(tmp_path, "exit 0")
    (root / "bin" / "x2t").write_bytes(b"")

    generate.generate(root)

    config = (root / "bin" / "DoctRenderer.config").read_text(encoding="utf-8")
    assert "<file>../sdkjs/common/Native/native.js</file>" in config
    assert "<sdkjs>./../sdkjs</sdkjs>" in config
    assert str(tmp_path) not in config
    assert "<allfonts>" not in config


def test_each_converter_has_a_code_cache_of_its_own(tmp_path, state):
    """V8's code cache is for one build of V8: a converter rebuilt or
    upgraded gets a new folder, and the old one goes."""
    root = make_payload_with_allfontsgen(tmp_path, "exit 0")
    x2t = root / "bin" / "x2t"
    x2t.write_bytes(b"one build")
    layout = locate.Layout.of(root)
    first = generate.make_code_cache_dir(layout)
    (first / "word-sdk-all.cache").write_bytes(b"compiled")
    assert generate.make_code_cache_dir(layout) == first
    assert (first / "word-sdk-all.cache").is_file()

    os.utime(x2t, ns=(0, x2t.stat().st_mtime_ns + 10**9))
    second = generate.make_code_cache_dir(layout)

    assert second != first
    assert second.is_relative_to(state)
    assert list(second.parent.iterdir()) == [second]


def test_a_quit_stops_the_allfontsgen_still_running(tmp_path):
    """A font index builds on a daemon thread, which a quit ends, and its
    allfontsgen ran on without it."""
    # exec, so the process killed is the one holding the pipes, as the real
    # allfontsgen is: dash, Debian's sh, runs a last command as a child, and
    # killing the shell left `sleep` holding them for its thirty seconds.
    root = make_payload_with_allfontsgen(tmp_path, "exec sleep 30")
    failed: list[Exception] = []

    def build():
        try:
            generate.run_allfontsgen(locate.Layout.of(root))
        except PayloadError as e:
            failed.append(e)

    building = threading.Thread(target=build)
    building.start()
    deadline = time.monotonic() + 5
    while not generate._running and time.monotonic() < deadline:
        time.sleep(0.01)

    generate.stop_allfontsgen()

    building.join(5)
    assert not building.is_alive(), "allfontsgen still running"
    assert failed
