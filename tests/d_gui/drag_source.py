"""A window in the top left corner that offers files to a drag, as a file manager
does. On X `text/uri-list`, which is all Thunar offered, measured on 2026-11-04;
on Windows a file drop, from a WinForms window and not from Explorer.

    drag_source.py FILE...
"""

from __future__ import annotations

import pathlib
import sys


def offer_on_x(names: list[str]) -> None:
    import gi

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


def offer_on_windows(names: list[str]) -> None:
    import clr

    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    from System import Array, String
    from System.Drawing import Point, Size
    from System.Threading import ApartmentState, Thread, ThreadStart
    from System.Windows.Forms import (
        Application,
        DataFormats,
        DataObject,
        DragDropEffects,
        Form,
        FormBorderStyle,
        FormStartPosition,
    )

    paths = Array[String](names)

    def run() -> None:
        form = Form()
        form.Text = "drag-source"
        form.FormBorderStyle = getattr(FormBorderStyle, "None")
        form.StartPosition = FormStartPosition.Manual
        form.Location = Point(0, 0)
        form.Size = Size(150, 150)
        form.TopMost = True
        form.MouseDown += lambda _sender, _event: form.DoDragDrop(
            DataObject(DataFormats.FileDrop, paths), DragDropEffects.Copy
        )
        Application.Run(form)

    # DoDragDrop needs a single-threaded apartment, which Python's main thread is not.
    thread = Thread(ThreadStart(run))
    thread.SetApartmentState(ApartmentState.STA)
    thread.Start()
    thread.Join()


if sys.platform == "win32":
    offer_on_windows(sys.argv[1:])
else:
    offer_on_x(sys.argv[1:])
