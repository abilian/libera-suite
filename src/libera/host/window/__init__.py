"""Windows and the dialogs that hang from them.

    portable  what every toolkit answers; pywebview's answers, and Answer
    macos     AppKit's answers
    gtk       GTK's question, and pywebview's for the rest
    win32     a Win32 message box, and pywebview's for the rest
    windows   which windows exist, which is in front; chooses `native`
    dialogs   what each question says, and what each answer does

Each imports only what is above it in that list. `native` is one of the three
toolkit modules, chosen once in `windows`, so nothing else here tests the
platform: `dialogs` decides what to ask and `native` draws it.

One edge used to go upward: `_open_first_window` created the first window and
wired its `closing` event to `confirm_close`. It lives in `host/app.py` now,
which was its only caller and which already imports both halves -- so the
wiring is done by the thing that owns the application, and neither half
reaches up.
"""

from __future__ import annotations

from libera.host.window.dialogs import (
    ask,
    ask_open_path,
    ask_save_path,
    ask_to_recover,
    confirm_close,
    offer_reload,
    say,
)
from libera.host.window.portable import Answer, Question
from libera.host.window.windows import (
    _create_window,
    close_start_window,
    copy_untitled,
    find_front_session,
    find_front_window,
    find_window,
    fold_changes_in,
    make_new_document,
    native,
    reload_session,
    set_fullscreen,
)

__all__ = [
    "Answer",
    "Question",
    "_create_window",
    "ask",
    "ask_open_path",
    "ask_save_path",
    "ask_to_recover",
    "close_start_window",
    "confirm_close",
    "copy_untitled",
    "find_front_session",
    "find_front_window",
    "find_window",
    "fold_changes_in",
    "make_new_document",
    "native",
    "offer_reload",
    "reload_session",
    "say",
    "set_fullscreen",
]
