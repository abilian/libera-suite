"""AppKit: windows and dialogs as macOS draws them.

One of the three toolkit modules `windows` chooses between, each a
`portable.Toolkit`. Read on macOS alone, so AppKit is imported once, here.

It also starts the application the way AppKit wants it started: prepare()
before anything exists, complete_startup() once the menu bar does, which is where
Finder's "open documents" events start being answered.

AppKit is main-thread-only, while most of what puts something on screen
arrives on a request thread. `run_on_gui_thread` hands work over; an alert
expects to be called there already, and the save panel hands itself over,
because it waits for a completion handler.
"""

from __future__ import annotations

import logging
import threading
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import AppKit
import Foundation
import objc
import webview
from PyObjCTools import AppHelper

from libera.host import about, hooks, language
from libera.host.window.portable import Answer, Question
from libera.payload import locate

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Sequence

    from webview import Window
    from webview.guilib import GUIType

GUI: GUIType = "cocoa"

logger = logging.getLogger(__name__)


T = TypeVar("T")

# AppKit's NSAlertFirstButtonReturn, which pyobjc does not export by name.
# Buttons are numbered from it in the order they were added.
NS_ALERT_FIRST_BUTTON = 1000


def run_on_gui_thread(work: Callable[[], T]) -> T:
    """Run something that touches AppKit, and wait for its answer.

    AppKit is main-thread-only and does not warn: "NSWindow should only be
    instantiated on the main thread" is a hard exception that takes the request
    with it. Most of what asks the user a question arrives on a request thread,
    so it has to come back here first.

    Already on it? Call it. Dispatching to the thread we are standing on and
    then waiting for it is a deadlock.

    Whatever the work raises is raised again here, on the thread that asked.
    It used to stay on the GUI thread, where pyobjc logs it and moves on. The
    caller got None, which the recovery prompt read as "Open Saved Version",
    so a prompt that failed to appear discarded the edits it was there to
    offer back.
    """
    if threading.current_thread() is threading.main_thread():
        return work()

    done = threading.Event()
    outcome: list = []

    def run():
        try:
            outcome.append((work(), None))
        except Exception as e:
            outcome.append((None, e))
        finally:
            done.set()

    AppHelper.callAfter(run)
    done.wait()
    answer, failure = outcome[0]
    if failure is not None:
        raise failure
    return answer


def make_window(title: str, url: str, width: int, height: int) -> Window | None:
    """pywebview's create_window, except for the first window after none.

    pywebview names the first window it knows "master" and makes it at once,
    on the thread that asks, which it expects to be the one about to call
    start(). Once the last window has closed and the application runs on
    (stay_open), the next window is a "master" again, asked for by a request
    thread, and AppKit refuses: "NSWindow should only be instantiated on the
    main thread". So with no window, it is made on the GUI thread, by the two
    steps create_window takes once start() has run. There, create_window only
    lists it.
    """
    gui = webview.guilib
    if webview.windows or gui is None:
        # Another window open, or start() still to come: pywebview's own way.
        return webview.create_window(title, url, width=width, height=height)

    def make() -> Window | None:
        window = webview.create_window(title, url, width=width, height=height)
        if window is None or not window._initialize(gui=gui):
            return None
        gui.create_window(window)
        return window

    return run_on_gui_thread(make)


def find_key_window(windows: Sequence[Window]) -> Window | None:
    """The key window, else the main one, as pywebview windows.

    pywebview's active_window() is keyWindow, which is None whenever the
    application is not frontmost, and is the sheet while a save panel is up.
    The main window is the document behind it.
    """
    for native in (AppKit.NSApp.keyWindow(), AppKit.NSApp.mainWindow()):
        if native is None:
            continue
        for window in windows:
            # Bound to a local: a checker cannot narrow
            # `getattr(x, "native", None)` across a second lookup, nor can a
            # reader be sure a second lookup returns the same object.
            its_native = getattr(window, "native", None)
            if its_native is not None and (
                its_native.windowNumber() == native.windowNumber()
            ):
                return window
    return None


