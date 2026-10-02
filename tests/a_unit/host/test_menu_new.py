"""File > New makes any kind of document, from any window.

It made the front window's kind only. With a document open, the start window
(which offers every kind) is gone, so a user in Words had no way to a new
spreadsheet: one of the two halves of a beta tester's "impossible to have two
documents of different types open at once".
"""

from __future__ import annotations

import sys

import pytest
from webview.menu import Menu

from libera.host import apps, session, window
from libera.host.menu import actions, gtk


def test_new_offers_every_kind_that_can_be_created():
    # Diagrams is a viewer, with no blank to start from.
    assert actions.list_creatable() == (apps.WORDS, apps.TABLES, apps.SLIDES)


def test_each_new_item_on_the_linux_bar_makes_its_own_kind(monkeypatch):
    """One item per kind, each bound to its own: the loop-binding trap again."""
    made = []
    monkeypatch.setattr(actions, "open_new_document", made.append)
    file_menu = next(m for m in gtk.make_menubar() if m.title == "File")
    new = next(i for i in file_menu.items if isinstance(i, Menu) and i.title == "New")

    assert [i.title for i in new.items] == ["Document", "Spreadsheet", "Presentation"]
    for item in new.items:
        item.function()
    assert made == [apps.WORDS, apps.TABLES, apps.SLIDES]


@pytest.fixture
def front(monkeypatch, tmp_path):
    """Make a session of a given document the front window's."""

    def put_in_front(document: str | None):
        found = session.Session(
            payload=tmp_path,
            work=tmp_path / "w",
            document=tmp_path / document if document else None,
        )
        monkeypatch.setattr(window, "find_front_session", lambda: found)

    return put_in_front


@pytest.mark.parametrize(
    ("document", "kind"),
    [
        ("budget.xlsx", apps.TABLES),
        ("deck.pptx", apps.SLIDES),
        ("notes.docx", apps.WORDS),
        # The start window: no document, so ⌘N makes a document.
        (None, apps.WORDS),
        # A viewer cannot make its own kind, so ⌘N makes a document there too.
        ("network.vsdx", apps.WORDS),
    ],
)
def test_command_n_makes_the_front_windows_kind(front, document, kind):
    front(document)
    assert actions.choose_new_kind() == kind


def test_command_n_with_no_window_makes_a_document(monkeypatch):
    monkeypatch.setattr(window, "find_front_session", lambda: None)
    assert actions.choose_new_kind() == apps.WORDS


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit")
def test_command_n_sits_on_exactly_one_item_of_the_mac_submenu():
    import AppKit

    from libera.host.menu import macos

    menu = AppKit.NSMenu.alloc().initWithTitle_("New")
    for app in actions.list_creatable():
        item = menu.addItemWithTitle_action_keyEquivalent_(app.noun, None, "")
        item.setRepresentedObject_(app.name)

    for kind in actions.list_creatable():
        macos.give_new_its_key(menu, kind)
        keyed = [
            str(menu.itemAtIndex_(i).title())
            for i in range(menu.numberOfItems())
            if str(menu.itemAtIndex_(i).keyEquivalent()) == "n"
        ]
        assert keyed == [kind.noun]
