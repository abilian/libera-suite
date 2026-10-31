"""Opening a document into a session, and offering back what a crash left."""

from __future__ import annotations

import json
import logging
import pathlib
import shutil
import threading
from typing import TYPE_CHECKING

from libera import timeline
from libera.host import convert, hooks, locking, recents
from libera.host.session import SESSIONS, PasswordAsked, Session

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def open_document(session: Session, document: pathlib.Path) -> None:
    """Prepare the session for a document, converting it for the editor.

    Converting throws away the previous session, so this is the only moment at
    which edits that never reached the file can still be rescued.
    """
    stale = find_recoverable(session, document)
    if stale and hooks.shell.ask_to_recover(document):
        _recover(session, document, stale)
        return
    try:
        convert.convert_to_editor_bin(session, document)
    except convert.PasswordNeededError as e:
        # Nobody to show a failure to: the request that answered fails.
        ask_password(session, document, e.code, lambda _e: None, lambda: None)
    else:
        _converted(session, document)
    if stale and stale != session.work:
        # "Open Saved Version" declines the edits wherever they were. In this
        # session's directory the conversion has just replaced them; left in
        # another, they were offered again on every open.
        (stale / "unsaved.json").unlink(missing_ok=True)
    session.write_current_document(document)
    locking.hold(session, document)


def _converted(session: Session, document: pathlib.Path) -> None:
    """What follows a document's conversion: it is open, as it is on disk."""
    session.unsaved_marker.unlink(missing_ok=True)
    recents.remember_recent(session, document)


def ask_password(
    session: Session,
    document: pathlib.Path,
    code: int,
    failed: Callable[[convert.ConversionError], None],
    done: Callable[[], None],
) -> None:
    """Leave the editor the question of the document's password, which it
    asks with its own dialog when it asks for the document
    (server/document.py). The password typed converts the document, then
    `done`; a wrong one leaves the question again, saying so with x2t's
    WRONG_PASSWORD; any other failure is `failed`'s to show, and raised."""

    def answer(password: str) -> None:
        session.password = password
        try:
            convert.convert_to_editor_bin(session, document)
        except convert.PasswordNeededError as e:
            session.password = ""
            ask_password(session, document, e.code, failed, done)
            return
        except convert.ConversionError as e:
            session.password = ""
            session.password_asked = None
            failed(e)
            raise
        session.password_asked = None
        _converted(session, document)
        done()

    session.password_asked = PasswordAsked(code, answer)


def begin_opening(session: Session, document: pathlib.Path) -> bool:
    """`open_document` for a window, up to the conversion, which then runs while
    the window loads the editor (`convert_behind`). The editor asks for the
    document about two seconds after its window is made, and x2t takes 0.05
    to 0.7 s, more for a Markdown file with pictures on the web: started
    first, the conversion was all added to the wait.

    Here, what has to come before the window: the question about edits a
    crash left, and the lock, which the editor's page reads as it loads.
    True when the document still has to be converted; False when it is the
    recovered edits that open, which are converted already.
    """
    stale = find_recoverable(session, document)
    if stale and hooks.shell.ask_to_recover(document):
        _recover(session, document, stale)
        return False
    if stale and stale != session.work:
        # Declined, as in open_document.
        (stale / "unsaved.json").unlink(missing_ok=True)
    session.write_current_document(document)
    locking.hold(session, document)
    return True


def convert_behind(
    session: Session,
    document: pathlib.Path,
    failed: Callable[[convert.ConversionError], None],
    done: Callable[[], None] = lambda: None,
) -> None:
    """The conversion `begin_opening` left, on a thread of its own; asking for
    Editor.bin waits for it. `done` or `failed` follows, on that thread."""

    def run() -> None:
        try:
            convert.convert_to_editor_bin(session, document)
        except convert.PasswordNeededError as e:
            ask_password(session, document, e.code, failed, done)
            return
        except convert.ConversionError as e:
            failed(e)
            return
        timeline.mark("converted", again=True)
        _converted(session, document)
        done()

    session.converting = threading.Thread(
        target=run, name=f"converting {document.name}", daemon=True
    )
    session.converting.start()


def _recover(session: Session, document: pathlib.Path, stale: pathlib.Path) -> None:
    """Open the unsaved edits a crash left in `stale` instead of the file."""
    if stale != session.work:
        # The edits are in another window's old session; adopt them.
        shutil.rmtree(session.doc, ignore_errors=True)
        shutil.move(str(stale / "doc"), str(session.doc))
        shutil.copyfile(stale / "unsaved.json", session.unsaved_marker)
        shutil.rmtree(stale, ignore_errors=True)
    logger.info("recovered unsaved changes to %s", document)
    session.write_current_document(document)
    recents.remember_recent(session, document)
    locking.hold(session, document)
    marker = json.loads(session.unsaved_marker.read_text(encoding="utf-8"))
    if marker.get("protected") and session.editor.converted:
        _ask_recovered_password(session, document)


def _ask_recovered_password(session: Session, document: pathlib.Path) -> None:
    """A protected document's recovered edits are decrypted already, and open
    without its password; saved without it, they would be written
    unprotected. So the editor asks for it, as on any open, and the password
    typed is checked against the document on disk, in a session of its own
    that is then deleted: a mistyped one would otherwise become the
    document's. A PDF needs none of this, since the editor asks itself."""

    def answer(password: str) -> None:
        check = Session(
            payload=session.payload,
            work=session.work / "password-check",
            fonts=session.fonts,
            document=document,
            app=session.app,
            password=password,
        )
        try:
            convert.convert_to_editor_bin(check, document)
        except convert.PasswordNeededError as e:
            session.password_asked = PasswordAsked(e.code, answer)
            return
        finally:
            shutil.rmtree(check.work, ignore_errors=True)
        session.password = password
        session.password_asked = None

    session.password_asked = PasswordAsked(convert.NO_PASSWORD, answer)


def has_unsaved_edits(found: Session, document: pathlib.Path) -> bool:
    """Does this session's directory hold unsaved edits to that document?"""
    marker = found.unsaved_marker
    if not (marker.is_file() and found.editor_bin.is_file() and found.change_log):
        return False
    try:
        return json.loads(marker.read_text(encoding="utf-8")).get("document") == str(
            document
        )
    except (ValueError, OSError) as e:
        # Answering False here means "nothing to recover": the edits go
        # without the user being asked. That is the right answer for a marker
        # we cannot read, since there is nothing to offer them *about*; it
        # must still never be given without a warning in the log.
        logger.warning("unreadable recovery marker at %s: %s", marker, e)
        return False


def find_recoverable(session: Session, document: pathlib.Path) -> pathlib.Path | None:
    """The session directory holding unsaved edits to this document, if any.

    Any of them, not just this window's: with a window per document the
    session that crashed is rarely the one being opened now.

    Except another window's. Its edits are not a crash's, they are live, and
    recovering them moved its files away and deleted its directory while the
    window was still writing to it -- which is what opening a document twice
    did.
    """
    here = session.work
    live = {found.work for found in list(SESSIONS.values())}
    others = (
        d
        for d in sorted(here.parent.glob("*"))
        if d.is_dir() and d != here and d not in live
    )
    for work in (here, *others):
        # Each read as a session, because where its files are is Session's to say.
        if has_unsaved_edits(Session(payload=session.payload, work=work), document):
            return work
    return None
