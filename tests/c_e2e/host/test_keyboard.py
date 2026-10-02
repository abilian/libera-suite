"""What the page does with a keystroke the menu bar also owns.

Cmd-N has been wrong twice: once making two windows because the page acted as
well as the menu, once making none because the page claimed the key instead of
merely declining it. Both were in this JavaScript, and a browser can drive it.

What a browser cannot do is *be* AppKit. These tests cover the page's half of
the contract -- given what the host says the menu owns, does the page act or
not -- and nothing here says whether the menu then fires. That half needs a
real application; see notes/04-plan.md.

The server runs in-process rather than as `libera --serve`, because the whole
point is to vary what the host tells the page, and a subprocess with no window
always reports an empty list.
"""

from __future__ import annotations

import sys

import pytest

from libera.host import menu


def test_the_page_yields_a_key_the_menu_bar_owns(editor_with):
    """Cmd-N with a menu bar: AppKit's job, so the page must not also ask."""
    editor = editor_with([s.as_json() for s in menu.PAGE_YIELDS])
    editor.press("Meta+n")

    # Nothing asked is also what a key that never arrived looks like.
    assert editor.saw("n") > 0, "the keystroke reached no frame"
    assert editor.asked_for("new") == 0


@pytest.mark.xfail(
    not sys.platform.startswith("darwin"),
    strict=True,
    reason=(
        "No New accelerator on Linux. Measured in the container: the keystroke"
        " reaches the editor -- one frame sees it -- and no `new` request"
        " follows, for Meta+n or Control+n. The menu bar that owns it is"
        " macOS-only (host/menu.py), and the web layer does not handle the key"
        " itself off a Mac. strict, so this tells us if it ever starts working."
    ),
)
def test_the_page_handles_the_key_when_nothing_else_will(editor_with):
    """The same key with no menu bar -- `libera --serve` -- must work.

    On macOS this is the real path for a serve-only run. On Linux it is the
    *only* path, and it does not work: see the xfail above, and the known
    issue in docs/src/main/status.md.
    """
    editor = editor_with([])
    editor.press("Meta+n")
    # Create New offers a choice now, with the editor's own kind in focus, so
    # Return is what makes the document the key used to make at once.
    editor.page.keyboard.press("Enter")
    editor.page.wait_for_timeout(1500)

    assert editor.asked_for("new") == 1


def test_the_page_declines_the_key_without_claiming_it(editor_with):
    """Declining and swallowing are one line apart and opposite.

    stopImmediatePropagation stops the editor's own handler, which is wanted.
    preventDefault marks the event handled, WKWebView reports that to AppKit as
    "the page took it", and the menu item does not fire either. Both together
    is the obvious thing to write, and it makes Cmd-N do nothing at all.
    """
    editor = editor_with([s.as_json() for s in menu.PAGE_YIELDS])
    editor.press("Meta+n")

    assert editor.saw("n") > 0, "the keystroke reached no frame"
    assert editor.asked_for("new") == 0, "the page acted on a key the menu owns"
    assert not editor.claimed("n"), (
        "the page claimed the key, so the menu will not fire"
    )
