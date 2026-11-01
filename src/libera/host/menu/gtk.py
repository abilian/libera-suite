"""The Linux menu bar.

The other upper layer. It reads `actions` for what the items do, the same
functions AppKit's selectors call, and nothing in `actions` reads back.

pywebview's GTK backend turns a list of `webview.Menu` into a `Gio.Menu` and
hands it to `Gtk.Application.set_menubar`. That is the menu GNOME stopped
exporting in 3.32, so the worry was that it would render nowhere -- but
pywebview's windows are `Gtk.ApplicationWindow`s, which draw the application's
menubar themselves whenever the shell has not claimed it. Measured before
relying on it: `lb linux gui` screenshots File, Edit, View and Help across
the top of the window. So the whole bar is one list, handed to
`webview.start(menu=...)` before the application starts.

**Three key equivalents: Ctrl-N, Ctrl-O and Ctrl-W**, the keys the editor has
no use for, as on the Mac. `webview.MenuAction` has no shortcut, but pywebview
names each item's `Gio.SimpleAction` after its menu path on its own
`Gtk.Application`, so `install` gives those three actions accelerators, and
GTK prints each beside its item. The key is then the menu's: a window runs its
accelerators before WebKit sees the event (measured in the Linux container:
Ctrl-N made one window, through the menu, and the page never saw it), so the
page runs them on Windows only (`shortcuts.PAGE_RUNS`). Ctrl-N follows the
front window, onto the New item of its kind, as AppKit's does. The editor's own
keys, Ctrl-S, Ctrl-Z, Ctrl-F and the rest, get none: bound, they would be
taken from its text fields too, the find box and a cell being edited among
them, where Ctrl-Z undoes the field and not the document.

**Built once, before the application runs**, because that is the only moment
pywebview reads it. Open Recent therefore lists what was remembered at
startup: opening a document during the session does not add a line to it until
the next launch; a first-ever run has no Open Recent submenu at all. The
alternative is reaching into `webview.platforms.gtk._app` and calling
`set_menubar` again, where the action names collide on a second
build -- `create_menu` appends an underscore until the name is free -- so a
rebuilt bar leaks a dead action per item.

**Nothing greys out.** `actions.is_enabled` decides that on the Mac, through
validateMenuItem:. Gio's equivalent is `Gio.SimpleAction.set_enabled` on an
action pywebview owns and names by a rule of its own. Save on an unmodified
document and Undo with an empty history therefore stay available here and do
nothing when used, which is what the same keystrokes already do inside the
page.

**No Edit > Cut, Copy or Paste.** WebKitGTK does them through
`execute_editing_command`, which pywebview does not expose, and the keystrokes
already work in the page. A menu item that does nothing is worse than an
absent one.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

import webview
from webview.menu import Menu, MenuAction, MenuSeparator

from libera.host import apps, language, shortcuts
from libera.host.menu import actions


def make_menubar() -> list:
    """The bar, for `webview.start(menu=...)`.

    Linux and Windows both: pywebview's WinForms backend draws the same list
    as each window's menu strip.
    """
    # No submenu when nothing is remembered: Gio has no disabled item pywebview
    # can reach, so "No Recent Documents" would be a live item that does
    # nothing, which reads as broken.
    remembered = actions.read_recent_documents()

    # partial, because a comprehension keeps one binding for all
    # of its iterations, so `lambda: open_recent(path)` would give every item
    # the last document. ruff B023 says the same thing.
    recent: list = (
        [
            Menu(
                language.translate("Open Recent"),
                [
                    MenuAction(Path(path).name, partial(actions.open_recent, path))
                    for path in remembered
                ],
            )
        ]
        if remembered
        else []
    )

    return [
        Menu(
            language.translate("File"),
            [
                Menu(
                    language.translate("New"),
                    [
                        MenuAction(
                            language.translate(app.noun),
                            partial(actions.open_new_document, app),
                        )
                        for app in actions.list_creatable()
                    ],
                ),
                MenuAction(language.translate("Open…"), actions.open_document),
                *recent,
                MenuSeparator(),
                MenuAction(language.translate("Save"), actions.save),
                MenuAction(language.translate("Save As…"), actions.save_as),
                MenuAction(language.translate("Print…"), actions.print_document),
                MenuSeparator(),
                MenuAction(language.translate("Reload"), actions.reload_document),
                MenuAction(language.translate("Close"), actions.close_window),
            ],
        ),
        Menu(
            language.translate("Edit"),
            [
                MenuAction(language.translate("Undo"), actions.undo),
                MenuAction(language.translate("Redo"), actions.redo),
                MenuSeparator(),
                MenuAction(language.translate("Find…"), actions.find),
            ],
        ),
        Menu(
            language.translate("View"),
            [
                MenuAction(language.translate("Zoom In"), actions.zoom_in),
                MenuAction(language.translate("Zoom Out"), actions.zoom_out),
                MenuAction(language.translate("Fit Page"), actions.fit_page),
                MenuAction(language.translate("Fit Width"), actions.fit_width),
                MenuSeparator(),
                MenuAction(
                    language.translate("Formatting Marks"),
                    actions.toggle_formatting_marks,
                ),
            ],
        ),
        Menu(
            language.translate("Help"),
            [
                MenuAction(language.translate("Libera Help"), actions.show_help),
                MenuSeparator(),
                # macOS gets this from the application menu, which reads
                # NSHumanReadableCopyright out of the bundle. GTK has no
                # equivalent, so the item is explicit here.
                MenuAction(
                    language.translate("About Libera Suite"), actions.show_about
                ),
            ],
        ),
    ]


def action_name(*path: str) -> str:
    """The action pywebview's `create_menu` makes for the item at `path`."""
    return "_".join(["", *path]).replace(" ", "_")


def accelerator(key: shortcuts.Shortcut) -> str:
    return ("<Control><Shift>" if key.shift else "<Control>") + key.key


def list_owned_keys(front: apps.App) -> dict[str, list[str]]:
    """Each File item's action, and the accelerators it gets with `front` the
    kind of the window in front: Ctrl-N goes to that kind's New item alone."""
    file_menu, new = language.translate("File"), language.translate("New")
    owned = {
        action_name(file_menu, new, language.translate(app.noun)): (
            [accelerator(shortcuts.NEW)] if app is front else []
        )
        for app in actions.list_creatable()
    }
    owned[action_name(file_menu, language.translate("Open…"))] = [
        accelerator(shortcuts.OPEN)
    ]
    owned[action_name(file_menu, language.translate("Close"))] = [
        accelerator(shortcuts.CLOSE)
    ]
    return owned


def install() -> None:
    """The keys `list_owned_keys` gives, set again whenever another window
    comes to the front, so that Ctrl-N follows it.

    Only pywebview's GTK backend has an application to hold accelerators; on
    WinForms there is none, and the page runs the keys. Called on pywebview's
    startup thread, so every GTK call goes through the GUI loop.
    """
    backend = webview.guilib
    application = getattr(backend, "_app", None)
    if application is None:
        return
    glib = backend.__dict__["glib"]  # the GTK backend's own GLib

    def follow_front(*_: object) -> bool:
        for name, keys in list_owned_keys(actions.choose_new_kind()).items():
            application.set_accels_for_action(f"app.{name}", keys)
        return False  # once: idle_add repeats a callback that returns true

    def start() -> bool:
        follow_front()
        application.connect("notify::active-window", follow_front)
        return False

    glib.idle_add(start)
