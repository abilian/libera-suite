"""The macOS menu bar: AppKit's own, extended once the application runs.

The upper half: it reads `actions` for what each item does, and nothing in
`actions` reads back.

Most of what is here is about AppKit's own menu rather than ours -- pywebview
builds a default bar before we get a look at it, so this extends what is there
(Edit, View, Window, Help) rather than replacing it, and de-duplicates what
appears twice.

Read on macOS alone -- `menu` picks this module or `gtk` as `native`, and both
answer `make_menubar()` and `install()` -- so AppKit is imported once, here.

TARGET and the two delegates are module state because AppKit holds a menu
item's target by an *unretained* pointer: an object that goes out of scope
leaves items wired to freed memory. They are made as the module loads, so no
reader can find one missing.
"""

from __future__ import annotations

import logging
from pathlib import Path

import AppKit

from libera.host import apps, window
from libera.host.menu import actions
from libera.host.shortcuts import COMMAND, NEW, SHIFT

logger = logging.getLogger(__name__)


class LiberaMenuTarget(AppKit.NSObject):
    """Where every item of ours sends its selector."""

    def newDocumentOfKind_(self, sender):
        actions.open_new_document(
            apps.BY_NAME.get(str(sender.representedObject() or ""))
        )

    def reloadDocument_(self, _sender):
        actions.reload_document()

    def openDocument_(self, _sender):
        actions.open_document()

    def openRecent_(self, sender):
        actions.open_recent(str(sender.representedObject() or ""))

    def saveDocument_(self, _sender):
        actions.save()

    def saveDocumentAs_(self, _sender):
        actions.save_as()

    def printDocument_(self, _sender):
        actions.print_document()

    def undo_(self, _sender):
        actions.undo()

    def redo_(self, _sender):
        actions.redo()

    def find_(self, _sender):
        actions.find()

    def zoomIn_(self, _sender):
        actions.zoom_in()

    def zoomOut_(self, _sender):
        actions.zoom_out()

    def zoomFitPage_(self, _sender):
        actions.fit_page()

    def zoomFitWidth_(self, _sender):
        actions.fit_width()

    def toggleFormattingMarks_(self, _sender):
        actions.toggle_formatting_marks()

    def showHelp_(self, _sender):
        actions.show_help()

    def validateMenuItem_(self, item):
        """Grey out what would decline. The decision is in is_enabled()."""
        return actions.is_enabled(str(item.action() or ""), window.find_front_session())


class LiberaRecentMenu(AppKit.NSObject):
    """Rebuilds the Open Recent submenu each time it is opened.

    Building it once would show whatever was remembered when the application
    started, which is wrong the moment a document is opened.
    """

    def menuNeedsUpdate_(self, menu):
        menu.removeAllItems()
        paths = actions.read_recent_documents()
        if not paths:
            empty = menu.addItemWithTitle_action_keyEquivalent_(
                "No Recent Documents", None, ""
            )
            empty.setEnabled_(False)
            return
        for path in paths:
            item = menu.addItemWithTitle_action_keyEquivalent_(
                Path(path).name, "openRecent:", ""
            )
            item.setTarget_(TARGET)
            item.setRepresentedObject_(path)


class LiberaNewMenu(AppKit.NSObject):
    """Puts ⌘N on the New submenu's item for the front window's kind.

    Each time AppKit consults the menu, which it does when the menu opens and
    when it looks for the item a key equivalent belongs to. So ⌘N in Tables
    makes a spreadsheet, as it did when New was one item, while the submenu
    beside it offers every other kind.
    """

    def menuNeedsUpdate_(self, menu):
        give_new_its_key(menu, actions.choose_new_kind())


def give_new_its_key(menu, kind: apps.App) -> None:
    """⌘N on `kind`'s item of the New submenu, and on no other."""
    for index in range(menu.numberOfItems()):
        item = menu.itemAtIndex_(index)
        mine = str(item.representedObject() or "") == kind.name
        item.setKeyEquivalent_(NEW.key if mine else "")
        item.setKeyEquivalentModifierMask_(NEW.mask)