def set_fullscreen(window: Window, on: bool) -> None:
    """Read the window's own style mask, and act only when it disagrees.

    pywebview offers only toggle_fullscreen(), which drifts out of step the
    first time a call is missed; sdkjs says on and off explicitly.
    """
    native = window.native
    if native is None:  # pywebview has not finished making it
        return

    def apply() -> None:
        already = bool(native.styleMask() & AppKit.NSWindowStyleMaskFullScreen)
        if already != on:
            native.toggleFullScreen_(None)

    # The request arrives on a server thread; AppKit belongs to the GUI one.
    AppHelper.callAfter(apply)


def show_edited(window: Window, edited: bool) -> None:
    """The dot in the close button, and "Edited" after the title.

    setDocumentEdited: alone gives only the dot: the grey "Edited" Pages and
    TextEdit show comes from the window's subtitle, which NSDocument sets and
    this does in its place (measured, macOS 14).
    """
    native = window.native
    if native is None:  # pywebview has not finished making it
        return

    def apply() -> None:
        native.setDocumentEdited_(edited)
        native.setSubtitle_(language.translate("Edited") if edited else "")

    # The news arrives on a server thread; AppKit belongs to the GUI one.
    AppHelper.callAfter(apply)


def close_window(window: Window) -> None:
    """performClose:, as the menu's File > Close sends.

    It goes through the window's delegate, which asks about unsaved changes.
    pywebview's destroy() calls NSWindow.close, which skips the delegate and
    would close a window holding unsaved edits without a word.
    """
    native = window.native
    if native is None:  # pywebview has not finished making it
        return
    # The request arrives on a server thread; AppKit belongs to the GUI one.
    AppHelper.callAfter(native.performClose_, None)


def ask(question: Question, parent: Window | None) -> Answer:
    """An NSAlert, run modally on the GUI thread, which the caller is on.

    The first button added is the default and the rightmost; Cancel goes
    beside it and the choice that discards furthest away, which is the macOS
    order: Save, Cancel, Don't Save. `parent` goes unused: an alert run
    modally belongs to the application.
    """
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(question.title)
    alert.setInformativeText_(question.message)
    order = [(question.yes, Answer.YES), (question.no, Answer.NO)]
    if question.cancel is not None:
        order.insert(1, (question.cancel, Answer.CANCEL))
    for label, _ in order:
        alert.addButtonWithTitle_(label)
    alert.setAlertStyle_(AppKit.NSAlertStyleWarning)
    clicked = int(alert.runModal()) - NS_ALERT_FIRST_BUTTON
    return order[clicked][1] if 0 <= clicked < len(order) else Answer.CANCEL


def tell(title: str, message: str, parent: Window | None) -> None:
    """An NSAlert with one button, on the GUI thread, which the caller is on."""
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    alert.runModal()


def run_save_panel(
    suggested: str,
    formats: Sequence[tuple[str, str]],
    start_in: Path | None,
    parent: Window | None,
) -> str | None:
    """A save dialog with a File Format popup.

    This is the export path. Upstream hides "Download As" for an offline
    desktop app -- FileMenu.js swaps it for "Save As" when isDesktopApp and
    isOffline -- so Save As is the only way to reach another format, and
    pywebview's save dialog takes no file filter at all on macOS.

    Called from a request thread; the panel has to run on the GUI thread, so
    this hands the work over and waits for the panel's answer.
    """
    done = threading.Event()
    chosen: list[str | None] = [None]
    failure: list[Exception] = []
    native = getattr(parent, "native", None)

    def show():
        # A panel that could not be built is raised on the thread that asked.
        # Left here, pyobjc logged it, `done` was never set, and Save As hung.
        try:
            panel, _ = build_save_panel(suggested, formats, start_in)
        except Exception as e:
            failure.append(e)
            done.set()
            return

        def record_choice(response):
            if response == AppKit.NSFileHandlingPanelOKButton:
                # Exactly what the panel confirmed. Rewriting the path
                # afterwards would mean the overwrite the user agreed to was
                # for a different file, and macOS grants access only to the
                # file they chose. The extension is right because
                # setAllowedFileTypes_ makes the panel enforce it.
                chosen[0] = str(panel.URL().path())
            logger.info("save as -> %s", chosen[0] or "cancelled")
            done.set()

        # A sheet on the document window, not a nested runModal inside
        # pywebview's own event loop: that is the native shape for a document
        # save, and it leaves the loop free to deliver the format popup's
        # action, which a nested modal session does not.
        if native is not None:
            panel.beginSheetModalForWindow_completionHandler_(native, record_choice)
        else:
            record_choice(panel.runModal())

    AppHelper.callAfter(show)
    done.wait()
    if failure:
        raise failure[0]
    return chosen[0]


