"""Sessions: one per window, one per open document.

They share a server and therefore an origin, which is what keeps localStorage
-- theme, units, spellcheck language -- the same in every window. A server per
window would give each one its own port and its own empty settings.

The session for the request being served is bound to the thread serving it, so
the fifty-odd places that need it and nothing else can say `H.doc` without
being handed it.
"""

from __future__ import annotations

import json
import logging
import pathlib
import secrets
import shutil
import threading
import time
from dataclasses import dataclass
from typing import Any

from libera.host import apps

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Host:
    """Where the payload is, where session state goes, and what is open."""

    payload: pathlib.Path
    work: pathlib.Path
    document: pathlib.Path | None = None
    shot: pathlib.Path | None = None
    # Which editor this window is. Derived from the document when not given,
    # so `libera sheet.xlsx` opens Tables rather than showing a
    # spreadsheet to a word processor.
    app: apps.App | None = None

    @property
    def editor(self) -> apps.App:
        if self.app is not None:
            return self.app
        return apps.for_document(self.document) if self.document else apps.WORDS

    # --- the payload, read-only
    @property
    def web(self) -> pathlib.Path:
        """Served at /, so /sdkjs and /web-apps resolve."""
        return self.payload

    @property
    def sdkjs_common(self) -> pathlib.Path:
        return self.payload / "sdkjs" / "common"

    @property
    def service_worker(self) -> pathlib.Path:
        # The editor registers its worker at the *origin root* -- a worker's
        # scope is capped by its own URL path, so it has to sit at "/" to see
        # /web-apps and /sdkjs. The file lives under sdkjs. DocumentServer
        # bridges the gap with an nginx alias; this is that alias.
        return self.sdkjs_common / "serviceworker" / "document_editor_service_worker.js"

    @property
    def fonts(self) -> pathlib.Path:
        """The obfuscated copies the browser downloads."""
        return self.payload / "fonts"

    @property
    def unsaved(self) -> pathlib.Path:
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
        return self.blank_for(None)

    def blank_for(self, app: apps.App | None) -> pathlib.Path:
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
        return self.payload / "bin" / "x2t"

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
    def out(self) -> pathlib.Path:
        return self.work / "out"

    @property
    def current(self) -> pathlib.Path:
        return self.work / "current.txt"


# One window, one session, one document -- the shape LibreOffice and every
# other desktop editor has. They share a server and therefore an origin, which
# is what keeps localStorage (theme, units, spellcheck language) the same in
# every window; a server per window would give each one its own port and its
# own empty settings.
SESSIONS: dict[str, Host] = {}


_current = threading.local()


class _Session:
    """The session the calling thread is serving.

    Fifty-odd places need the session and nothing else. Threading it through
    each of them would be noise that never varies, so the server binds it per
    request from the id in the URL: `H.doc` means "the document this request is
    about" rather than "the one document there is".
    """

    def __getattr__(self, name: str) -> Any:
        host = getattr(_current, "host", None)
        if host is None:
            msg = "no session bound on this thread"
            raise NotReadyError(msg)
        return getattr(host, name)


H = _Session()


# What the editor in each session can do right now, so a menu can grey out
# what would decline. Keyed by session id; the editor pushes changes.
EDITOR_STATE: dict[str, dict] = {}


def use(host: Host, session: str = "") -> None:
    """Bind a session to this thread."""
    _current.host = host
    _current.session = session


def bind(session: str) -> None:
    """Bind the named session to this thread, or the first one if unknown.

    Two callers need this and they arrive very differently: an HTTP request
    names its session in the query string, and a macOS menu action arrives on a
    thread of its own with nothing bound at all. Both want the same answer, and
    both fail the same confusing way without it -- `H` is thread-local, so an
    unbound thread does not get a default, it raises.
    """
    host = SESSIONS.get(session) or next(iter(SESSIONS.values()), None)
    if host is None:
        msg = "no sessions"
        raise NotReadyError(msg)
    use(host, session if session in SESSIONS else next(iter(SESSIONS), ""))