TARGET = LiberaMenuTarget.alloc().init()
RECENT_DELEGATE = LiberaRecentMenu.alloc().init()
NEW_DELEGATE = LiberaNewMenu.alloc().init()


def make_menubar() -> list:
    """Nothing to hand `webview.start`: AppKit builds its own bar.

    install() extends that one, once the application runs and it exists.
    """
    return []


def _add_item(menu, title, selector, key="", mask=COMMAND):
    item = menu.addItemWithTitle_action_keyEquivalent_(title, selector, key)
    if key:
        item.setKeyEquivalentModifierMask_(mask)
    # A standard selector goes to the responder chain and must have no target;
    # ours would never be reached without one.
    if selector and not selector.startswith(("perform", "toggle", "arrangeInFront")):
        item.setTarget_(TARGET)
    return item


def install() -> None:
    """Add Libera Suite's menus to the one pywebview has already built.

    Called once the application is running, because there is no menu to add to
    before that.
    """
    main = AppKit.NSApp.mainMenu()
    if main is None or _has_item(main, "File"):
        return

    file_menu = AppKit.NSMenu.alloc().initWithTitle_("File")
    # New > Document, Spreadsheet, Presentation: any kind from any window. ⌘N
    # sits on the front window's kind, and its delegate moves it there each
    # time the menu is consulted; this puts it somewhere before that happens.
    new_menu = AppKit.NSMenu.alloc().initWithTitle_("New")
    new_menu.setDelegate_(NEW_DELEGATE)
    for app in actions.list_creatable():
        _add_item(new_menu, app.noun, "newDocumentOfKind:").setRepresentedObject_(
            app.name
        )
    give_new_its_key(new_menu, actions.choose_new_kind())
    new_item = file_menu.addItemWithTitle_action_keyEquivalent_("New", None, "")
    new_item.setSubmenu_(new_menu)
    _add_item(file_menu, "Open…", "openDocument:", "o")

    recent = AppKit.NSMenu.alloc().initWithTitle_("Open Recent")
    recent.setDelegate_(RECENT_DELEGATE)
    recent_item = file_menu.addItemWithTitle_action_keyEquivalent_(
        "Open Recent", None, ""
    )
    recent_item.setSubmenu_(recent)

    file_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    # No key equivalent. Reloading is rare, and a shortcut here would be one
    # more key the page also handles -- see PAGE_YIELDS.
    _add_item(file_menu, "Reload", "reloadDocument:")
    file_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    # performClose: is the standard one: it goes through the window's delegate,
    # which is where Libera Suite asks about unsaved changes.
    _add_item(file_menu, "Close", "performClose:", "w")
    _add_item(file_menu, "Save", "saveDocument:", "s")
    _add_item(file_menu, "Save As…", "saveDocumentAs:", "s", COMMAND | SHIFT)
    file_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    _add_item(file_menu, "Print…", "printDocument:", "p")

    file_item = AppKit.NSMenuItem.alloc().init()
    file_item.setTitle_("File")
    file_item.setSubmenu_(file_menu)
    # After the application menu, before Edit, which is where a Mac user looks.
    main.insertItem_atIndex_(file_item, 1)

    _extend_edit(main)
    _fill_view(main)
    _add_window_menu(main)
    _add_help_menu(main)

    for index in range(main.numberOfItems()):
        submenu = main.itemAtIndex_(index).submenu()
        if submenu is not None:
            _dedupe(submenu)


def _dedupe(menu) -> None:
    """Drop repeated items, keeping the first of each.

    macOS adds some of its own -- full screen, and the two above if they got in
    before the defaults did -- and pywebview adds one of the same. A menu with
    "Emoji & Symbols" in it three times is the sort of thing people notice.
    """
    seen = set()
    for index in reversed(range(menu.numberOfItems())):
        item = menu.itemAtIndex_(index)
        if item.isSeparatorItem():
            continue
        key = (str(item.title()), str(item.action() or ""))
        if key in seen:
            menu.removeItemAtIndex_(index)
        else:
            seen.add(key)