def build_save_panel(
    suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None = None
):
    """The panel and its format popup, built but not shown, in `start_in`.

    `formats` is what the popup offers. It differs per editor: Tables has no
    .docx and Words no .xlsx. Always the caller's: this runs on the GUI
    thread, where the session bound is not the window that asked.

    Separate from running it so the wiring can be checked without a dialog on
    screen. The panel itself runs out of process, so once it is up there is
    nothing left to inspect.
    """
    labels = [label for label, _ in formats]
    extensions = [ext for _, ext in formats]
    start = Path(suggested).suffix.lstrip(".").lower()
    index = extensions.index(start) if start in extensions else 0

    panel = AppKit.NSSavePanel.savePanel()
    # False: the panel must not let a typed extension override the format, or
    # an ODT file ends up called .docx.
    panel.setAllowsOtherFileTypes_(False)
    panel.setExtensionHidden_(False)
    if start_in is not None:
        panel.setDirectoryURL_(
            Foundation.NSURL.fileURLWithPath_isDirectory_(str(start_in), True)
        )

    row = AppKit.NSView.alloc().initWithFrame_(Foundation.NSMakeRect(0, 0, 380, 32))
    label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, 6, 88, 20)
    )
    label.setStringValue_(language.translate("File Format:"))
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

    watcher = LiberaFormatWatcher.alloc().init()
    watcher.panel = panel
    watcher.extensions = extensions
    popup.setTarget_(watcher)
    popup.setAction_("formatChanged:")
    row.addSubview_(popup)

    panel.setAccessoryView_(row)
    # setTarget_ does not retain; nor does a pyobjc object take Python
    # attributes to park it in. Without an association the watcher is
    # collected as soon as this returns, and choosing a format does nothing
    # (or worse, calls through a dangling pointer).
    objc.setAssociatedObject(
        popup, b"libera.format.watcher", watcher, objc.OBJC_ASSOCIATION_RETAIN
    )
    return panel, popup


class LiberaFormatWatcher(AppKit.NSObject):
    """Keeps the save panel's filename in step with the format popup.

    At module level, so the class is registered with the Objective-C runtime
    once: defining it a second time raises "overriding existing Objective-C
    class", which made the second Save As of a session fail when it was
    defined per panel.
    """

    def formatChanged_(self, sender):
        # Read the name field: the popup changes only the format, and by now
        # the user may well have typed a name over the one the panel opened
        # with.
        extension = self.extensions[sender.indexOfSelectedItem()]
        current = Path(str(self.panel.nameFieldStringValue()))
        apply_format(self.panel, current, extension, self.extensions)


def apply_format(panel, name: Path, extension: str, known: Collection[str]) -> None:
    """Put the format on the panel: its filename and what it will accept.

    setAllowedFileTypes_ is the call that matters. It makes the panel itself
    enforce the extension, so the path it returns already ends in it. The
    overwrite it confirms and the access macOS grants are then both for the
    file we are actually going to write.
    """
    panel.setAllowedFileTypes_([extension])
    panel.setNameFieldStringValue_(with_format(name, extension, known).name)
    logger.debug("save as: format -> .%s", extension)


def with_format(path: Path, extension: str, known: Collection[str]) -> Path:
    """The same file, with the chosen format's extension.

    Replaces an extension the dialog deals in, and appends otherwise.
    Path.with_suffix would replace whatever follows the last dot, which for a
    name like "Minutes 2026.03.11" means eating the ".11".

    `known` is the popup's own list, passed in: this runs on the GUI thread
    when the user changes the format, where no session is in reach.
    """
    if path.suffix.lstrip(".").lower() in known:
        return path.with_suffix(f".{extension}")
    return path.with_name(f"{path.name}.{extension}")


