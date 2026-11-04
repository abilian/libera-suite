"""A file dragged from another application onto a real window, on Linux.

`tests/c_e2e/host/test_drop.py` dispatches a drop in the page, because a browser
cannot drag a file from the desktop, and what it dispatches is what the page
would have been told. WebKitGTK tells it something else. The first real drag, on
2026-11-04, typed `file:///...` into the document, whichever the file, and
opened and inserted nothing; the suite had passed throughout.

So this has one: a window offering the files as a file manager does, and X
events for the mouse, in steps too big to land twice on one toolbar button. The
toolbar and the start window need that: a move onto a new element fires only
dragenter, WebKit answers that position from it, and a release after a "no" is
no drop at all. A page that accepted on dragover alone passed on the canvas,
which is one element, and failed there.
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

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .conftest import Launch

pytestmark = pytest.mark.skipif(
    not (sys.platform.startswith("linux") and shutil.which("xdotool")),
    reason="a real drag needs X and xdotool: `lb linux gui-test`",
)

SOURCE = pathlib.Path(__file__).parent / "drag_source.py"
# The middle of the source window, which is at the top left of the screen.
GRAB = (75, 75)
# Above the middle of the screen by this much is the editor's toolbar: the
# window is 900 tall and centred, measured on 1000 and 1100 tall screens.
TOOLBAR_ABOVE_MIDDLE = 320


def xdotool(*args: object) -> str:
    return subprocess.run(
        ["xdotool", *map(str, args)], capture_output=True, text=True, check=True
    ).stdout


def middle_of_screen() -> tuple[int, int]:
    width, height = xdotool("getdisplaygeometry").split()
    return int(width) // 2, int(height) // 2


def window_names() -> list[str]:
    tree = subprocess.run(
        ["xwininfo", "-root", "-tree"], capture_output=True, text=True, check=True
    ).stdout
    return [line.split('"')[1] for line in tree.splitlines() if line.count('"') >= 2]


def wait_for_window(name: str) -> None:
    deadline = time.monotonic() + 30
    while not any(name in found for found in window_names()):
        assert time.monotonic() < deadline, f"no window {name}: {window_names()}"
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
        time.sleep(1)  # Mapped is not yet ready to be grabbed.
        xdotool("mousemove", *GRAB)
        time.sleep(0.3)
        xdotool("mousedown", 1)
        time.sleep(0.3)
        x, y = to
        for step in range(1, 21):
            xdotool(
                "mousemove",
                GRAB[0] + (x - GRAB[0]) * step // 20,
                GRAB[1] + (y - GRAB[1]) * step // 20,
            )
            time.sleep(0.1)
        xdotool("mouseup", 1)

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
    return [name for name in window_names() if name.startswith("*")]


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

    drag(middle_of_screen(), picture)

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

    drag(middle_of_screen(), document_to_drop)

    app.windows_that_painted(2)
    assert any(document_to_drop.name in name for name in window_names()), (
        f"{window_names()}\n{app.said()}"
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

    x, y = middle_of_screen()
    drag((x, y - TOOLBAR_ABOVE_MIDDLE), document_to_drop)

    app.windows_that_painted(2)
    assert edited_windows() == [], "the drop went into the document"


def test_a_document_dropped_on_the_start_window_opens(
    launch: Callable[..., Launch],
    document_to_drop: pathlib.Path,
    drag: Callable[..., None],
) -> None:
    app = launch()
    wait_for_window("Libera")
    time.sleep(3)  # The window is mapped; its page has to have loaded.

    drag(middle_of_screen(), document_to_drop)

    app.windows_that_painted(1)
    assert any(document_to_drop.name in name for name in window_names()), (
        f"{window_names()}\n{app.said()}"
    )
