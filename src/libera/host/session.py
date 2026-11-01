"""Sessions: one per window, one per open document.

They share a server and therefore an origin, which is what keeps localStorage
-- theme, units, spellcheck language -- the same in every window. A server per
window would give each one its own port and its own empty settings.

The server looks up the session each request names in its query string and
hands it on; nothing finds a session any other way. It used to be bound
to the thread serving the request, as `H`, and every thread bug this host had
came from reading `H` on a thread that had bound none, or the wrong one.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import pathlib
import secrets
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar

from libera.host import apps, language
from libera.host.changelog import ChangeLog
from libera.payload import fonts, locate

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Session:
    """One window: where its files are, what is open in it, and what the host
    learns while it is.

    The last three fields used to be three dictionaries keyed by session id,
    in three modules -- here, `window` and `server` -- and closing a window
    cleared one of them. Held here, they go when the session does.
    """

    payload: pathlib.Path
    work: pathlib.Path
    # The index of the fonts installed on the machine this window was opened
    # with (payload/fonts.py), or None for the payload's own fonts alone.
    fonts: pathlib.Path | None = None
    document: pathlib.Path | None = None
    shot: pathlib.Path | None = None
    # Which editor this window is. Derived from the document when not given,
    # so `libera sheet.xlsx` opens Tables.
    app: apps.App | None = None
    # pywebview's uid for the window showing this session, once there is one.
    window: str | None = None
    # What the editor last said it can do -- undo, redo -- so a menu can grey
    # out what would decline. Pushed by the editor, never asked for.
    abilities: dict[str, bool] = field(default_factory=dict)
    # Whether a reload has been offered for an error already: an editor that
    # throws once throws again; a dialog per repeat is worse than the fault.
    reload_offered: bool = False
    # Who else has this document open, as their lock file says, when it was
    # found locked on opening: "Ada Lovelace, since 03.10.2026 20:20".
    locked_by: str | None = None
    # The files the shell has handed this window's page by path -- chosen in
    # an open dialog, or dropped -- and so the only ones the page may ask the
    # host to copy in. A path of the page's own choosing reads any file the
    # user can.
    offered: set[pathlib.Path] = field(default_factory=set)
    # Held while the change log is written and while x2t reads it: the editor
    # streams edits on one thread while a save, a close or a reload converts
    # on another, and a log read half-appended loses the last edit.
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    # The conversion of the document, while its window loads the editor
    # (opening.convert_behind); asking for Editor.bin waits for it.
    converting: threading.Thread | None = field(default=None, repr=False)

    @property
    def id(self) -> str:
        """The id the registry knows it by, which every request from its
        window names in the query string: its directory's name.

        A field once, set by `configure`, so a session that skipped it had an
        id of "" -- which `lookup` reads as "the first session", another
        window's. Derived, it cannot be missing or disagree with the directory.
        """
        return self.work.name

    @property
    def editor(self) -> apps.App:
        if self.app is not None:
            return self.app
        return apps.choose_for(self.document) if self.document else apps.WORDS

    # --- the payload, read-only
    @property
    def layout(self) -> locate.Layout:
        """Where each part of the payload is: see locate.Layout."""
        return locate.Layout(self.payload)

    @property
    def all_fonts(self) -> pathlib.Path:
        """The AllFonts.js of filesystem paths, which x2t reads."""
        return self.fonts / "AllFonts.js" if self.fonts else self.layout.all_fonts

    @property
    def font_dir(self) -> pathlib.Path:
        """Where x2t finds font_selection.bin, which it calls its font folder."""
        return self.fonts or self.layout.sdkjs_common

    @property
    def unsaved_marker(self) -> pathlib.Path:
        """Marks a session whose document has edits that are not in the file.

        Beside the session's doc/ directory, because that is rebuilt on every
        open and this has to be read before that happens.
        """
        return self.work / "unsaved.json"

    @property
    def scratch(self) -> pathlib.Path:
        """Where untitled documents are copied out to.

        Beside the recents file, which is what keeps them out of the Recent
        list: remember_recent refuses anything under that directory, because
        it is our plumbing.

        One hop from `work`, like every other path here. Deriving it from two
        hops -- "the state directory" -- reads better and breaks the moment
        anyone nests a session differently, which every test does.
        """
        return self.work.parent / "untitled"

    @property
    def recents(self) -> pathlib.Path:
        """Remembered documents.

        Beside the session directory: a session is rebuilt from the document
        on every open, while this has to outlive that.
        """
        return self.work.parent / "recents.json"

    @property
    def blank(self) -> pathlib.Path:
        """The blank File > New starts from, for the editor this session is."""
        return self.choose_blank(None)

    def choose_blank(self, app: apps.App | None) -> pathlib.Path:
        """The same, for an editor named by the caller.

        The start window asks for a spreadsheet from a session that is showing
        nothing, so "which editor" cannot always come from the session.
        """
        app = app or self.editor
        if app.blank is None:
            msg = f"{app.title} cannot create documents"
            raise NotReadyError(msg)
        return language.find_blank_dir(self.layout.blanks) / app.blank

    # --- session state, written
    @property
    def doc(self) -> pathlib.Path:
        return self.work / "doc"

    @property
    def editor_bin(self) -> pathlib.Path:
        return self.doc / "Editor.bin"

    @property
    def media(self) -> pathlib.Path:
        return self.doc / "media"

    @property
    def change_log(self) -> ChangeLog:
        """Every edit since the document was opened, as the editor streamed it."""
        return ChangeLog(self.doc / "changes" / "changes0.json")

    @property
    def out_dir(self) -> pathlib.Path:
        return self.work / "out"

    @property
    def current_file(self) -> pathlib.Path:
        return self.work / "current.txt"

    def read_current_document(self) -> pathlib.Path | None:
        """The document this window has open: where Save writes, and what
        Save As moves it to. On disk, beside the session, so recovery can
        read it after a crash."""
        if not self.current_file.is_file():
            return None
        text = read_atomically(self.current_file).strip()
        return pathlib.Path(text) if text else None

    def write_current_document(self, document: pathlib.Path) -> None:
        write_atomically(self.current_file, str(document))

    def mark_modified(self, modified: bool) -> None:
        """Record whether the editor has edits the file does not.

        The editor tells us on every transition, which is a better signal than
        the change log: the log stays non-empty after a save, because it is
        the delta from the document as it was opened.
        """
        if modified:
            self.work.mkdir(parents=True, exist_ok=True)
            write_atomically(
                self.unsaved_marker,
                json.dumps({
                    "document": str(self.read_current_document() or ""),
                    "at": time.time(),
                }),
            )
        else:
            self.unsaved_marker.unlink(missing_ok=True)


# One window, one session, one document -- the shape LibreOffice and every
# other desktop editor has. They share a server and therefore an origin, which
# is what keeps localStorage (theme, units, spellcheck language) the same in
# every window; a server per window would give each one its own port and its
# own empty settings.
SESSIONS: dict[str, Session] = {}
# Request threads, the GUI thread and pywebview's event threads all add, drop
# and look up sessions. Adding and dropping are single operations, safe as
# they are; whoever walks the registry walks a snapshot, `list(SESSIONS...)`,
# or the walk can fail with "dictionary changed size during iteration".


def lookup(session_id: str) -> Session:
    """The session with that id, or the first if no id is given.

    An HTTP request names its session in the query string. A static request
    names none, and gets the first, which is harmless because the payload is
    shared.

    An id that matches no session is refused, not defaulted. It used to fall
    back to the first session, so a request still on its way from a window
    that had closed went to another window's document: a change-log write with
    an undo index truncated that document's log.
    """
    if not session_id:
        # A snapshot: another thread may be adding or dropping a window.
        session_id = next(iter(list(SESSIONS)), "")
    found = SESSIONS.get(session_id)
    if found is None:
        msg = f"no session {session_id!r}" if session_id else "no sessions"
        raise NotReadyError(msg)
    return found


def configure(session: Session) -> None:
    """Register a session under its id, and make its directories."""
    SESSIONS[session.id] = session
    session.work.mkdir(parents=True, exist_ok=True)
    session.out_dir.mkdir(parents=True, exist_ok=True)
    if session.document is not None:
        session.write_current_document(session.document)


def new_work(root: pathlib.Path) -> pathlib.Path:
    """A session directory of its own under `root`. The first window's was
    `0` in every process, so two at once shared one."""
    return root / secrets.token_hex(6)


def create_session(document: pathlib.Path | None = None) -> Session:
    """A second window's worth of state, beside the first.

    Sessions share the payload and the recents list and nothing else: each has
    its own working copy, change log and unsaved marker, because each is
    editing a different document, and its own font list, the newest when it
    was made.
    """
    template = next(iter(list(SESSIONS.values())))
    layout = locate.Layout(template.payload)
    # The fonts as they are now, if their index is built; and if it is not, it
    # is built for the windows after this one.
    fonts.build_behind(layout, {s.fonts for s in list(SESSIONS.values())})
    made = Session(
        payload=template.payload,
        work=new_work(template.work.parent),
        fonts=fonts.choose(layout),
        document=document,
    )
    if template.shot is not None:
        # One name per window, under the name `--shot` gave: two windows
        # posting to one path would leave whichever painted last, and the
        # window that never painted is the one worth catching.
        made.shot = template.shot.with_name(
            f"{template.shot.stem}-{made.id}{template.shot.suffix}"
        )
    configure(made)
    return made


def find_session_showing(document: pathlib.Path) -> Session | None:
    """The live session that has this document open, if one does.

    Compared as files. A symlink, or another case on a case-insensitive disk,
    spells the same document differently; a second window on it would save
    over the first.
    """
    for found in list(SESSIONS.values()):
        current = found.read_current_document()
        try:
            if current is not None and current.samefile(document):
                return found
        except OSError:
            # One of the two is gone; then they are not the same open file.
            continue
    return None


def drop_session(session_id: str) -> None:
    """Forget a closed window, and all the host learned about it.

    Its directory stays: it may hold unsaved edits.
    """
    SESSIONS.pop(session_id, None)


def is_inside(root: pathlib.Path, f: pathlib.Path) -> bool:
    """Is `f` a real file inside `root`, with no `..` escaping it?

    Both sides have to be resolved. Comparing an unresolved root against
    resolved parents silently fails the moment the root is itself a symlink --
    which is what happens the moment a served directory is a symlink -- an
    installed payload, or a link into a build tree.
    """
    return f.is_file() and root.resolve() in f.resolve().parents


class NotReadyError(RuntimeError):
    """The session cannot be served, said in terms a user can act on."""


def sweep_sessions(root: pathlib.Path, keep: set[str]) -> None:
    """Delete session directories no one is using and nothing needs.

    A window per document means a directory per document, and a directory that
    holds no unsaved edits after its window has gone is just litter.
    """
    if not root.is_dir():
        return
    for d in root.glob("*"):
        if not d.is_dir() or d.name in keep or (d / "unsaved.json").is_file():
            continue
        # Only sessions. The untitled documents live in this directory too and
        # are not litter: deleting them would take somebody's unsaved new
        # document with them. A session has been configured, so it
        # has doc/ or out/; nothing else in here does.
        if not (d / "doc").is_dir() and not (d / "out").is_dir():
            continue
        shutil.rmtree(d, ignore_errors=True)


def write_atomically(path: pathlib.Path, text: str) -> None:
    """Replace a file in one step: a reader sees the old file or the new one.

    `write_text` empties the file and then fills it, and a reader in between
    -- another window, the start window -- saw it empty or half-written, took
    that for "nothing there", and saved its own view over everyone else's.
    """
    # A name of its own, so that two writers -- two threads, or two copies of
    # Libera Suite after a failed hand-off -- never share a staging file.
    fd, staged = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    _retrying(lambda: pathlib.Path(staged).replace(path))


def read_atomically(path: pathlib.Path) -> str:
    """A file `write_atomically` writes, read whole: the old text or the new."""
    return _retrying(lambda: path.read_text(encoding="utf-8"))


# Windows will not replace a file another thread has open, nor open one while
# it is being replaced: PermissionError, on either side. On the Windows builder
# two readers and one writer, for two seconds, had 1,940 of 2,216 replaces fail
# and 883 reads; a failed read of the Recent list is an empty one, which the
# next save then writes over everyone's entries. Each side holds the file for
# microseconds, so trying again is enough. Elsewhere PermissionError is a real
# refusal, and it is raised half a second later than it would have been.
RETRIES = 50
RETRY_PAUSE = 0.01
T = TypeVar("T")


def _retrying(action: Callable[[], T]) -> T:
    for _ in range(RETRIES):
        with contextlib.suppress(PermissionError):
            return action()
        time.sleep(RETRY_PAUSE)
    return action()
