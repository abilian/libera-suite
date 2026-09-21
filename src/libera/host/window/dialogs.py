"""Everything that puts something on screen and waits for an answer.

Save panels, alerts, the close prompt, the recovery offer. Cocoa on macOS and
pywebview's own dialogs elsewhere, and all of it above `windows`: a dialog
needs a window to hang from.
"""

from __future__ import annotations

import functools
import logging
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from libera.host import convert
from libera.host.session import SESSIONS, H, current_path, use
from libera.host.window.windows import (
    front_window,
    on_gui_thread,
    reload_session,
    window_for,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

# AppKit's NSAlertFirstButtonReturn and friends, which pyobjc does not export
# by name. Buttons are numbered in the order they were added.
NS_ALERT_FIRST_BUTTON = 1000
NS_ALERT_SECOND_BUTTON = 1001

logger = logging.getLogger(__name__)


def _gtk_ask(title: str, message: str, buttons: Sequence[str]) -> int:
    """Put a modal question on screen with GTK. Returns the index chosen, or -1.

    The three questions this module asks were macOS-only, and each one said so
    in a comment that ended "nowhere to ask". Two of them cost a user their
    work: closing a window with unsaved edits closed it, and the recovery
    offer that was supposed to catch that never appeared either, so the edits
    sat in the session directory with nothing to surface them.

    **Not `create_confirmation_dialog`.** pywebview's is two buttons, where
    the close prompt needs three, and it hands the work to the GTK thread and
    waits -- which deadlocks when the caller is already on that thread, as the
    `closing` handler is.

    So: a real Gtk.MessageDialog, run where GTK can run it. `dialog.run()`
    spins its own nested main loop, so it is safe on the GUI thread and only
    there; a request thread hands it over with idle_add and waits for the
    answer, which is the same shape as on_gui_thread on the macOS side.
    """
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    answer: list[int] = []
    done = threading.Event()

    def ask() -> bool:
        window = front_window()
        dialog = Gtk.MessageDialog(
            transient_for=getattr(window, "native", None),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            text=title,
            secondary_text=message,
        )
        for index, label in enumerate(buttons):
            dialog.add_button(label, index)
        try:
            response = int(dialog.run())
        finally:
            dialog.destroy()
        answer.append(response if 0 <= response < len(buttons) else -1)
        done.set()
        return False  # idle_add repeats until its callback says otherwise

    if threading.current_thread() is threading.main_thread():
        # webview.start() runs the GTK loop on the main thread, so this is it.
        ask()
    else:
        GLib.idle_add(ask)
        # No timeout: a question is answered when somebody answers it, and the
        # macOS alert on the other side of this blocks in exactly the same way.
        done.wait()
    return answer[0] if answer else -1


def _ask_to_recover(document: Path) -> bool:
    """Offer back edits that never reached the file.

    An NSAlert rather than a pywebview dialog, because the question has to be
    answered before the document is converted, and converting is the step that
    discards the session those edits live in.

    Called from a request thread whenever a second window opens a document, so
    it goes through on_gui_thread -- building the alert where the request
    happens to be raises NSInternalInconsistencyException.
    """
    if sys.platform != "darwin":
        return (
            _gtk_ask(
                f"Recover unsaved changes to \u201c{document.name}\u201d?",
                "Libera Suite has edits to this document that were never "
                "saved. Open the document with them, or without?",
                ("Without", "Recover"),
            )
            == 1
        )
    return bool(on_gui_thread(lambda: _recovery_alert(document)))


def _recovery_alert(document: Path) -> bool:
    import AppKit

    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_("Recover unsaved changes?")
    alert.setInformativeText_(
        f"Libera Suite has changes to “{document.name}” that were never saved.\n\n"
        "Recover them, or open the document as it is on disk?"
    )
    alert.addButtonWithTitle_("Recover")
    alert.addButtonWithTitle_("Open Saved Version")
    alert.setAlertStyle_(AppKit.NSAlertStyleWarning)
    return int(alert.runModal()) == NS_ALERT_FIRST_BUTTON


def apply_format(panel, name: Path, extension: str, known: Collection[str]) -> None:
    """Put the format on the panel: its filename and what it will accept.

    setAllowedFileTypes_ is the half that matters. It makes the panel itself
    enforce the extension, so the path it returns already carries it -- which
    means the overwrite it confirms and the access macOS grants are both for
    the file we are actually going to write.
    """
    panel.setAllowedFileTypes_([extension])
    panel.setNameFieldStringValue_(with_format(name, extension, known).name)
    logger.debug("save as: format -> .%s", extension)


def with_format(path: Path, extension: str, known: Collection[str]) -> Path:
    """The same file, carrying the chosen format's extension.

    Replaces an extension the dialog deals in, and appends otherwise.
    Path.with_suffix would replace whatever follows the last dot, which for a
    name like "Minutes 2026.03.11" means eating the ".11".

    `known` is the popup's own list, passed in rather than read off the bound
    session: this runs on the GUI thread when the user changes the format, and
    the GUI thread has no session bound -- `H` there raises.
    """
    if path.suffix.lstrip(".").lower() in known:
        return path.with_suffix(f".{extension}")
    return path.with_name(f"{path.name}.{extension}")


@functools.cache
def _format_watcher():
    """The popup's target class.

    Cached because pyobjc registers a class by name with the Objective-C
    runtime: defining it twice raises "overriding existing Objective-C class",
    which would make the second Save As of a session fail.
    """
    import AppKit

    class LiberaFormatWatcher(AppKit.NSObject):
        """Keeps the save panel's filename in step with the format popup."""

        def formatChanged_(self, sender):
            # Read the name field rather than the name the panel opened with:
            # the popup changes the format, not the name, and by now the user
            # may well have typed one.
            extension = self.extensions[sender.indexOfSelectedItem()]
            current = Path(str(self.panel.nameFieldStringValue()))
            apply_format(self.panel, current, extension, self.extensions)

    return LiberaFormatWatcher


def _save_panel(suggested: str) -> str | None:
    """A save dialog with a File Format popup.

    This is the export path. Upstream hides "Download As" for an offline
    desktop app -- FileMenu.js swaps it for "Save As" when isDesktopApp and
    isOffline -- so Save As is the only way to reach another format, and
    pywebview's save dialog takes no file filter at all on macOS.

    Called from a request thread; the panel has to run on the GUI thread, so
    this hands the work over and waits for it.
    """
    import AppKit
    from PyObjCTools import AppHelper

    done = threading.Event()
    chosen: list[str | None] = [None]

    def show():
        panel, _ = build_save_panel(suggested)

        def finished(response):
            if response == AppKit.NSFileHandlingPanelOKButton:
                # Exactly what the panel confirmed. Rewriting the path
                # afterwards would mean the overwrite the user agreed to was
                # for a different file -- and macOS grants access to the file
                # they chose, not to one we substitute. The extension is right
                # because setAllowedFileTypes_ makes the panel enforce it.
                chosen[0] = str(panel.URL().path())
            logger.info("save as -> %s", chosen[0] or "cancelled")
            done.set()

        # A sheet on the document window, not a nested runModal inside
        # pywebview's own event loop: that is the native shape for a document
        # save, and it leaves the loop free to deliver the format popup's
        # action, which a nested modal session does not.
        window = front_window()
        native = getattr(window, "native", None) if window else None
        if native is not None:
            panel.beginSheetModalForWindow_completionHandler_(native, finished)
        else:
            finished(panel.runModal())

    AppHelper.callAfter(show)
    done.wait()
    return chosen[0]


def build_save_panel(suggested: str, formats: Sequence[tuple[str, str]] | None = None):
    """The panel and its format popup, built but not shown.

    `formats` is what the popup offers, and it differs per editor -- Tables has
    no .docx and Words no .xlsx. Defaults to the bound session's, which is what
    the save path wants; the tests pass one in, because a dialog builder should
    not need a live session to be checked.

    Separate from running it so the wiring can be checked without a dialog on
    screen -- the panel itself runs out of process, so once it is up there is
    nothing left to inspect.
    """
    import AppKit
    import Foundation
    import objc

    if formats is None:
        formats = H.editor.save_formats
    labels = [label for label, _ in formats]
    extensions = [ext for _, ext in formats]
    start = Path(suggested).suffix.lstrip(".").lower()
    index = extensions.index(start) if start in extensions else 0

    panel = AppKit.NSSavePanel.savePanel()
    # False: the panel must not let a typed extension override the format, or
    # an ODT file ends up called .docx.
    panel.setAllowsOtherFileTypes_(False)
    panel.setExtensionHidden_(False)

    row = AppKit.NSView.alloc().initWithFrame_(Foundation.NSMakeRect(0, 0, 380, 32))
    label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, 6, 88, 20)
    )
    label.setStringValue_("File Format:")
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setEditable_(False)
    label.setSelectable_(False)
    row.addSubview_(label)

    popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
        Foundation.NSMakeRect(92, 2, 278, 26), False
    )
    popup.addItemsWithTitles_(labels)
    popup.selectItemAtIndex_(index)

    apply_format(panel, Path(suggested), extensions[index], extensions)

    watcher = _format_watcher().alloc().init()
    watcher.panel = panel
    watcher.extensions = extensions
    popup.setTarget_(watcher)
    popup.setAction_("formatChanged:")
    row.addSubview_(popup)

    panel.setAccessoryView_(row)
    # setTarget_ does not retain, and a pyobjc object takes no Python
    # attributes to park it in either. Without an association the watcher is
    # collected as soon as this returns, and choosing a format does nothing --
    # or worse, calls through a dangling pointer.
    objc.setAssociatedObject(
        popup, b"libera.format.watcher", watcher, objc.OBJC_ASSOCIATION_RETAIN
    )
    return panel, popup


