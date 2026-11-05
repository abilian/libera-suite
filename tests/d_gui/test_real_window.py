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

import ctypes
import sys
from ctypes import wintypes
from typing import TYPE_CHECKING

import pytest

from .conftest import complaints

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


def test_a_window_on_windows_stays_on_the_screen(
    launch: Callable[..., Launch], sample_document: Path
) -> None:
    """Measured on the primary monitor, where this tier's windows open. Means
    something on a small or scaled display: 1920x1080 at 150% was off it."""
    if sys.platform == "win32":
        app = launch(sample_document)
        app.windows_that_painted(1)
        user32 = ctypes.windll.user32
        # As the application is, so that both of these are in physical pixels.
        user32.SetProcessDPIAware()
        area = wintypes.RECT()
        spi_getworkarea = 0x30
        user32.SystemParametersInfoW(spi_getworkarea, 0, ctypes.byref(area), 0)
        found: dict[str, wintypes.RECT] = {}

        def visit(handle: int, _param: int) -> bool:
            size = user32.GetWindowTextLengthW(handle)
            text = ctypes.create_unicode_buffer(size + 1)
            user32.GetWindowTextW(handle, text, size + 1)
            if user32.IsWindowVisible(handle) and sample_document.name in text.value:
                rect = wintypes.RECT()
                user32.GetWindowRect(handle, ctypes.byref(rect))
                found[text.value] = rect
            return True

        user32.EnumWindows(
            ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(visit), 0
        )
        (rect,) = found.values()
        assert area.left <= rect.left
        assert area.top <= rect.top
        assert rect.right <= area.right
        assert rect.bottom <= area.bottom
    else:
        pytest.skip("the other toolkits place their windows themselves")


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
