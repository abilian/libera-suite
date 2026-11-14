"""The keys the menu bar shows, read off the real bar, and Ctrl-S on Linux.

Off a Mac the bar is pywebview's, labelled after it is built: by GTK from the
accelerators `menu.gtk.install` sets, and on Windows by `menu.gtk.show_keys`,
which writes on each window's menu strip. Either can come out blank with
nothing failing, so the bar itself is read.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest
from support.protected import make_protected

from libera.host import apps, shortcuts
from libera.host.menu import gtk

if TYPE_CHECKING:
    from .driver import Run

pytestmark = pytest.mark.skipif(
    sys.platform == "darwin", reason="AppKit's items show their own keys"
)


def shown_on_this_platform() -> dict[str, str]:
    """Each item that shows a key here, by its title: on Linux, those GTK
    binds, so not the editor's own."""
    return {
        path[-1]: key.label
        for path, key in gtk.list_keys(apps.WORDS).items()
        if key and (sys.platform == "win32" or key not in shortcuts.EDITOR_KEEPS)
    }


def test_the_bar_shows_its_keys(run: Run) -> None:
    document = make_protected(apps.WORDS, "docx", run.work / "keys", password="")
    run.window(document, steps=(("menu-keys", json.dumps(shown_on_this_platform())),))


@pytest.mark.skipif(sys.platform != "linux", reason="GTK's accelerator")
def test_ctrl_s_saves_through_the_menu(run: Run) -> None:
    document = make_protected(apps.WORDS, "docx", run.work / "save", password="")
    run.window(document, steps=(("ctrl-s", "zqx-saved-by-key"),))
