"""The Linux menu bar.

The other upper half. It reads `actions` for what the items do, the same
functions AppKit's selectors call, and nothing in `actions` reads back.

pywebview's GTK backend turns a list of `webview.Menu` into a `Gio.Menu` and
hands it to `Gtk.Application.set_menubar`. That is the menu GNOME stopped
exporting in 3.32, so the worry was that it would render nowhere -- but
pywebview's windows are `Gtk.ApplicationWindow`s, which draw the application's
menubar themselves whenever the shell has not claimed it. Measured before
relying on it: `make gui-linux` screenshots File, Edit, View and Help across
the top of the window. So the whole bar is one list, handed to
`webview.start(menu=...)` before the application starts.

**No key equivalents, by design.** `webview.MenuAction` carries no shortcut,
and the editor already owns Ctrl-S, Ctrl-P, Ctrl-Z and the rest inside the
page. A menu accelerator would be a
second handler for a key that already works, which is the doubling PAGE_YIELDS
exists to prevent on the Mac. The items worth having here are the ones the
page has no equivalent for: New, Open, Open Recent, Reload, Close.

**Built once, before the application runs**, because that is the only moment
pywebview reads it. Open Recent therefore lists what was remembered at
startup: opening a document during the session does not add a line to it until
the next launch, and a first-ever run has no Open Recent submenu at all. The
alternative is reaching into `webview.platforms.gtk._app` and calling
`set_menubar` again, and its action names collide on a second
build -- `create_menu` appends an underscore until the name is free -- so a
rebuilt bar leaks a dead action per item.

**Nothing greys out.** `actions.enabled_for` decides that on the Mac, through
validateMenuItem:, and Gio's equivalent is `Gio.SimpleAction.set_enabled` on an
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

from libera.host.menu import actions


def menubar() -> list:
    """The bar, for `webview.start(menu=...)`.

    Returns a plain list so `app.run` can pass it through on Linux and pass
    `[]` everywhere else, which is `start()`'s own default.
    """
    from webview.menu import Menu, MenuAction, MenuSeparator

    # No submenu rather than an empty one: Gio has no disabled item pywebview
    # can reach, so "No Recent Documents" would be a live item that does
    # nothing, which reads as broken.
    remembered = actions.recent_documents()

    # partial rather than a lambda: a comprehension keeps one binding for all
    # of its iterations, so `lambda: open_recent(path)` would give every item
    # the last document. ruff B023 says the same thing.
    recent: list = (
        [
            Menu(
                "Open Recent",
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
            "File",
            [
                MenuAction("New", actions.new_document),
                MenuAction("Open…", actions.open_document),
                *recent,
                MenuSeparator(),
                MenuAction("Save", actions.save),
                MenuAction("Save As…", actions.save_as),
                MenuAction("Print…", actions.print_document),
                MenuSeparator(),
                MenuAction("Reload", actions.reload_document),
                MenuAction("Close", actions.close_window),
            ],
        ),
        Menu(
            "Edit",
            [
                MenuAction("Undo", actions.undo),
                MenuAction("Redo", actions.redo),
                MenuSeparator(),
                MenuAction("Find…", actions.find),
            ],
        ),
        Menu(
            "View",
            [
                MenuAction("Zoom In", actions.zoom_in),
                MenuAction("Zoom Out", actions.zoom_out),
                MenuAction("Fit Page", actions.fit_page),
                MenuAction("Fit Width", actions.fit_width),
                MenuSeparator(),
                MenuAction("Formatting Marks", actions.toggle_formatting_marks),
            ],
        ),
        Menu("Help", [MenuAction("Libera Help", actions.show_help)]),
    ]