# --- starting the application ------------------------------------------------


def prepare() -> None:
    """What AppKit reads once, as the application is first made.

    Each of these is read when NSApplication.sharedApplication() first runs,
    or when the first window or the menu bar is built: before webview.start(),
    and never again.
    """
    # First, because this rewrites the running bundle's
    # CFBundleName, and macOS reads that once, when NSApplication.
    # sharedApplication() is first called. Afterwards the menu bar says
    # "Python" for the life of the process and nothing can change it.
    _name_the_application()

    # macOS gives any document-shaped window a tab bar, and a tab bar with
    # one tab is a second title bar saying what the first one said. Tabs
    # would need real support (newWindowForTab:, moving a document between
    # windows); until Libera Suite has it, turn them off. Class-level and before
    # the window exists, because a bar already on screen does not come off.
    AppKit.NSWindow.setAllowsAutomaticWindowTabbing_(False)

    # Before the menu bar is built, which is the only time these are read.
    _quieten_system_items()


def complete_startup(then: Callable[[], None]) -> None:
    """Once AppKit has a menu bar: the Dock icon, `then`, and Finder's documents.

    `then` is the menu package's install(), handed in because `menu` is above
    this module.

    Waiting for `webview.windows` was waiting for nothing: create_window fills
    that list before start() runs, so the wait returned at once and the install
    landed before there was a menu to add to. install() checks and returns
    without a word in that case, so the symptom, an application with no File
    menu and no crash, came and went with the race.

    So ask on the GUI thread, where the menu lives, and ask again shortly if it
    is not there yet.
    """

    def attempt(tries: int = 40) -> None:
        if AppKit.NSApp is None or AppKit.NSApp.mainMenu() is None:
            if tries:
                AppHelper.callLater(0.05, attempt, tries - 1)
            else:
                logger.warning("no menu bar to add to; our menus are missing")
            return
        _wear_the_application_icon()
        then()
        # Here for the same reason as the menu: AppKit installs its own handler
        # while launching, and the last one installed wins.
        _accept_documents_from_finder()

    AppHelper.callAfter(attempt)


def on_quit(work: Callable[[], None]) -> None:
    """Run `work` as the application quits.

    Cmd-Q is pywebview's menu item, `terminate:`, and AppKit ends the process
    inside start(), which never returns: whatever its caller meant to do on
    the way out did not happen. Every document's lock file stayed behind, so
    to LibreOffice, or to Libera Suite under another account, the document
    was still being edited by us.
    """
    center = Foundation.NSNotificationCenter.defaultCenter()
    center.addObserverForName_object_queue_usingBlock_(
        AppKit.NSApplicationWillTerminateNotification, None, None, lambda _note: work()
    )


def stay_open() -> None:
    """Keep running with no window, until Quit, as a Mac application does.

    A document opened later, by a double-click or a second `libera`, then
    goes to this process and skips the launch: on screen in about 1.7 s
    instead of 2.5 to 3 (notes/21-startup-and-size.md).

    pywebview stops AppKit's loop when its last window closes, which is what
    made start() return; this runs the loop again, for as long as the windows
    keep going. pywebview also stops it on a Cmd-Q its webview catches, with
    windows open: that is a quit, so this returns.
    """
    while not webview.windows:
        # pywebview drops its delegate with its last window, and sets it
        # again with its next.
        AppKit.NSApp.setDelegate_(REOPENER)
        AppKit.NSApp.run()


class LiberaReopener(AppKit.NSObject):
    """The application's delegate while no window is open."""

    @objc.typedSelector(b"Z@:@Z")
    def applicationShouldHandleReopen_hasVisibleWindows_(self, _app, _visible):
        """A click on the Dock icon: the start window. Off the GUI thread,
        where pywebview creates a window."""
        threading.Thread(target=hooks.shell.show_start_window, daemon=True).start()
        return False


