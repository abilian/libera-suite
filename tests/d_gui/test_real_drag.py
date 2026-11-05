"""A file dragged from another application onto a real window.

`tests/c_e2e/host/test_drop.py` dispatches a drop in the page, because a browser
cannot drag a file from the desktop, and what it dispatches is what the page
would have been told. WebKitGTK tells it something else. The first real drag, on
2026-11-04, typed `file:///...` into the document, whichever the file, and
opened and inserted nothing; the suite had passed throughout.

So this has one: a window offering the files as a file manager does, and a real
mouse, in steps too big to land twice on one toolbar button. The toolbar and the
start window need that: a move onto a new element fires only dragenter, WebKit
answers that position from it, and a release after a "no" is no drop at all. A
page that accepted on dragover alone passed on the canvas, which is one element,
and failed there.

On Linux under Xvfb, by `lb linux gui-test`, and on Windows in the desktop session,
by `lb app windows-gui-test`, where the screen has to be unlocked. macOS has
neither.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest
from support.make_sample_docx import solid_png

from .desktop import desktop

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .conftest import Launch

WHY_NOT = desktop.why_no_drag()
pytestmark = pytest.mark.skipif(WHY_NOT is not None, reason=WHY_NOT or "")

SOURCE = pathlib.Path(__file__).parent / "drag_source.py"
# The middle of the source window, which is at the top left of the screen.
GRAB = (75, 75)
# What every window of the application has in its title.
APPLICATION = "Libera"


def wait_for_window(name: str) -> None:
    deadline = time.monotonic() + 30
    while not any(name in found for found in desktop.window_names()):
        assert time.monotonic() < deadline, (
            f"no window {name}: {desktop.window_names()}"
        )
        time.sleep(0.2)


@pytest.fixture
def drag() -> Iterator[Callable[..., None]]:
    """Drag files from another application to a point on the screen."""
    sources: list[subprocess.Popen[bytes]] = []

    def run(to: tuple[int, int], *files: pathlib.Path) -> None:
        sources.append(
            subprocess.Popen([sys.executable, str(SOURCE), *map(str, files)])
        )
        wait_for_window("drag-source")
        time.sleep(1.5)  # Mapped is not yet ready to be grabbed.
        desktop.move(*GRAB)
        time.sleep(0.3)
        desktop.press()
        time.sleep(0.3)
        x, y = to
        for step in range(1, 21):
            desktop.move(
                GRAB[0] + (x - GRAB[0]) * step // 20,
                GRAB[1] + (y - GRAB[1]) * step // 20,
            )
            time.sleep(0.1)
        time.sleep(0.5)  # The target answers the last position before the release.
        desktop.release()

    yield run

    for source in sources:
        source.terminate()
        source.wait(timeout=10)


@pytest.fixture
def document_to_drop(tmp_path: pathlib.Path, sample_document: pathlib.Path):
    """Spaces and an accent, because a URI escapes them and a page has no path."""
    dropped = tmp_path / "from" / "mon rapport é.docx"
    dropped.parent.mkdir()
    shutil.copyfile(sample_document, dropped)
    return dropped


def edited_windows() -> list[str]:
    return [
        name
        for name in desktop.window_names()
        if name.startswith("*") and APPLICATION in name
    ]


def test_a_picture_dropped_on_the_page_is_inserted(
    launch: Callable[..., Launch],
    sample_document: pathlib.Path,
    drag: Callable[..., None],
    tmp_path: pathlib.Path,
) -> None:
    picture = tmp_path / "from" / "a picture é.png"
    picture.parent.mkdir()
    picture.write_bytes(solid_png(200, 120, (220, 30, 30)))
    app = launch(sample_document)
    app.windows_that_painted(1)

    drag(desktop.page_middle(sample_document.name), picture)

    deadline = time.monotonic() + 20
    media = tmp_path / "home"
    while not (copied := list(media.glob("**/media/*"))):
        assert time.monotonic() < deadline, f"nothing in the media\n{app.said()}"
        time.sleep(0.2)
    assert [path.read_bytes() for path in copied] == [picture.read_bytes()]


def test_a_document_dropped_on_the_page_opens_and_leaves_this_one_alone(
    launch: Callable[..., Launch],
    sample_document: pathlib.Path,
    document_to_drop: pathlib.Path,
    drag: Callable[..., None],
) -> None:
    app = launch(sample_document)
    app.windows_that_painted(1)

    drag(desktop.page_middle(sample_document.name), document_to_drop)

    app.windows_that_painted(2)
    assert any(document_to_drop.name in name for name in desktop.window_names()), (
        f"{desktop.window_names()}\n{app.said()}"
    )
    assert edited_windows() == [], "the drop went into the document"


def test_a_document_dropped_on_the_toolbar_opens(
    launch: Callable[..., Launch],
    sample_document: pathlib.Path,
    document_to_drop: pathlib.Path,
    drag: Callable[..., None],
) -> None:
    app = launch(sample_document)
    app.windows_that_painted(1)

    drag(desktop.toolbar(sample_document.name), document_to_drop)

    app.windows_that_painted(2)
    assert edited_windows() == [], "the drop went into the document"


def test_a_document_dropped_on_the_start_window_opens(
    launch: Callable[..., Launch],
    document_to_drop: pathlib.Path,
    drag: Callable[..., None],
) -> None:
    app = launch()
    wait_for_window(APPLICATION)
    time.sleep(3)  # The window is mapped; its page has to have loaded.

    drag(desktop.page_middle(APPLICATION), document_to_drop)

    app.windows_that_painted(1)
    assert any(document_to_drop.name in name for name in desktop.window_names()), (
        f"{desktop.window_names()}\n{app.said()}"
    )