def forget() -> None:
    """Unbind this thread. Used by the tests between cases.

    Nothing in the application calls it: a request thread ends, and the GUI
    thread should never have been bound in the first place.
    """
    _current.__dict__.pop("host", None)
    _current.__dict__.pop("session", None)


def current_session() -> str:
    return getattr(_current, "session", "")


def editor_state(session: str) -> dict:
    """What that session's editor last said it could do."""
    return EDITOR_STATE.get(session, {})


def configure(host: Host, session: str = "0") -> None:
    """Register a session and bind it to this thread."""
    SESSIONS[session] = host
    use(host, session)
    host.work.mkdir(parents=True, exist_ok=True)
    host.out.mkdir(parents=True, exist_ok=True)
    if host.document is not None:
        host.current.write_text(str(host.document), encoding="utf-8")


def new_session(document: pathlib.Path | None = None) -> str:
    """A second window's worth of state, beside the first.

    Sessions share the payload and the recents list and nothing else: each has
    its own working copy, change log and unsaved marker, because each is
    editing a different document.
    """
    template = next(iter(SESSIONS.values()))
    session = secrets.token_hex(6)
    host = Host(
        payload=template.payload,
        work=template.work.parent / session,
        document=document,
    )
    previous = getattr(_current, "host", None)
    configure(host, session)
    if previous is not None:
        use(previous)  # do not steal this thread from the request in progress
    return session


def drop_session(session: str) -> None:
    """Forget a closed window. Its directory stays: it may hold unsaved edits."""
    SESSIONS.pop(session, None)
    EDITOR_STATE.pop(session, None)


def current_path() -> pathlib.Path | None:
    if not H.current.is_file():
        return None
    text = H.current.read_text(encoding="utf-8").strip()
    return pathlib.Path(text) if text else None


def contains(root: pathlib.Path, f: pathlib.Path) -> bool:
    """Is `f` a real file inside `root`, with no `..` escaping it?

    Both sides have to be resolved. Comparing an unresolved root against
    resolved parents silently fails the moment the root is itself a symlink --
    which is what happens the moment a served directory is a symlink -- an
    installed payload, or a link into a build tree.
    """
    return f.is_file() and root.resolve() in f.resolve().parents


class NotReadyError(RuntimeError):
    """The session cannot be served, said in terms a user can act on."""


def set_modified(modified: bool) -> None:
    """Record whether the editor has edits the file does not.

    The editor tells us on every transition, which is a better signal than the
    change log: the log stays non-empty after a save, because it is the delta
    from the document as it was opened.
    """
    if modified:
        H.work.mkdir(parents=True, exist_ok=True)
        H.unsaved.write_text(
            json.dumps({"document": str(current_path() or ""), "at": time.time()}),
            encoding="utf-8",
        )
    else:
        H.unsaved.unlink(missing_ok=True)


def holds_unsaved(work: pathlib.Path, document: pathlib.Path) -> bool:
    """Does this session directory hold unsaved edits to that document?"""
    marker, editor_bin = work / "unsaved.json", work / "doc" / "Editor.bin"
    change_log = work / "doc" / "changes" / "changes0.json"
    if not (marker.is_file() and editor_bin.is_file()):
        return False
    if not change_log.is_file() or change_log.stat().st_size == 0:
        return False
    try:
        return json.loads(marker.read_text(encoding="utf-8")).get("document") == str(
            document
        )
    except (ValueError, OSError) as e:
        # Answering False here means "nothing to recover", and the edits go
        # without the user being asked. That is the right answer for a marker
        # we cannot read -- there is nothing to offer them *about* -- but it
        # is never a right answer to give quietly.
        logger.warning("unreadable recovery marker at %s: %s", marker, e)
        return False


def recoverable(document: pathlib.Path) -> pathlib.Path | None:
    """The session directory holding unsaved edits to this document, if any.

    Any of them, not just this window's: with a window per document the
    session that crashed is rarely the one being opened now.
    """
    if holds_unsaved(H.work, document):
        return H.work
    for other in sorted(H.work.parent.glob("*")):
        if other != H.work and other.is_dir() and holds_unsaved(other, document):
            return other
    return None


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
