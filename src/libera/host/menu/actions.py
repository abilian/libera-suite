"""What a menu item does when it fires, and what decides whether it can.

The lower half: a plain function per item, the Objective-C target whose
selectors point at them, the recent-menu delegate, and the small helpers those
call. `build` and `gtk` put the items on a bar; nothing here knows a bar
exists.

The functions are the reason both bars can exist. Their bodies used to be the
selector bodies, so File > Save was a method on an NSObject subclass -- which
is a macOS-only home for a line of JavaScript that has nothing to do with
AppKit.

TARGET, RECENT_DELEGATE and the two class factories carry no leading
underscore: `build` uses all four, and an underscore would be claiming a
privacy the package does not have.

TARGET and RECENT_DELEGATE are module state because AppKit holds a menu
item's target by an *unretained* pointer -- an object that goes out of scope
leaves items wired to freed memory. `build.install()` assigns them here, as
`actions.TARGET = ...`, and everything that reads them reads them through this
module for the same reason.
"""

from __future__ import annotations

import functools
import logging
import threading
import webbrowser
from pathlib import Path

from libera.host import hooks, recents, session

logger = logging.getLogger(__name__)

HELP_URL = "https://docs.liberasuite.eu/"


def _reload_front_window() -> None:
    """File > Reload: rebuild the editor in the window you are looking at.

    The way out of an editor that has stopped responding. It keeps the edits
    -- the host folds the change log back into the document first -- and costs
    the undo history and where the cursor was.
    """
    from libera.host.window import front_session

    session_id = front_session()
    if hooks.RELOAD is None or not session_id:
        logger.warning("reload: no window to reload")
        return
    hooks.RELOAD(session_id)


def _in_background(work) -> None:
    """Run a menu action off the GUI thread.

    Menu actions arrive on the GUI thread and most of what they do -- asking
    the editor through evaluate_js, putting a save panel up -- waits on that
    same thread. Doing it here would be a deadlock every time.
    """
    threading.Thread(target=work, daemon=True).start()


def _editor(what: str, js: str) -> None:
    """Ask the front window's editor to do something.

    Anything that goes wrong is said out loud. A menu item that silently does
    nothing is the hardest kind of bug to report, and swallowing the exception
    here hid three of them at once.
    """

    def ask():
        from libera.host.window import front_window

        window = front_window()
        if window is None:
            logger.warning("menu %s: no window", what)
            return
        result = window.evaluate_js(
            '(function(){try{var w=document.querySelector("iframe").contentWindow;'
            "var api=w.Asc&&w.Asc.editor;"
            'if(!api) return "no editor in this window";'
            + js
            + 'return "";}catch(e){return String(e);}})()'
        )
        if result:
            logger.warning("menu %s: %s", what, result)

    _in_background(ask)


CONDITIONAL = frozenset({"undo:", "redo:", "saveDocument:"})


def enabled_for(action: str, session_id: str) -> bool:
    """Should the menu item for `action` be available, for that session?

    asc_Save on an unmodified document writes nothing and says nothing, and so
    does Undo with an empty history -- which from the other side of the screen
    is indistinguishable from a broken menu. The editor pushes what it can do;
    this only reads what it last said.

    A plain function and not a method, so it can be tested without AppKit --
    and so that the session *id* and the session *module* cannot end up with
    the same name. They did: `session = front_session()` shadowed the imported
    module, and `session.SESSIONS` was then an attribute lookup on a str.
    Every Undo, Redo and Save validation raised AttributeError inside an ObjC
    callback, where the exception goes nowhere anyone reads.
    """
    if action not in CONDITIONAL:
        return True
    if action == "saveDocument:":
        host = session.SESSIONS.get(session_id)
        return bool(host and host.unsaved.is_file())
    state = session.editor_state(session_id)
    # Absent means the editor has not said yet: leave it available rather than
    # grey out something that would have worked.
    return bool(state.get(action.rstrip(":"), True))


# --- what an item does -------------------------------------------------------
#
# Plain functions, because two menu bars call them: AppKit's, through the
# selectors below, and GTK's, through `menu.gtk`. They lived as selector
# bodies, which made every one of them macOS-only for no reason -- not one
# touches AppKit.


def new_document() -> None:
    _in_background(lambda: hooks.WINDOW_OPENER and hooks.WINDOW_OPENER(None))


def open_document() -> None:
    def pick():
        path = hooks.OPEN_PATH_CHOOSER("documents") if hooks.OPEN_PATH_CHOOSER else None
        if path and hooks.WINDOW_OPENER:
            hooks.WINDOW_OPENER(Path(path))

    _in_background(pick)


def open_recent(path: str) -> None:
    def open_it():
        if path and hooks.WINDOW_OPENER:
            hooks.WINDOW_OPENER(Path(path))

    _in_background(open_it)


def reload_document() -> None:
    _in_background(_reload_front_window)


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
        from libera.host.window import front_window

        window = front_window()
        if window is None:
            logger.warning("menu Close: no window")
            return
        window.destroy()

    _in_background(close)