# The close prompt's buttons, in the order they are added on either platform.
CLOSE_SAVE, CLOSE_CANCEL, CLOSE_DISCARD = 0, 1, 2


def _gtk_confirm_close(document: Path) -> bool:
    """The close prompt everywhere that is not macOS. False keeps the window."""
    chosen = _gtk_ask(
        f"Save changes to \u201c{document.name}\u201d before closing?",
        "Your changes will be lost if you don't save them.",
        ("Save", "Cancel", "Don't Save"),
    )
    if chosen == CLOSE_SAVE:
        return _save_or_say_why(
            document, lambda heading, detail: _gtk_ask(heading, detail, ("OK",))
        )
    # A dismissed dialog (-1) keeps the window, which is the answer that cannot
    # lose anything.
    return chosen == CLOSE_DISCARD


def _save_or_say_why(document: Path, tell) -> bool:
    """Save, and answer whether the window may now close.

    `tell(heading, detail)` puts a failure on screen. The two platforms differ
    only in how they do that, and a window that closed on a failed save would
    take the edits with it -- which is the whole reason this asks at all.
    """
    if not convert.save_document({"fileType": 0, "params": ""}).get("error"):
        return True
    tell(
        "Libera Suite could not save the document",
        f"\u201c{document.name}\u201d was not written, so the window has been "
        "left open. Try File \u25b8 Save As somewhere else.",
    )
    return False


