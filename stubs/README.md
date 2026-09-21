# `stubs/`

Type stubs for the three pyobjc modules the host uses, and for PyGObject. pyobjc ships none, and
its members are built at import time from the Objective-C runtime, so a
checker asked about `AppKit.NSMenuItem` finds nothing and reports fifty
`unresolved-attribute` errors across `menu.py`, `window.py` and `desktop.py`.

**The alternative was to turn that rule off for those files, and that would
have been a mistake.** The rule is how `session.SESSIONS` was caught being
looked up on a `str` — a local shadowing the imported module, raising
`AttributeError` inside every Undo, Redo and Save menu validation. Silencing
the rule silences the bugs it is for.

So these say only what is true: the names exist, and their types are not known
here. Anything else in those files is still checked. A name used but not
listed fails the check, which is the right way round — add it.

`gi/` is the same idea for the other platform. PyGObject exists on Linux and
not on macOS, so a checker on a Mac reports every `gi` import as unresolvable,
which is true there and says nothing about the code. `gi/repository.pyi` has
to exist as well as `gi/__init__.pyi`: `gi.repository` has no modules on disk,
and an import of Gtk or GLib runs a finder that builds the namespace from a
typelib.

Not a substitute for real stubs. If pyobjc ever ships them, delete this.
