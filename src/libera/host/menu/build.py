"""Putting the menu bar together, once, at startup.

The upper half: it reads `actions` for the target to wire items to, and
nothing in `actions` reads back.

Most of what is here is about AppKit's own menu rather than ours -- pywebview
builds a default bar before we get a look at it, so this extends what is there
(Edit, View, Window, Help) rather than replacing it, and de-duplicates what
appears twice.
"""

from __future__ import annotations

import logging
from importlib import resources

from libera.host.menu import actions
from libera.host.shortcuts import COMMAND, NEW, SHIFT

logger = logging.getLogger(__name__)


def _item(menu, title, selector, key="", mask=COMMAND):
    item = menu.addItemWithTitle_action_keyEquivalent_(title, selector, key)
    if key:
        item.setKeyEquivalentModifierMask_(mask)
    # A standard selector goes to the responder chain and must have no target;
    # ours would never be reached without one.
    if selector and not selector.startswith(("perform", "toggle", "arrangeInFront")):
        item.setTarget_(actions.TARGET)
    return item


def install() -> None:
    """Add Libera Suite's menus to the one pywebview has already built.

    Called once the application is running, because there is no menu to add to
    before that.
    """
    import AppKit

    main = AppKit.NSApp.mainMenu()
    if main is None or _has(main, "File"):
        return

    _wear_the_application_icon()

    actions.TARGET = actions.target_class().alloc().init()
    actions.RECENT_DELEGATE = actions.recent_delegate_class().alloc().init()

    file_menu = AppKit.NSMenu.alloc().initWithTitle_("File")
    _item(file_menu, "New", "newDocument:", NEW.key, NEW.mask)
    _item(file_menu, "Open…", "openDocument:", "o")

    recent = AppKit.NSMenu.alloc().initWithTitle_("Open Recent")
    recent.setDelegate_(actions.RECENT_DELEGATE)
    recent_item = file_menu.addItemWithTitle_action_keyEquivalent_(
        "Open Recent", None, ""
    )
    recent_item.setSubmenu_(recent)

    file_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    # No key equivalent. Reloading is rare, and a shortcut here would be one
    # more key the page also handles -- see PAGE_YIELDS.
    _item(file_menu, "Reload", "reloadDocument:")
    file_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    # performClose: is the standard one: it goes through the window's delegate,
    # which is where Libera Suite asks about unsaved changes.
    _item(file_menu, "Close", "performClose:", "w")
    _item(file_menu, "Save", "saveDocument:", "s")
    _item(file_menu, "Save As…", "saveDocumentAs:", "s", COMMAND | SHIFT)
    file_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    _item(file_menu, "Print…", "printDocument:", "p")

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


def name_the_application() -> None:
    """Say Libera, not Python, in the menu bar and in what the system reports.

    Outside `Libera.app` the running process's main bundle is the interpreter's
    own -- Homebrew's `Python.app`, whose CFBundleName is "Python". So a
    developer running `libera` got "About Python" and "Hide Python" in the
    application menu, and "Python" as the bold item in the menu bar.

    The main bundle's info dictionary is mutable and both names come out of it,
    so setting them fixes the menu at the source: AppKit builds the titles from
    the right name rather than being corrected item by item afterwards, which
    is what this replaced and which only ever reached the titles somebody had
    thought of. Measured after the change: "Libera" in the menu bar, "About
    Libera" in the menu, and "Libera Suite" from `lsappinfo` and from another
    process's `NSRunningApplication.localizedName()`.

    **Before `NSApplication.sharedApplication()`, and that is the whole
    constraint.** Measured: the same two lines after the shared application
    exists change nothing at all, not even before `setActivationPolicy_`. So
    this runs from `app.run` ahead of `webview.start()`, and it cannot move
    into `install()` with the rest of the menu work.

    Both keys, mirroring `build/macos-app.sh`'s Info.plist: CFBundleName is the
    menu bar, CFBundleDisplayName is what the system reports elsewhere. Inside
    the bundle both already hold these values, so this is a no-op there.

    **It does not fix the Dock tile's name, and nothing here can.** That name
    is the bundle's *filename* on disk, which for us is `Python.app` and is not
    ours to rename. Measured against the tile itself, three ways: this change
    leaves it at "Python"; the private `_LSSetApplicationInformationItem` sets
    the LaunchServices display name, which is already "Libera Suite" and which
    the tile plainly ignores; and the same build launched as `Libera.app` reads
    "Libera", as `Libera Suite.app` reads "Libera Suite". The icon has an
    override (`_wear_the_application_icon`) because AppKit messages the Dock
    for that one; the name has no counterpart. A bundle is the answer.

    **Check any of this from outside the process**, because every reading
    available in here lies in both directions:
    `NSRunningApplication.currentApplication()` reports the dictionary it was
    just handed whether or not it took, `NSWorkspace.frontmostApplication()`
    reported "Python" for a run whose menu bar was on screen saying Libera, and
    `lsappinfo` reported "Libera Suite" for a run whose Dock tile said Python.
    For the tile, ask the Dock:

        osascript -e 'tell application "System Events" to tell process "Dock"
                      to get name of every UI element of list 1'
    """
    import Foundation

    info = Foundation.NSBundle.mainBundle().infoDictionary()
    info["CFBundleName"] = "Libera"
    info["CFBundleDisplayName"] = "Libera Suite"