def _has_item(main, title: str) -> bool:
    for i in range(main.numberOfItems()):
        if str(main.itemAtIndex_(i).title()) == title:
            return True
    return False


def _find_submenu(main, title: str):
    for i in range(main.numberOfItems()):
        item = main.itemAtIndex_(i)
        if item.submenu() is not None and str(item.submenu().title()) == title:
            return item.submenu()
    return None


def _extend_edit(main) -> None:
    """Undo and Redo, which pywebview's Edit menu does not carry.

    Not the standard undo: and redo: selectors -- those drive NSUndoManager,
    which knows nothing about the editor's own history.
    """
    edit = _find_submenu(main, "Edit")
    if edit is None:
        return
    undo = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Undo", "undo:", "z"
    )
    undo.setTarget_(TARGET)
    redo = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Redo", "redo:", "z"
    )
    redo.setKeyEquivalentModifierMask_(COMMAND | SHIFT)
    redo.setTarget_(TARGET)
    edit.insertItem_atIndex_(undo, 0)
    edit.insertItem_atIndex_(redo, 1)
    edit.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), 2)

    find = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Find…", "find:", "f"
    )
    find.setTarget_(TARGET)
    edit.addItem_(AppKit.NSMenuItem.separatorItem())
    edit.addItem_(find)


def _fill_view(main) -> None:
    """Give the View menu something to show.

    pywebview puts one item in it, Enter Fullscreen, and macOS hides that as a
    duplicate of the one it manages itself -- leaving a menu that opens onto
    nothing, which is worse than not having the menu at all.
    """
    view = _find_submenu(main, "View")
    if view is None:
        return
    # Insert above whatever is there, so the system's full-screen item stays
    # at the bottom where macOS puts it.
    items = [
        ("Zoom In", "zoomIn:", "+", COMMAND),
        ("Zoom Out", "zoomOut:", "-", COMMAND),
        ("Fit Page", "zoomFitPage:", "0", COMMAND),
        ("Fit Width", "zoomFitWidth:", "0", COMMAND | SHIFT),
        (None, None, None, None),
        ("Formatting Marks", "toggleFormattingMarks:", "8", COMMAND),
        # No trailing separator: the only thing below is the full-screen item,
        # which macOS hides, and a menu that ends in a divider looks broken.
    ]
    for index, (title, selector, key, mask) in enumerate(items):
        if title is None:
            view.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), index)
            continue
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, selector, key
        )
        item.setKeyEquivalentModifierMask_(mask)
        item.setTarget_(TARGET)
        view.insertItem_atIndex_(item, index)


def _add_window_menu(main) -> None:
    """A Window menu, which macOS then keeps the window list in itself."""
    window_menu = AppKit.NSMenu.alloc().initWithTitle_("Window")
    _add_item(window_menu, "Minimize", "performMiniaturize:", "m")
    _add_item(window_menu, "Zoom", "performZoom:")
    window_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    _add_item(window_menu, "Bring All to Front", "arrangeInFront:")

    item = AppKit.NSMenuItem.alloc().init()
    item.setTitle_("Window")
    item.setSubmenu_(window_menu)
    main.addItem_(item)
    # Handing it to the application is what makes the open windows appear in it
    # and stay in step, which is most of the value of having one.
    AppKit.NSApp.setWindowsMenu_(window_menu)


def _add_help_menu(main) -> None:
    help_menu = AppKit.NSMenu.alloc().initWithTitle_("Help")
    _add_item(help_menu, "Libera Help", "showHelp:", "?")

    item = AppKit.NSMenuItem.alloc().init()
    item.setTitle_("Help")
    item.setSubmenu_(help_menu)
    main.addItem_(item)
    AppKit.NSApp.setHelpMenu_(help_menu)