# Alive for the life of the process: NSApplication does not retain its delegate.
REOPENER = LiberaReopener.alloc().init()


def _name_the_application() -> None:
    """Say Libera in the menu bar and in what the system reports.

    Outside `Libera.app` the running process's main bundle is the interpreter's
    own: Homebrew's `Python.app`, whose CFBundleName is "Python". So a
    developer running `libera` got "About Python" and "Hide Python" in the
    application menu, and "Python" as the bold item in the menu bar.

    The main bundle's info dictionary is mutable and both names come out of it,
    so setting them fixes the menu at the source: AppKit builds the titles from
    the right name. The fix this replaced corrected the titles item by item
    afterwards, and only ever reached the ones someone had thought of.
    Measured after the change: "Libera" in the menu bar, "About
    Libera" in the menu, and "Libera Suite" from `lsappinfo` and from another
    process's `NSRunningApplication.localizedName()`.

    **The one constraint is to run before
    `NSApplication.sharedApplication()`.** Measured: the same two lines after
    the shared application exists change nothing at all, not even before
    `setActivationPolicy_`. So this runs from prepare(), ahead of
    `webview.start()`, and cannot move into complete_startup() with the rest
    of the start-up work.

    Both keys, mirroring `build/macos/macos-app.sh`'s Info.plist: CFBundleName is the
    menu bar, CFBundleDisplayName is what the system reports elsewhere. Inside
    the bundle both already hold these values, so this is a no-op there.

    **Nothing here can fix the Dock tile's name.** That name
    is the bundle's *filename* on disk, which for us is `Python.app` and is not
    ours to rename. Measured against the tile itself, three ways: this change
    leaves it at "Python"; the private `_LSSetApplicationInformationItem` sets
    the LaunchServices display name, which is already "Libera Suite" and which
    the tile ignores; and the same build launched as `Libera.app` reads
    "Libera", as `Libera Suite.app` reads "Libera Suite". The icon has an
    override (`_wear_the_application_icon`) because AppKit messages the Dock
    for that one; the name has no counterpart. A bundle is the answer.

    **Check any of this from outside the process.** Every reading available
    in here lies in both directions:
    `NSRunningApplication.currentApplication()` reports the dictionary it was
    just handed whether or not it took, `NSWorkspace.frontmostApplication()`
    reported "Python" for a run whose menu bar was on screen saying Libera, and
    `lsappinfo` reported "Libera Suite" for a run whose Dock tile said Python.
    For the tile, ask the Dock:

        osascript -e 'tell application "System Events" to tell process "Dock"
                      to get name of every UI element of list 1'
    """
    info = Foundation.NSBundle.mainBundle().infoDictionary()
    info["CFBundleName"] = "Libera"
    info["CFBundleDisplayName"] = "Libera Suite"

    # The attribution too, for the same reason and out of the same dictionary.
    # AppKit's standard About panel reads NSHumanReadableCopyright from the main
    # bundle, which outside `Libera.app` is the interpreter's: "About Libera"
    # showed *"(c) 2001-2023 Python Software Foundation"* and named neither
    # upstream nor the licence. Measured on Homebrew's Python.app, which is what
    # a pipx or uv install runs. Inside the bundle `macos-app.sh` already writes
    # the same string, so this is a no-op there.
    info["NSHumanReadableCopyright"] = about.COPYRIGHT
    # The versions too, which the panel shows as "Version 0.4.0 (payload 0.4)":
    # outside the bundle they were the interpreter's, or nothing.
    info["CFBundleShortVersionString"] = about.app_version()
    info["CFBundleVersion"] = f"payload {locate.PAYLOAD_VERSION}"