def _wear_the_application_icon() -> None:
    """Show the Libera mark in the Dock, not Python's rocket.

    The same gap as `name_the_application`, and the other half of what that
    fixes: the Dock takes its icon from the running process's main bundle, and
    outside `Libera.app` that bundle is the interpreter's. So `libera` from a
    virtualenv came up under a rocket. setApplicationIconImage_ overrides it
    for the life of the process, and it is harmless inside the bundle, where it
    sets the icon to the drawing the .icns was made from.

    Unlike the name, this one cannot run early: it needs `NSApp`, and the name
    has to be set *before* anything creates it. So the two sit at opposite ends
    of startup on purpose.

    `icon.svg` ships in the wheel and is the one copy of the mark in the
    repository; `build/macos-icon.py` and `build/flatpak.sh` read the same file.

    NSImage has read SVG only since macOS 13. On 11 and 12 it returns nil, and
    then there is nothing to do but leave the rocket -- an application that
    launches with the wrong icon is better than one that does not launch. The
    bundle is unaffected either way, because its icon is an .icns.
    """
    import AppKit

    # resources.files, not Path(__file__).parents[2]: the icon is package data
    # two directories up from this module, and counting parents is how six test
    # files broke the moment they moved. See notes/lessons-learned.md.
    icon = resources.files("libera") / "icon.svg"
    image = AppKit.NSImage.alloc().initWithContentsOfFile_(str(icon))
    if image is None:
        logger.debug("no Dock icon: %s did not read as an image", icon)
        return
    AppKit.NSApp.setApplicationIconImage_(image)


def quieten_system_items() -> None:
    """Stop macOS adding Dictation and Emoji & Symbols to the Edit menu.

    It adds them to any menu titled Edit, and it added each of them more than
    once here. These are the documented off-switches, but they are only read
    while the menu is being built -- so this has to run before the application
    starts, not when the menus are extended.

    registerDefaults_ rather than setBool_forKey_: the former lives for the
    process, the latter writes into the user's preferences for whatever bundle
    we happen to be running as.
    """
    import Foundation

    Foundation.NSUserDefaults.standardUserDefaults().registerDefaults_({
        "NSDisabledDictationMenuItem": True,
        "NSDisabledCharacterPaletteMenuItem": True,
    })


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


def _has(main, title: str) -> bool:
    for i in range(main.numberOfItems()):
        if str(main.itemAtIndex_(i).title()) == title:
            return True
    return False


def _submenu(main, title: str):
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
    import AppKit

    edit = _submenu(main, "Edit")
    if edit is None:
        return
    undo = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Undo", "undo:", "z"
    )
    undo.setTarget_(actions.TARGET)
    redo = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Redo", "redo:", "z"
    )
    redo.setKeyEquivalentModifierMask_(COMMAND | SHIFT)
    redo.setTarget_(actions.TARGET)
    edit.insertItem_atIndex_(undo, 0)
    edit.insertItem_atIndex_(redo, 1)
    edit.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), 2)

    find = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Find…", "find:", "f"
    )
    find.setTarget_(actions.TARGET)
    edit.addItem_(AppKit.NSMenuItem.separatorItem())
    edit.addItem_(find)


def _fill_view(main) -> None:
    """Give the View menu something to show.

    pywebview puts one item in it, Enter Fullscreen, and macOS hides that as a
    duplicate of the one it manages itself -- leaving a menu that opens onto
    nothing, which is worse than not having the menu at all.
    """
    import AppKit

    view = _submenu(main, "View")
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
        item.setTarget_(actions.TARGET)
        view.insertItem_atIndex_(item, index)


def _add_window_menu(main) -> None:
    """A Window menu, which macOS then keeps the window list in itself."""
    import AppKit

    window_menu = AppKit.NSMenu.alloc().initWithTitle_("Window")
    _item(window_menu, "Minimize", "performMiniaturize:", "m")
    _item(window_menu, "Zoom", "performZoom:")
    window_menu.addItem_(AppKit.NSMenuItem.separatorItem())
    _item(window_menu, "Bring All to Front", "arrangeInFront:")

    item = AppKit.NSMenuItem.alloc().init()
    item.setTitle_("Window")
    item.setSubmenu_(window_menu)
    main.addItem_(item)
    # Handing it to the application is what makes the open windows appear in it
    # and stay in step, which is most of the value of having one.
    AppKit.NSApp.setWindowsMenu_(window_menu)


def _add_help_menu(main) -> None:
    import AppKit

    help_menu = AppKit.NSMenu.alloc().initWithTitle_("Help")
    _item(help_menu, "Libera Help", "showHelp:", "?")

    item = AppKit.NSMenuItem.alloc().init()
    item.setTitle_("Help")
    item.setSubmenu_(help_menu)
    main.addItem_(item)
    AppKit.NSApp.setHelpMenu_(help_menu)
