"""AppKit: windows and dialogs as macOS draws them.

One of the three toolkit modules `windows` chooses between, each a
`portable.Toolkit`. Read on macOS alone, so AppKit is imported once, here.

It also starts the application the way AppKit wants it started: prepare()
before anything exists, complete_startup() once the menu bar does, which is where
Finder's "open documents" events start being answered.

AppKit is main-thread-only, and most of what puts something on screen arrives
on a request thread. `run_on_gui_thread` hands work over; an alert expects to be
called there already, and the save panel hands itself over, because it waits
for a completion handler rather than for a return.
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
from PyObjCTools import AppHelper

from libera.host import about, hooks
from libera.host.window.portable import Answer, Question

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Sequence

    from webview import Window

logger = logging.getLogger(__name__)

T = TypeVar("T")

# AppKit's NSAlertFirstButtonReturn, which pyobjc does not export by name.
# Buttons are numbered from it in the order they were added.
NS_ALERT_FIRST_BUTTON = 1000


def run_on_gui_thread(work: Callable[[], T]) -> T:
    """Run something that touches AppKit, and wait for its answer.

    AppKit is main-thread-only, and it does not warn: "NSWindow should only be
    instantiated on the main thread" is a hard exception that takes the request
    with it. Most of what asks the user a question arrives on a request thread,
    so it has to come back here first.

    Already on it? Call it. Dispatching to the thread we are standing on and
    then waiting for it is a deadlock.

    Whatever the work raises is raised again here, on the thread that asked.
    It used to stay on the GUI thread, where pyobjc logs it and moves on, and
    the caller got None -- which the recovery prompt read as "Open Saved
    Version", so a prompt that failed to appear discarded the edits it was
    there to offer back.
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


def find_key_window(windows: Sequence[Window]) -> Window | None:
    """The key window, else the main one, as pywebview windows.

    pywebview's active_window() is keyWindow, which is None whenever the
    application is not frontmost -- and is the sheet, not the document, while
    a save panel is up. The main window is the document behind it.
    """
    for native in (AppKit.NSApp.keyWindow(), AppKit.NSApp.mainWindow()):
        if native is None:
            continue
        for window in windows:
            # Bound to a local rather than fetched twice: a checker cannot
            # narrow `getattr(x, "native", None)` across a second lookup, and
            # neither can a reader be sure it is the same object.
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


def ask(question: Question, parent: Window | None) -> Answer:
    """An NSAlert, run modally on the GUI thread, which the caller is on.

    The first button added is the default and the rightmost; Cancel goes
    beside it and the choice that discards furthest away, which is the macOS
    order: Save, Cancel, Don't Save. `parent` goes unused: an alert run
    modally belongs to the application, not to a window.
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
    native = getattr(parent, "native", None)

    def show():
        panel, _ = build_save_panel(suggested, formats, start_in)

        def record_choice(response):
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
        if native is not None:
            panel.beginSheetModalForWindow_completionHandler_(native, record_choice)
        else:
            record_choice(panel.runModal())

    AppHelper.callAfter(show)
    done.wait()
    return chosen[0]


def build_save_panel(
    suggested: str, formats: Sequence[tuple[str, str]], start_in: Path | None = None
):
    """The panel and its format popup, built but not shown, in `start_in`.

    `formats` is what the popup offers, and it differs per editor -- Tables has
    no .docx and Words no .xlsx. Always the caller's: this runs on the GUI
    thread, where the session bound is not the window that asked.

    Separate from running it so the wiring can be checked without a dialog on
    screen -- the panel itself runs out of process, so once it is up there is
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

    watcher = LiberaFormatWatcher.alloc().init()
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


class LiberaFormatWatcher(AppKit.NSObject):
    """Keeps the save panel's filename in step with the format popup.

    At module level, so the class is registered with the Objective-C runtime
    once: defining it a second time raises "overriding existing Objective-C
    class", which made the second Save As of a session fail when it was
    defined per panel.
    """

    def formatChanged_(self, sender):
        # Read the name field rather than the name the panel opened with:
        # the popup changes the format, not the name, and by now the user
        # may well have typed one.
        extension = self.extensions[sender.indexOfSelectedItem()]
        current = Path(str(self.panel.nameFieldStringValue()))
        apply_format(self.panel, current, extension, self.extensions)


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
    # First, and not for tidiness: this rewrites the running bundle's
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
    quietly in that case, which is why the symptom was an application with no
    File menu rather than a crash -- and why it came and went.

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