def confirm_close(session: str) -> bool:
    """Ask before a window takes unsaved edits with it. False keeps it open.

    The editor is not asked to save: pywebview's evaluate_js hands work to the
    GUI thread and waits, and this runs *on* the GUI thread, so calling it here
    would deadlock. It is not needed either -- Editor.bin and the change log
    the editor streams as you type are both already on disk, which is what the
    host converts from on an ordinary save.
    """
    host = SESSIONS.get(session)
    if host is None:
        return True
    use(host)
    document = current_path()
    if document is None or not H.unsaved.is_file():
        return True
    if sys.platform != "darwin":
        return _gtk_confirm_close(document)

    import AppKit

    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(f"Save changes to “{document.name}” before closing?")
    alert.setInformativeText_("Your changes will be lost if you don't save them.")
    # First button is rightmost and default, which is the macOS order.
    alert.addButtonWithTitle_("Save")
    alert.addButtonWithTitle_("Cancel")
    alert.addButtonWithTitle_("Don't Save")
    alert.setAlertStyle_(AppKit.NSAlertStyleWarning)

    answer = int(alert.runModal())
    if answer == NS_ALERT_SECOND_BUTTON:
        return False
    if answer == NS_ALERT_FIRST_BUTTON:

        def tell(heading: str, detail: str) -> None:
            AppKit.NSBeep()
            failed = AppKit.NSAlert.alloc().init()
            failed.setMessageText_(heading)
            failed.setInformativeText_(detail)
            failed.runModal()

        if not _save_or_say_why(document, tell):
            return False
    # "Don't Save" leaves the unsaved marker where it is, so the edits are
    # offered back the next time this document is opened.
    return True