def _wear_the_application_icon() -> None:
    """Show the Libera mark in the Dock.

    The same gap as `_name_the_application`, and the other half of what that
    fixes: the Dock takes its icon from the running process's main bundle, and
    outside `Libera.app` that bundle is the interpreter's. So `libera` from a
    virtualenv came up under a rocket. setApplicationIconImage_ overrides it
    for the life of the process. It is harmless inside the bundle, where it
    sets the icon to the drawing the .icns was made from.

    Unlike the name, this one cannot run early: it needs `NSApp`, and the name
    has to be set *before* anything creates it. So the two sit at opposite ends
    of startup on purpose.

    `icon.svg` ships in the wheel and is the one copy of the mark in the
    repository; `build/macos/macos-icon.py` and `lb app flatpak`
    (libera_build/flatpak.py) read the same file.

    NSImage has read SVG only since macOS 13. On 11 and 12 it returns nil,
    leaving nothing to do but keep the rocket: an application that launches
    with the wrong icon is better than one that does not launch. The
    bundle is unaffected either way, because its icon is an .icns.
    """
    # resources.files: the icon is package data two directories up from this
    # module, and counting parents (`Path(__file__).parents[2]`) is how six test
    # files broke the moment they moved. See notes/lessons-learned/data-and-paths.md.
    icon = resources.files("libera") / "icon.svg"
    image = AppKit.NSImage.alloc().initWithContentsOfFile_(str(icon))
    if image is None:
        logger.debug("no Dock icon: %s did not read as an image", icon)
        return
    AppKit.NSApp.setApplicationIconImage_(image)


def _quieten_system_items() -> None:
    """Stop macOS adding Dictation and Emoji & Symbols to the Edit menu.

    It adds them to any menu titled Edit; here it added each of them more than
    once. These are the documented off-switches, but they are only read while
    the menu is being built, so this has to run before the application starts.

    registerDefaults_ lives for the process; setBool_forKey_ would write into
    the user's preferences for whatever bundle we happen to be running as.
    """
    Foundation.NSUserDefaults.standardUserDefaults().registerDefaults_({
        "NSDisabledDictationMenuItem": True,
        "NSDisabledCharacterPaletteMenuItem": True,
    })


def _pack_fourcc(code: bytes) -> int:
    """An Apple Event Manager name, such as b"odoc", as the integer it is."""
    return int.from_bytes(code, "big")


def _accept_documents_from_finder() -> None:
    """Open the documents Finder sends while Libera.app is already running.

    Finder launches Libera.app only when it is not running, and that launch
    reaches the launcher (build/macos/launcher.m), which hands the documents to
    this process as arguments. Once it runs, the launcher has become this
    process, so a double-click sends it an "open documents" Apple Event instead,
    and nothing here answered one. AppKit's fallback then asked the document
    types an NSDocument application declares, of which this has none, and said
    "Libera cannot open files in the PowerPoint Presentation (.pptx) format"
    about a file it opens perfectly well at launch.
    """
    events = AppKit.NSAppleEventManager.sharedAppleEventManager()
    events.setEventHandler_andSelector_forEventClass_andEventID_(
        OPEN_DOCUMENTS,
        b"handleOpen:withReply:",
        _pack_fourcc(b"aevt"),
        _pack_fourcc(b"odoc"),
    )


class LiberaDocumentOpener(AppKit.NSObject):
    """What the "open documents" event is sent to."""

    @objc.typedSelector(b"v@:@@")
    def handleOpen_withReply_(self, event, _reply) -> None:
        documents = _read_documents(event)
        logger.info("finder: open %s", ", ".join(d.name for d in documents))
        # Off the GUI thread, which this is: opening converts the document
        # first, as a hand-off from a second `libera` does.
        threading.Thread(target=_open_each, args=(documents,), daemon=True).start()


# Alive for the life of the process: the event manager does not retain its
# handlers.
OPEN_DOCUMENTS = LiberaDocumentOpener.alloc().init()


def _read_documents(event) -> list[Path]:
    """The files an "open documents" event names, as paths."""
    listed = event.paramDescriptorForKeyword_(_pack_fourcc(b"----"))
    if listed is None:
        return []
    count = listed.numberOfItems()
    items = [listed.descriptorAtIndex_(i) for i in range(1, count + 1)] or [listed]
    urls = (item.fileURLValue() for item in items)
    return [Path(url.path()) for url in urls if url is not None]


def _open_each(documents: list[Path]) -> None:
    for document in documents:
        hooks.shell.open_window(document)