def _name_the_application() -> None:
    """Say Libera, not Python, in the menu bar and in what the system reports.

    Outside `Libera.app` the running process's main bundle is the interpreter's
    own -- Homebrew's `Python.app`, whose CFBundleName is "Python". So a
    developer running `libera` got "About Python" and "Hide Python" in the
    application menu, and "Python" as the bold item in the menu bar.

    The main bundle's info dictionary is mutable and both names come out of it,
    so setting them fixes the menu at the source: AppKit builds the titles from
    the right name rather than being corrected item by item afterwards, which
    is what this replaced and which only ever reached the titles somebody had
    thought of. Measured after the change: "Libera" in the menu bar, "About
    Libera" in the menu, and "Libera Suite" from `lsappinfo` and from another
    process's `NSRunningApplication.localizedName()`.

    **Before `NSApplication.sharedApplication()`, and that is the whole
    constraint.** Measured: the same two lines after the shared application
    exists change nothing at all, not even before `setActivationPolicy_`. So
    this runs from prepare(), ahead of `webview.start()`, and it cannot move
    into complete_startup() with the rest of the start-up work.

    Both keys, mirroring `build/macos-app.sh`'s Info.plist: CFBundleName is the
    menu bar, CFBundleDisplayName is what the system reports elsewhere. Inside
    the bundle both already hold these values, so this is a no-op there.

    **It does not fix the Dock tile's name, and nothing here can.** That name
    is the bundle's *filename* on disk, which for us is `Python.app` and is not
    ours to rename. Measured against the tile itself, three ways: this change
    leaves it at "Python"; the private `_LSSetApplicationInformationItem` sets
    the LaunchServices display name, which is already "Libera Suite" and which
    the tile plainly ignores; and the same build launched as `Libera.app` reads
    "Libera", as `Libera Suite.app` reads "Libera Suite". The icon has an
    override (`_wear_the_application_icon`) because AppKit messages the Dock
    for that one; the name has no counterpart. A bundle is the answer.

    **Check any of this from outside the process**, because every reading
    available in here lies in both directions:
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

    # And the attribution, for the same reason and out of the same dictionary.
    # AppKit's standard About panel reads NSHumanReadableCopyright from the main
    # bundle, which outside `Libera.app` is the interpreter's: "About Libera"
    # showed *"(c) 2001-2023 Python Software Foundation"* and named neither
    # upstream nor the licence. Measured on Homebrew's Python.app, which is what
    # a pipx or uv install runs. Inside the bundle `macos-app.sh` already writes
    # the same string, so this is a no-op there.
    info["NSHumanReadableCopyright"] = about.COPYRIGHT


def _wear_the_application_icon() -> None:
    """Show the Libera mark in the Dock, not Python's rocket.

    The same gap as `name_the_application`, and the other half of what that
    fixes: the Dock takes its icon from the running process's main bundle, and
    outside `Libera.app` that bundle is the interpreter's. So `libera` from a
    virtualenv came up under a rocket. setApplicationIconImage_ overrides it
    for the life of the process, and it is harmless inside the bundle, where it
    sets the icon to the drawing the .icns was made from.

    Unlike the name, this one cannot run early: it needs `NSApp`, and the name
    has to be set *before* anything creates it. So the two sit at opposite ends
    of startup on purpose.

    `icon.svg` ships in the wheel and is the one copy of the mark in the
    repository; `build/macos-icon.py` and `build/flatpak.sh` read the same file.

    NSImage has read SVG only since macOS 13. On 11 and 12 it returns nil, and
    then there is nothing to do but leave the rocket -- an application that
    launches with the wrong icon is better than one that does not launch. The
    bundle is unaffected either way, because its icon is an .icns.
    """
    # resources.files, not Path(__file__).parents[2]: the icon is package data
    # two directories up from this module, and counting parents is how six test
    # files broke the moment they moved. See notes/lessons-learned.md.
    icon = resources.files("libera") / "icon.svg"
    image = AppKit.NSImage.alloc().initWithContentsOfFile_(str(icon))
    if image is None:
        logger.debug("no Dock icon: %s did not read as an image", icon)
        return
    AppKit.NSApp.setApplicationIconImage_(image)


def _quieten_system_items() -> None:
    """Stop macOS adding Dictation and Emoji & Symbols to the Edit menu.

    It adds them to any menu titled Edit, and it added each of them more than
    once here. These are the documented off-switches, but they are only read
    while the menu is being built -- so this has to run before the application
    starts, not when the menus are extended.

    registerDefaults_ rather than setBool_forKey_: the former lives for the
    process, the latter writes into the user's preferences for whatever bundle
    we happen to be running as.
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