def offer_reload(session: str, message: str, port: int) -> None:
    """The editor threw. Offer the window back rather than leave it wedged.

    Reloading costs the editor's undo history and where the cursor was, and
    keeps the edits -- so it is an offer, not something done behind the user's
    back. The alert and the reload both belong to the GUI thread.
    """

    def ask() -> None:
        if window_for(session) is None:
            return

        import AppKit

        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Libera Suite ran into a problem")
        alert.setInformativeText_(
            "The editor stopped working properly and may not respond.\n\n"
            "Reloading keeps your edits. It loses the undo history and where "
            f"the cursor was.\n\n{message.splitlines()[0][:200]}"
        )
        alert.addButtonWithTitle_("Reload")
        alert.addButtonWithTitle_("Leave It")
        alert.setAlertStyle_(AppKit.NSAlertStyleWarning)
        if int(alert.runModal()) != NS_ALERT_FIRST_BUTTON:
            logger.info("reload declined")
            return

        reload_session(session, port)

    if sys.platform != "darwin":
        if (
            _gtk_ask(
                "The editor stopped responding.",
                "Reload it? Your edits are kept; the undo history is not.",
                ("Leave it", "Reload"),
            )
            == 1
        ):
            reload_session(session, port)
        return

    from PyObjCTools import AppHelper

    AppHelper.callAfter(ask)


def _chosen_path(chosen: Sequence[str] | None) -> str | None:
    """What create_file_dialog returns, as one path or none.

    pywebview types it `Sequence[str] | None` and a `str` satisfies that, so
    the isinstance is doing real work: a save dialog answers with the path
    itself and an open dialog with a tuple of them.
    """
    if not chosen:
        return None
    return chosen if isinstance(chosen, str) else chosen[0]


def _gtk_save_path(suggested: str) -> str | None:
    """The save dialog everywhere that is not macOS.

    A function of its own rather than the second half of ask_save_path: one
    per platform reads better, and pyrefly loses track of the `window is None`
    guard when a `sys.platform` return precedes it in the same body -- it
    reported the line below as a None dereference with the check three lines
    above it.
    """
    import webview

    window = front_window()
    if window is None:
        return None
    return _chosen_path(
        window.create_file_dialog(webview.FileDialog.SAVE, save_filename=suggested)
    )


def ask_save_path(suggested: str) -> str | None:
    """Where to save. Installed as hooks.SAVE_PATH_CHOOSER by run()."""
    if sys.platform == "darwin":
        return _save_panel(suggested)
    return _gtk_save_path(suggested)


def ask_open_path(_filter: str) -> str | None:
    """What to open. Installed as hooks.OPEN_PATH_CHOOSER by run()."""
    import webview

    window = front_window()
    if window is None:
        return None
    return _chosen_path(window.create_file_dialog(webview.FileDialog.OPEN))
