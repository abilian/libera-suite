"""Windows and the dialogs that hang from them.

    windows   which windows exist, which is in front, what is in them
    dialogs   save panels, alerts, the close prompt, the recovery offer

`dialogs` is above `windows` and calls into it; nothing goes the other way.
One edge used to: `_first_window` created the first window and wired its
`closing` event to `confirm_close`. It lives in `host/app.py` now, which was
its only caller and which already imports both halves -- so the wiring is done
by the thing that owns the application, and neither half reaches up.
"""

from __future__ import annotations

from libera.host.window.dialogs import (
    NS_ALERT_FIRST_BUTTON,
    NS_ALERT_SECOND_BUTTON,
    _ask_to_recover,
    apply_format,
    ask_open_path,
    ask_save_path,
    build_save_panel,
    confirm_close,
    offer_reload,
    with_format,
)
from libera.host.window.windows import (
    SESSION_BY_WINDOW,
    _window,
    close_start_window,
    fold_changes_in,
    front_session,
    front_window,
    new_document,
    on_gui_thread,
    reload_session,
    set_fullscreen,
    untitled,
    window_for,
)

__all__ = [
    "NS_ALERT_FIRST_BUTTON",
    "NS_ALERT_SECOND_BUTTON",
    "SESSION_BY_WINDOW",
    "_ask_to_recover",
    "_window",
    "apply_format",
    "ask_open_path",
    "ask_save_path",
    "build_save_panel",
    "close_start_window",
    "confirm_close",
    "fold_changes_in",
    "front_session",
    "front_window",
    "new_document",
    "offer_reload",
    "on_gui_thread",
    "reload_session",
    "set_fullscreen",
    "untitled",
    "window_for",
    "with_format",
]
