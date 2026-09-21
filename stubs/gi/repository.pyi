from typing import Any

# gi.repository has no modules on disk: an import of Gtk or GLib runs a finder
# that loads a typelib and builds the namespace from it, so there is nothing
# for a checker to read even on a machine that has PyGObject installed.
#
# Declared rather than left out, for the reason in README.md: the names a file
# uses are checked against this list, so a typo is still an error and only the
# members behind them are unknown.
GLib: Any
Gtk: Any
