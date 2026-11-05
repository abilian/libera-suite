"""A window on Windows stays on the screen it opens on."""

from __future__ import annotations

import pytest

from libera.host.window.win32 import fit_on_screen

# 1920x1080 less a taskbar, in the physical pixels WinForms works in.
SCREEN = (0, 0, 1920, 1032)


@pytest.mark.parametrize(
    ("bounds", "fitted"),
    [
        pytest.param((100, 100, 800, 600), (100, 100, 800, 600), id="fits: untouched"),
        pytest.param((228, 228, 1080, 960), (228, 72, 1080, 960), id="too low: moved"),
        pytest.param((1500, 50, 800, 600), (1120, 50, 800, 600), id="too far: moved"),
        pytest.param((114, 114, 1946, 1106), SCREEN, id="too big: the whole screen"),
        pytest.param((-50, -50, 800, 600), (0, 0, 800, 600), id="above: moved"),
    ],
)
def test_a_window_moves_and_shrinks_only_as_far_as_it_has_to(bounds, fitted):
    assert fit_on_screen(bounds, SCREEN) == fitted


def test_the_area_can_be_a_monitor_left_of_the_main_one():
    monitor = (-1600, 100, 1600, 900)

    assert fit_on_screen((-300, 500, 800, 600), monitor) == (-800, 400, 800, 600)
