"""Windows and the dialogs that hang from them.

    portable  the Toolkit every platform answers, pywebview's answers, Answer
    macos     AppKit's answers
    gtk       GTK's question, and pywebview's for the rest
    win32     a Win32 message box, and pywebview's for the rest
    windows   which windows exist and which is in front; it chooses `native`
    dialogs   what each question says and each answer does

Each imports only what is above it in that list. `native` is one of the three
toolkit modules, chosen once in `windows`, so nothing else here tests the
platform: `dialogs` decides what to ask and `native` draws it.

One edge used to go upward: `_open_first_window` created the first window and
wired its `closing` event to `confirm_close`. It lives in `host/app.py` now,
which was its only caller and which already imports both modules. The module
that owns the application does the wiring, so neither `windows` nor `dialogs`
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
    bring_start_window_forward,
    close_session_window,
    close_start_window,
    copy_untitled,
    create_window,
    document_title,
    find_front_session,
    find_front_window,
    find_window,
    fold_changes_in,
    forget_start_window,
    listen_for_drops,
    make_new_document,
    native,
    reload_session,
    remember_start_window,
    set_fullscreen,
    show_session_document,
    show_session_edited,
    take_dropped,
)

__all__ = [
    "Answer",
    "Question",
    "ask",
    "ask_open_path",
    "ask_save_path",
    "ask_to_recover",
    "bring_start_window_forward",
    "close_session_window",
    "close_start_window",
    "confirm_close",
    "copy_untitled",
    "create_window",
    "document_title",
    "find_front_session",
    "find_front_window",
    "find_window",
    "fold_changes_in",
    "forget_start_window",
    "listen_for_drops",
    "make_new_document",
    "native",
    "offer_reload",
    "reload_session",
    "remember_start_window",
    "say",
    "set_fullscreen",
    "show_session_document",
    "show_session_edited",
    "take_dropped",
]
