"""What a menu item does when it fires, and what decides whether it can.

The lower half: a plain function per item, and the small helpers those call.
`macos` and `gtk` put the items on a bar; nothing here knows a bar exists, and
nothing here touches a toolkit.

The functions are the reason both bars can exist. Their bodies used to be the
selector bodies, so File > Save was a method on an NSObject subclass -- which
is a macOS-only home for a line of JavaScript that has nothing to do with
AppKit. The Objective-C target whose selectors call them, and the menu
delegates, are in `macos`.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from libera.host import about, apps, desktop, hooks, recents, session, window

logger = logging.getLogger(__name__)

HELP_URL = "https://docs.liberasuite.eu/"


def _reload_front_window() -> None:
    """File > Reload: rebuild the editor in the window you are looking at.

    The way out of an editor that has stopped responding. It keeps the edits
    -- the host folds the change log back into the document first -- and costs
    the undo history and where the cursor was.
    """
    front = window.find_front_session()
    if front is None:
        logger.warning("reload: no window to reload")
        return
    hooks.shell.reload(front)


def _run_in_background(work) -> None:
    """Run a menu action off the GUI thread.

    Menu actions arrive on the GUI thread and most of what they do -- asking
    the editor through evaluate_js, putting a save panel up -- waits on that
    same thread. Doing it here would be a deadlock every time.
    """
    threading.Thread(target=work, daemon=True).start()


def _ask_editor(what: str, js: str) -> None:
    """Ask the front window's editor to do something.

    Anything that goes wrong is said out loud. A menu item that silently does
    nothing is the hardest kind of bug to report, and swallowing the exception
    here hid three of them at once.
    """

    def ask():
        front = window.find_front_window()
        if front is None:
            logger.warning("menu %s: no window", what)
            return
        result = front.evaluate_js(
            '(function(){try{var w=document.querySelector("iframe").contentWindow;'
            "var api=w.Asc&&w.Asc.editor;"
            'if(!api) return "no editor in this window";'
            + js
            + 'return "";}catch(e){return String(e);}})()'
        )
        if result:
            logger.warning("menu %s: %s", what, result)

    _run_in_background(ask)


CONDITIONAL = frozenset({"undo:", "redo:", "saveDocument:"})


def is_enabled(action: str, front: session.Session | None) -> bool:
    """Should the menu item for `action` be available, for the front session?

    asc_Save on an unmodified document writes nothing and says nothing, and so
    does Undo with an empty history -- which from the other side of the screen
    is indistinguishable from a broken menu. The editor pushes what it can do;
    this only reads what it last said.

    A plain function and not a method, so it can be tested without AppKit --
    and so that a session and the session *module* cannot end up with the
    same name. They did: `session = find_front_session()` shadowed the imported
    module, and `session.SESSIONS` was then an attribute lookup on a str.
    Every Undo, Redo and Save validation raised AttributeError inside an ObjC
    callback, where the exception goes nowhere anyone reads.
    """
    if action not in CONDITIONAL:
        return True
    if action == "saveDocument:":
        return bool(front and front.unsaved_marker.is_file())
    # Absent means the editor has not said yet: leave it available rather than
    # grey out something that would have worked.
    return bool(front.abilities.get(action.rstrip(":"), True)) if front else True


# --- what an item does -------------------------------------------------------
#
# Plain functions, because two menu bars call them: AppKit's, through the
# selectors below, and GTK's, through `menu.gtk`. They lived as selector
# bodies, which made every one of them macOS-only for no reason -- not one
# touches AppKit.


def open_new_document(app: apps.App | None = None) -> None:
    """File > New > Document, Spreadsheet or Presentation: a blank, in a window.

    Any kind from any window. It used to be the front window's kind only, so
    with a document open there was no way to a new spreadsheet: the start
    window, which offers every kind, closes once it has been used.
    """
    _run_in_background(lambda: hooks.shell.open_window(None, app))


def list_creatable() -> tuple[apps.App, ...]:
    """What File > New offers: every editor with a blank to start from.

    Diagrams has none, being a viewer, so it is not on the list.
    """
    return tuple(app for app in apps.ALL if app.blank)


def choose_new_kind() -> apps.App:
    """The kind ⌘N makes: the front window's, or a Document.

    A Document when there is no window to ask, when the front one is the start
    window (which shows no document), and when it holds a kind that cannot be
    created, which is Diagrams.
    """
    front = window.find_front_session()
    editor = front.editor if front is not None else apps.WORDS
    return editor if editor in list_creatable() else apps.WORDS


def open_document() -> None:
    def pick():
        path = hooks.shell.choose_open_path("documents")
        if path:
            hooks.shell.open_window(Path(path))

    _run_in_background(pick)


def open_recent(path: str) -> None:
    def open_it():
        if path:
            hooks.shell.open_window(Path(path))

    _run_in_background(open_it)


def reload_document() -> None:
    _run_in_background(_reload_front_window)


def close_window() -> None:
    """File > Close, for the GTK bar.

    macOS uses performClose:, which goes through the window delegate. GTK has
    no responder chain, so this destroys the window -- and pywebview's destroy
    emits delete-event, which is what raises the `closing` event `app.run`
    wired to confirm_close. So the menu item asks about unsaved changes by the
    same path the title bar's button does, rather than by a second one that
    would have to be kept in step.
    """

    def close():
        front = window.find_front_window()
        if front is None:
            logger.warning("menu Close: no window")
            return
        front.destroy()

    _run_in_background(close)


def save() -> None:
    _ask_editor("Save", "api.asc_Save();")


def save_as() -> None:
    _ask_editor("Save As", "api.asc_DownloadAs(new w.Asc.asc_CDownloadOptions());")


def print_document() -> None:
    _ask_editor("Print", "api.asc_Print();")


def undo() -> None:
    _ask_editor("Undo", "(api.asc_Undo || api.Undo).call(api);")


def redo() -> None:
    _ask_editor("Redo", "(api.asc_Redo || api.Redo).call(api);")


def find() -> None:
    _ask_editor("Find", 'w.Common.NotificationCenter.trigger("search:show");')


def zoom_in() -> None:
    _ask_editor("Zoom In", "api.zoomIn();")


def zoom_out() -> None:
    _ask_editor("Zoom Out", "api.zoomOut();")


def fit_page() -> None:
    _ask_editor("Fit Page", "api.zoomFitToPage();")


def fit_width() -> None:
    _ask_editor("Fit Width", "api.zoomFitToWidth();")


def toggle_formatting_marks() -> None:
    _ask_editor("Formatting Marks", "api.put_ShowParaMarks(!api.get_ShowParaMarks());")


def show_help() -> None:
    _run_in_background(_open_help)


def _open_help() -> None:
    """Help: the documentation, in the user's browser, or the URL if not.

    `desktop.open_url` and not `webbrowser.open`. The latter reports success
    for a browser it merely spawned, so on a machine where opening the link
    fails -- a Flatpak whose portal finds no handler, a desktop with nothing
    registered for https -- Help did nothing at all and said nothing either.
    `open_url` waits for the opener and returns its verdict.

    Reporting the URL is the fallback, and it is all we can do. What opens a
    link is the desktop's business, and a sandbox makes that more so.
    """
    if desktop.open_url(HELP_URL):
        return

    window.dialogs.say(
        "Nothing here could open a browser",
        f"The documentation is at:\n\n{HELP_URL}",
    )


def show_about() -> None:
    """About: who wrote the editors, and under what licence.

    On macOS the application menu's own About panel already reads
    `NSHumanReadableCopyright` out of the main bundle, so this is the Linux
    route to the same sentences. The editor has an About panel of its own,
    which upstream switches off whenever `isDesktopApp` on the assumption that
    the native shell provides one; `build/patches/web-apps/0007` turns it back
    on, and this is what the shell owes either way.
    """

    window.dialogs.say("Libera Suite", about.format_notice())


def read_recent_documents() -> list[str]:
    """The remembered documents, for whichever menu is asking.

    The list is shared by every session, so any one says where it is. Handed
    the first, rather than binding it to the thread asking -- AppKit's menu
    delegate, or `run()` itself -- which is what this used to do.
    """
    first = next(iter(session.SESSIONS.values()), None)
    if first is None:
        return []
    return [entry["path"] for entry in recents.read_recents(first)]
