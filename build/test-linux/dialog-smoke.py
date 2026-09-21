"""Does the GTK question actually reach the screen, and come back?

`dialogs._gtk_ask` is the Linux half of three questions the host has to ask:
save before closing, recover unsaved edits, reload a wedged editor. All three
returned "no" without asking before, and the one that mattered lost work.

What can go wrong here is not the wording. It is the threading. A dialog built
on the wrong thread never appears; `dialog.run()` called off the GTK thread
hangs; a worker that hands the work over with idle_add and forgets to wait
reads its answer before there is one. So this drives both paths -- from the
GTK thread and from a worker -- and asserts on the answer that came back.

The response is emitted from the main loop rather than clicked, because there
is no pointer in here. What that leaves untested is the click itself; what it
covers is every part of the hand-off, which is the part that was written today.

Run under xvfb-run, with libera importable.
"""

from __future__ import annotations

import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # ruff: ignore[module-import-not-at-top-of-file] -- require_version comes first

from libera.host.window import dialogs  # ruff: ignore[module-import-not-at-top-of-file] -- and so does gi's

BUTTONS = ("Save", "Cancel", "Don't Save")
WANTED = 2  # "Don't Save", the last button, so an off-by-one shows up


def answer_the_dialog(index: int) -> bool:
    """Find the dialog on screen and respond to it, from the GTK thread.

    Returns True to be called again: the dialog takes a moment to be realised,
    and a single miss would fail the run rather than wait for it.
    """
    for window in Gtk.Window.list_toplevels():
        if isinstance(window, Gtk.MessageDialog) and window.get_visible():
            window.response(index)
            return False
    return True


def ask_from(where: str, on_gtk_thread: bool) -> int:
    """Put the question up from one of the two places it gets asked from."""
    answers: list[int] = []

    def ask() -> None:
        answers.append(dialogs._gtk_ask(f"Question from {where}", "Body.", BUTTONS))  # ruff: ignore[private-member-access] -- _gtk_ask is the thing under test

    GLib.timeout_add(300, answer_the_dialog, WANTED)
    if on_gtk_thread:
        GLib.idle_add(lambda: (ask(), Gtk.main_quit(), False)[-1])
    else:
        worker = threading.Thread(target=lambda: (ask(), Gtk.main_quit()))
        worker.start()
    Gtk.main()
    return answers[0] if answers else -1


def main() -> int:
    failures = []
    for where, on_gtk_thread in (("the GTK thread", True), ("a worker", False)):
        got = ask_from(where, on_gtk_thread)
        print(f"    asked from {where}: answer {got}")
        if got != WANTED:
            failures.append(f"{where}: wanted {WANTED}, got {got}")

    if failures:
        for line in failures:
            print(f"FAIL: {line}", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
