"""A window in the top left corner that offers files to a drag, as a file manager
does: `text/uri-list`, which is all Thunar offered, measured on 2026-11-04.

    drag_source.py FILE...
"""

from __future__ import annotations

import pathlib
import sys

import gi


def main(names: list[str]) -> None:
    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, Gtk

    uris = [pathlib.Path(name).as_uri() for name in names]

    button = Gtk.Button(label="drag")
    button.drag_source_set(
        Gdk.ModifierType.BUTTON1_MASK,
        [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
        Gdk.DragAction.COPY,
    )
    button.connect("drag-data-get", lambda _w, _c, data, _i, _t: data.set_uris(uris))

    window = Gtk.Window(title="drag-source")
    window.set_decorated(False)
    window.set_default_size(150, 150)
    window.move(0, 0)
    window.add(button)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


main(sys.argv[1:])
