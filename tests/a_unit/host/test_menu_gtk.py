"""The Linux bar, which nothing on a Mac would otherwise build.

macOS has `test_menu.py`: a selector nobody implements does nothing, silently.
GTK's equivalent failure is quieter still. pywebview keeps a `MenuAction`'s
function in a dict and calls it on a thread, so an item wired to the wrong
callable raises where nobody is reading -- and `menubar()` runs once, before
`start()`, on the one platform this suite does not run on.

So build the bar here and look at it.
"""

from __future__ import annotations

from pathlib import Path

from webview.menu import Menu, MenuAction, MenuSeparator

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
    assert [m.title for m in gtk.menubar()] == ["File", "Edit", "View", "Help"]


def test_every_item_is_wired_to_something_callable():
    found = [a for menu in gtk.menubar() for a in every_action(menu)]
    # The count is a floor, not a fixture: it fails when a menu comes back
    # empty, which is what a renamed `actions` function would do.
    assert len(found) >= 12
    for action in found:
        assert callable(action.function), action.title


def test_separators_survive_into_the_menus():
    file_menu = by_title(gtk.menubar(), "File")
    assert any(isinstance(i, MenuSeparator) for i in items(file_menu))


def test_no_open_recent_when_nothing_is_remembered(monkeypatch):
    monkeypatch.setattr(actions, "recent_documents", list)
    file_menu = by_title(gtk.menubar(), "File")
    assert not [i for i in items(file_menu) if isinstance(i, Menu)]


def test_each_recent_item_opens_its_own_document(monkeypatch):
    """The bug this file exists for.

    A comprehension keeps one binding across its iterations, so a lambda over
    the loop variable gives every item the last path -- a menu of five
    documents that all open the fifth. Nothing about it looks wrong.
    """
    paths = ["/docs/one.docx", "/docs/two.xlsx", "/docs/three.pptx"]
    monkeypatch.setattr(actions, "recent_documents", lambda: paths)
    opened: list[str] = []
    monkeypatch.setattr(actions, "open_recent", opened.append)

    recent = next(
        i for i in items(by_title(gtk.menubar(), "File")) if isinstance(i, Menu)
    )
    assert recent.title == "Open Recent"
    assert [i.title for i in recent.items] == [Path(p).name for p in paths]

    for item in recent.items:
        item.function()
    assert opened == paths
