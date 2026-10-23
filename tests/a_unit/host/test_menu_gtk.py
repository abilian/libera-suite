"""The Linux bar, which nothing on a Mac would otherwise build.

macOS has `test_menu.py`: a selector nobody implements does nothing, silently.
GTK's equivalent failure is quieter still. pywebview keeps a `MenuAction`'s
function in a dict and calls it on a thread, so an item wired to the wrong
callable raises where nobody is reading -- and `make_menubar()` runs once, before
`start()`, on the one platform this suite does not run on.

So build the bar here and look at it.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import webview
from webview.menu import Menu, MenuAction, MenuSeparator

from libera.host import apps
from libera.host.menu import actions, gtk


def items(menu: Menu) -> list:
    return menu.items


def by_title(bar: list, title: str) -> Menu:
    return next(m for m in bar if m.title == title)


def every_action(node) -> list[MenuAction]:
    if isinstance(node, MenuAction):
        return [node]
    if isinstance(node, Menu):
        return [a for item in node.items for a in every_action(item)]
    return []


def test_the_bar_has_the_menus_a_desktop_expects():
    assert [m.title for m in gtk.make_menubar()] == ["File", "Edit", "View", "Help"]


def test_every_item_is_wired_to_something_callable():
    found = [a for menu in gtk.make_menubar() for a in every_action(menu)]
    # The count is a floor, not a fixture: it fails when a menu comes back
    # empty, which is what a renamed `actions` function would do.
    assert len(found) >= 12
    for action in found:
        assert callable(action.function), action.title


def test_separators_survive_into_the_menus():
    file_menu = by_title(gtk.make_menubar(), "File")
    assert any(isinstance(i, MenuSeparator) for i in items(file_menu))


def test_no_open_recent_when_nothing_is_remembered(monkeypatch):
    monkeypatch.setattr(actions, "read_recent_documents", list)
    file_menu = by_title(gtk.make_menubar(), "File")
    submenus = [i.title for i in items(file_menu) if isinstance(i, Menu)]
    assert "Open Recent" not in submenus


def test_each_recent_item_opens_its_own_document(monkeypatch):
    """The bug this file exists for.

    A comprehension keeps one binding across its iterations, so a lambda over
    the loop variable gives every item the last path -- a menu of five
    documents that all open the fifth. Nothing about it looks wrong.
    """
    paths = ["/docs/one.docx", "/docs/two.xlsx", "/docs/three.pptx"]
    monkeypatch.setattr(actions, "read_recent_documents", lambda: paths)
    opened: list[str] = []
    monkeypatch.setattr(actions, "open_recent", opened.append)

    recent = next(
        i
        for i in items(by_title(gtk.make_menubar(), "File"))
        if isinstance(i, Menu) and i.title == "Open Recent"
    )
    assert [i.title for i in recent.items] == [Path(p).name for p in paths]

    for item in recent.items:
        item.function()
    assert opened == paths


def test_ctrl_n_is_on_the_new_item_of_the_front_kind_alone():
    owned = gtk.list_owned_keys(apps.TABLES)
    assert owned == {
        "_File_New_Document": [],
        "_File_New_Spreadsheet": ["<Control>n"],
        "_File_New_Presentation": [],
        "_File_Open…": ["<Control>o"],
        "_File_Close": ["<Control>w"],
    }


class FakeApplication:
    """What `install` asks of pywebview's Gtk.Application."""

    def __init__(self) -> None:
        self.accels: dict[str, list[str]] = {}
        self.on_front = None

    def set_accels_for_action(self, name: str, keys: list[str]) -> None:
        self.accels[name] = keys

    def connect(self, signal: str, handler) -> None:
        assert signal == "notify::active-window"
        self.on_front = handler


def test_ctrl_n_follows_the_window_that_comes_to_the_front(monkeypatch):
    application = FakeApplication()
    # The GUI loop, run at once: idle_add calls until the callback says no more.
    glib = SimpleNamespace(idle_add=lambda f: f() and pytest.fail("repeats"))
    monkeypatch.setattr(webview, "guilib", SimpleNamespace(_app=application, glib=glib))
    monkeypatch.setattr(actions, "choose_new_kind", lambda: apps.WORDS)
    gtk.install()
    assert application.accels["app._File_New_Document"] == ["<Control>n"]

    monkeypatch.setattr(actions, "choose_new_kind", lambda: apps.SLIDES)
    assert application.on_front is not None
    application.on_front()
    assert application.accels["app._File_New_Presentation"] == ["<Control>n"]
    assert application.accels["app._File_New_Document"] == []


def test_winforms_gets_no_accelerators(monkeypatch):
    """Only the GTK backend has an application; the page runs the keys there."""
    monkeypatch.setattr(webview, "guilib", SimpleNamespace())
    gtk.install()


def test_the_names_are_the_ones_pywebview_gives(monkeypatch):
    """`action_name` restates pywebview's rule, so it is checked against
    pywebview's own `create_menu`, where GTK can be imported."""
    pytest.importorskip("gi")
    from webview.platforms import gtk as backend

    made: list[str] = []
    monkeypatch.setattr(
        backend, "_app", SimpleNamespace(add_action=lambda a: made.append(a.get_name()))
    )
    monkeypatch.setattr(backend, "_app_actions", {})
    backend.create_menu(gtk.make_menubar())
    assert set(gtk.list_owned_keys(apps.WORDS)) <= set(made)
