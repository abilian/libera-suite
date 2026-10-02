"""Sessions: one per window, one per open document.

They share a server and therefore an origin, which is what keeps localStorage
-- theme, units, spellcheck language -- the same in every window. A server per
window would give each one its own port and its own empty settings.

Each request names its session in its query string, and the server looks it
up and hands it on; nothing finds a session any other way. It used to be bound
to the thread serving the request, as `H`, and every thread bug this host had
came from reading `H` on a thread that had bound none, or the wrong one.
"""

from __future__ import annotations

import json
import logging
import pathlib
import secrets
import shutil
import time
from dataclasses import dataclass, field

from libera.host import apps
from libera.host.changelog import ChangeLog
from libera.payload import locate

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
    document: pathlib.Path | None = None
    shot: pathlib.Path | None = None
    # Which editor this window is. Derived from the document when not given,
    # so `libera sheet.xlsx` opens Tables rather than showing a
    # spreadsheet to a word processor.
    app: apps.App | None = None
    # pywebview's uid for the window showing this session, once there is one.
    window: str | None = None
    # What the editor last said it can do -- undo, redo -- so a menu can grey
    # out what would decline. Pushed by the editor, never asked for.
    abilities: dict[str, bool] = field(default_factory=dict)
    # Whether a reload has been offered for an error already: an editor that
    # throws once throws again, and a dialog per repeat is worse than the fault.
    reload_offered: bool = False

    @property
    def id(self) -> str:
        """The id the registry knows it by, which every request from its
        window carries in the query string: its directory's name.

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
    def sdkjs_common(self) -> pathlib.Path:
        return self.payload / "sdkjs" / "common"

    @property
    def fonts(self) -> pathlib.Path:
        """The obfuscated copies the browser downloads."""
        return self.payload / "fonts"

    @property
    def unsaved_marker(self) -> pathlib.Path:
        """Marks a session whose document has edits that are not in the file.

        Beside the session rather than inside it, because the session's doc/
        directory is rebuilt on every open and this has to be read before that
        happens.
        """
        return self.work / "unsaved.json"

    @property
    def scratch(self) -> pathlib.Path:
        """Where untitled documents are copied out to.

        Beside the recents file, which is what keeps them out of the Recent
        list: remember_recent refuses anything under that directory, because
        it is our plumbing rather than the user's documents.

        One hop from `work`, like every other path here. Deriving it from two
        hops -- "the state directory" -- reads better and breaks the moment
        anyone nests a session differently, which every test does.
        """
        return self.work.parent / "untitled"

    @property
    def recents(self) -> pathlib.Path:
        """Remembered documents.

        Beside the session directory, not inside it: a session is rebuilt from
        the document on every open, and this has to outlive that.
        """
        return self.work.parent / "recents.json"

    @property
    def all_fonts(self) -> pathlib.Path:
        """The doctrenderer font index: absolute paths to the real TTFs.

        Not sdkjs/common/AllFonts.js, which is the browser's copy and carries
        no paths at all -- hand that one to x2t and it fails deep inside sdkjs
        with "Cannot read property 'length' of null".
        """
        return self.payload / "AllFonts.js"

    @property
    def blank(self) -> pathlib.Path:
        """What File > New starts from, for the editor this session is."""
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
        return self.payload / "empty" / app.blank

    @property
    def x2t(self) -> pathlib.Path:
        return self.payload / "bin" / f"x2t{locate.EXE}"

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
        text = self.current_file.read_text(encoding="utf-8").strip()
        return pathlib.Path(text) if text else None

    def write_current_document(self, document: pathlib.Path) -> None:
        self.current_file.write_text(str(document), encoding="utf-8")

    def mark_modified(self, modified: bool) -> None:
        """Record whether the editor has edits the file does not.

        The editor tells us on every transition, which is a better signal than
        the change log: the log stays non-empty after a save, because it is
        the delta from the document as it was opened.
        """
        if modified:
            self.work.mkdir(parents=True, exist_ok=True)
            self.unsaved_marker.write_text(
                json.dumps({
                    "document": str(self.read_current_document() or ""),
                    "at": time.time(),
                }),
                encoding="utf-8",
            )
        else:
            self.unsaved_marker.unlink(missing_ok=True)


# One window, one session, one document -- the shape LibreOffice and every
# other desktop editor has. They share a server and therefore an origin, which
# is what keeps localStorage (theme, units, spellcheck language) the same in
# every window; a server per window would give each one its own port and its
# own empty settings.
SESSIONS: dict[str, Session] = {}


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
        session_id = next(iter(SESSIONS), "")
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


def create_session(document: pathlib.Path | None = None) -> Session:
    """A second window's worth of state, beside the first.

    Sessions share the payload and the recents list and nothing else: each has
    its own working copy, change log and unsaved marker, because each is
    editing a different document.
    """
    template = next(iter(SESSIONS.values()))
    made = Session(
        payload=template.payload,
        work=template.work.parent / secrets.token_hex(6),
        document=document,
    )
    configure(made)
    return made


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
    """Delete session directories nobody is using and nothing needs.

    A window per document means a directory per document, and a directory that
    holds no unsaved edits after its window has gone is just litter.
    """
    if not root.is_dir():
        return
    for d in root.glob("*"):
        if not d.is_dir() or d.name in keep or (d / "unsaved.json").is_file():
            continue
        # Only sessions. The untitled documents live in this directory too,
        # and they are not litter -- deleting them would take somebody's
        # unsaved new document with them. A session has been configured, so it
        # has doc/ or out/; nothing else in here does.
        if not (d / "doc").is_dir() and not (d / "out").is_dir():
            continue
        shutil.rmtree(d, ignore_errors=True)
