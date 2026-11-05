"""A window per document, and text drawn in the engine that ships.

Both halves of this were bugs. `app.py`'s `_open_rest` waited on
`webview.windows`, a list `create_window` fills *before* `start()` runs, so it
returned at once and every document after the first raced the GUI loop: a beta
tester reported two documents of different types as impossible to have open at
once. And a payload whose blank documents carried a quarter of the normal
leading drew overlapping, struck-through lines while every check that did not
look at the picture passed.

Neither is visible to the e2e tier: it has no window, and its browser is not
the engine any user has.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from support.mac_checks import Run
from support.protected import make_protected

from libera.host import apps

from .conftest import SOFTWARE_RENDERING, complaints
from .desktop import desktop

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .conftest import Launch


def test_one_document_paints_in_the_real_engine(
    launch: Callable[..., Launch], sample_document: Path
) -> None:
    app = launch(sample_document)
    (painted,) = app.windows_that_painted(1)
    assert complaints(painted) == [], f"{painted}: the picture is there to look at"


def test_every_document_gets_a_window_of_its_own(
    launch: Callable[..., Launch], sample_document: Path, blank_presentation: Path
) -> None:
    app = launch(sample_document, blank_presentation)
    painted = app.windows_that_painted(2)
    assert len(painted) == 2
    # Each window photographs its own canvas, so two pictures that came out
    # identical would mean one window posted twice.
    assert painted[0].read_bytes() != painted[1].read_bytes()


@pytest.mark.skipif(
    sys.platform != "win32", reason="the other toolkits place their windows themselves"
)
def test_a_window_on_windows_stays_on_the_screen(
    launch: Callable[..., Launch], sample_document: Path, blank_presentation: Path
) -> None:
    """Measured on the main monitor, where this tier's windows open. Means
    something on a small or scaled display: 1920x1080 at 150% was off it.

    Two, because they are made differently: the first is listed for start() to
    make, and any later one is made and shown before `create_window` returns."""
    app = launch(sample_document, blank_presentation)
    app.windows_that_painted(2)

    area = desktop.work_area()
    for document in (sample_document, blank_presentation):
        rect = desktop.rect(document.name)
        assert area.left <= rect.left, document.name
        assert area.top <= rect.top, document.name
        assert rect.right <= area.right, document.name
        assert rect.bottom <= area.bottom, document.name


def test_close_file_on_a_password_dialog_closes_the_window(
    tmp_path: Path, payload_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dialog's own button, in the engine that ships: headless Chromium only
    shows that the host is asked to."""
    for name, value in SOFTWARE_RENDERING.items():
        monkeypatch.setenv(name, value)
    protected = make_protected(apps.WORDS, "docx", tmp_path / "made")

    Run(tmp_path, payload_root).window(protected, decline=True)


def test_the_window_survives_the_documents_it_opened(
    launch: Callable[..., Launch], sample_document: Path, blank_presentation: Path
) -> None:
    """Nothing exits once the windows are up.

    A crash after the last document loads looks like a pass to anything that
    stops at the picture: the shots are already on disk.
    """
    app = launch(sample_document, blank_presentation)
    app.windows_that_painted(2)
    assert app.process.poll() is None, app.said()