def save() -> None:
    _editor("Save", "api.asc_Save();")


def save_as() -> None:
    _editor("Save As", "api.asc_DownloadAs(new w.Asc.asc_CDownloadOptions());")


def print_document() -> None:
    _editor("Print", "api.asc_Print();")


def undo() -> None:
    _editor("Undo", "(api.asc_Undo || api.Undo).call(api);")


def redo() -> None:
    _editor("Redo", "(api.asc_Redo || api.Redo).call(api);")


def find() -> None:
    _editor("Find", 'w.Common.NotificationCenter.trigger("search:show");')


def zoom_in() -> None:
    _editor("Zoom In", "api.zoomIn();")


def zoom_out() -> None:
    _editor("Zoom Out", "api.zoomOut();")


def fit_page() -> None:
    _editor("Fit Page", "api.zoomFitToPage();")


def fit_width() -> None:
    _editor("Fit Width", "api.zoomFitToWidth();")


def toggle_formatting_marks() -> None:
    _editor("Formatting Marks", "api.put_ShowParaMarks(!api.get_ShowParaMarks());")


def show_help() -> None:
    _in_background(_open_help)


def _open_help() -> None:
    """Help: the documentation, in the user's browser, or the URL if not.

    `webbrowser.open` returns False when it could find nothing to run, and
    dropping that was a menu item that did nothing at all on a machine with no
    browser. It happens: a Flatpak on a minimal desktop reaches the portal, the
    portal finds no handler, and the user is left guessing.

    Reporting the URL is the honest fallback, and it is all we can do. What
    opens a link is the desktop's business, and a sandbox makes that more true
    rather than less.
    """
    if webbrowser.open(HELP_URL):
        return
    logger.warning("nothing on this machine could open %s", HELP_URL)

    from libera.host.window import dialogs

    dialogs.say(
        "Nothing here could open a browser",
        f"The documentation is at:\n\n{HELP_URL}",
    )


def recent_documents() -> list[str]:
    """The remembered documents, for whichever menu is asking.

    Both bars need a session bound before `read_recents` will answer: H is
    thread-local and raises rather than defaulting, and the thread asking is
    AppKit's menu delegate or `run()` itself, neither of which has one.

    NotReadyError and nothing wider: read_recents already answers [] for a
    corrupt or unreadable file and says so in the log, so a broader except
    would only catch the bugs.
    """
    host = next(iter(session.SESSIONS.values()), None)
    if host is None:
        return []
    session.use(host)
    try:
        return [entry["path"] for entry in recents.read_recents()]
    except session.NotReadyError as e:
        logger.warning("no recent list for the menu: %s", e)
        return []


@functools.cache
def target_class():
    """The menu's action target.

    Cached because pyobjc registers a class by name with the Objective-C
    runtime, and building it twice raises.
    """
    import AppKit

    class LiberaMenuTarget(AppKit.NSObject):
        def newDocument_(self, _sender):
            new_document()

        def reloadDocument_(self, _sender):
            reload_document()

        def openDocument_(self, _sender):
            open_document()

        def openRecent_(self, sender):
            open_recent(str(sender.representedObject() or ""))

        def saveDocument_(self, _sender):
            save()

        def saveDocumentAs_(self, _sender):
            save_as()

        def printDocument_(self, _sender):
            print_document()

        def undo_(self, _sender):
            undo()

        def redo_(self, _sender):
            redo()

        def find_(self, _sender):
            find()

        def zoomIn_(self, _sender):
            zoom_in()

        def zoomOut_(self, _sender):
            zoom_out()

        def zoomFitPage_(self, _sender):
            fit_page()

        def zoomFitWidth_(self, _sender):
            fit_width()

        def toggleFormattingMarks_(self, _sender):
            toggle_formatting_marks()

        def showHelp_(self, _sender):
            show_help()

        def validateMenuItem_(self, item):
            """Grey out what would decline. The decision is in enabled_for()."""
            from libera.host.window import front_session

            return enabled_for(str(item.action() or ""), front_session())

    return LiberaMenuTarget


@functools.cache
def recent_delegate_class():
    """Rebuilds the Open Recent submenu each time it is opened.

    Building it once would show whatever was remembered when the application
    started, which is wrong the moment a document is opened.
    """
    import AppKit

    class LiberaRecentMenu(AppKit.NSObject):
        def menuNeedsUpdate_(self, menu):
            menu.removeAllItems()
            paths = recent_documents()
            if not paths:
                empty = menu.addItemWithTitle_action_keyEquivalent_(
                    "No Recent Documents", None, ""
                )
                empty.setEnabled_(False)
                return
            for path in paths:
                item = menu.addItemWithTitle_action_keyEquivalent_(
                    Path(path).name, "openRecent:", ""
                )
                item.setTarget_(TARGET)
                item.setRepresentedObject_(path)

    return LiberaRecentMenu


TARGET = None
RECENT_DELEGATE = None
