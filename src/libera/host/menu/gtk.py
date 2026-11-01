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

**No key equivalents, by design.** `webview.MenuAction` has no shortcut,
while the editor already owns Ctrl-S, Ctrl-P, Ctrl-Z and the rest inside the
page. A menu accelerator would be a
second handler for a key that already works, which is the doubling PAGE_YIELDS
exists to prevent on the Mac. The items here are the ones the page has no
equivalent for: New, Open, Open Recent, Reload, Close.

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

from webview.menu import Menu, MenuAction, MenuSeparator

from libera.host import language
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


def install() -> None:
    """Nothing: the bar went to `webview.start`, and GTK reads it only then."""
