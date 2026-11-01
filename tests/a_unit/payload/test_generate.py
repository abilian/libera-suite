"""Generating fonts, the one install step that runs a payload binary.

allfontsgen is stood in for by a shell script, because what is checked is how
its two ways of failing are reported: exiting non-zero, which raised an error
nothing above caught and threw its stderr away, and exiting 0 having found no
fonts, which an editor then shows as a box for every glyph.
"""

from __future__ import annotations

import sys
import threading
import time
from typing import TYPE_CHECKING

import pytest

from libera.payload import PayloadError, generate, locate

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


def test_a_failing_allfontsgen_says_what_it_said(tmp_path):
    root = make_payload_with_allfontsgen(
        tmp_path, 'echo "no such directory" >&2; exit 3'
    )

    with pytest.raises(PayloadError, match=r"exit 3.*no such directory"):
        generate.generate(root)


def test_finding_no_fonts_is_a_failure_whatever_it_exits(tmp_path):
    root = make_payload_with_allfontsgen(tmp_path, "exit 0")

    with pytest.raises(PayloadError, match="made 0 web fonts"):
        generate.generate(root)


def allfontsgen_making(fonts: int, thumbnails: int) -> str:
    """A stand-in that writes `fonts` web fonts and `thumbnails` pictures."""
    return f"""
for a in "$@"; do
  case "$a" in
    --output-web=*) web="${{a#*=}}" ;;
    --images=*) images="${{a#*=}}" ;;
  esac
done
i=0; while [ $i -lt {fonts} ]; do touch "$web/$i"; i=$((i+1)); done
i=0; while [ $i -lt {thumbnails} ]; do touch "$images/fonts_thumbnail$i.png"; i=$((i+1)); done
"""


def with_sources(root: Path, count: int) -> Path:
    for n in range(count):
        (root / "fonts-src" / f"face{n}.ttf").write_bytes(b"")
    return root


def test_a_font_for_each_source_and_every_thumbnail_is_a_payload(tmp_path):
    root = with_sources(
        make_payload_with_allfontsgen(tmp_path, allfontsgen_making(32, 10)), 32
    )

    assert generate.generate(root) == 32


def test_a_run_that_stopped_partway_through_the_fonts_is_a_failure(tmp_path):
    root = with_sources(
        make_payload_with_allfontsgen(tmp_path, allfontsgen_making(5, 10)), 32
    )

    with pytest.raises(PayloadError, match="made 5 web fonts from 32"):
        generate.generate(root)


def test_a_run_that_stopped_partway_through_the_thumbnails_is_a_failure(tmp_path):
    """On Windows it stopped at the second, and exited 0."""
    root = with_sources(
        make_payload_with_allfontsgen(tmp_path, allfontsgen_making(32, 1)), 32
    )

    with pytest.raises(PayloadError, match="drew 1 of 10"):
        generate.generate(root)


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
            generate.run_allfontsgen(locate.Layout(root))
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
