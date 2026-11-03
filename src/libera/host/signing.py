"""Digital signatures, through `libera-sign`, on the file on disk.

The signing library has a C++ interface only, so a program beside x2t does
the work (core patch 0190, notes/plans/release-0.7-protection.md): it lists a
package's signatures as the editor reads them, signs with a key file, removes
signatures, and prints a signer's certificate. Signing works on the saved
file, never on the editor's state: x2t's save rebuilds the package from
Editor.bin and drops every signature, which is what the editor's "Editing
will remove signatures" says.

The passphrase of a key goes to the program on its standard input, never on
its command line, where any process listing shows it, and is kept in memory
only, for the window it was typed in (`Session.certificate`).
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import pathlib
import re
import shutil
import tempfile
import zipfile
from typing import TYPE_CHECKING

from libera.host import convert, hooks, saving
from libera.host.session import ChosenCertificate, is_inside
from libera.payload import locate

if TYPE_CHECKING:
    from libera.host.session import Session

logger = logging.getLogger(__name__)

# The formats the signer signs: OOXML packages. ODF has no signing upstream,
# and the PDF editor has signatures off.
SIGNABLE = frozenset({
    *(".docx", ".docm", ".dotx", ".dotm"),
    *(".xlsx", ".xlsm", ".xltx", ".xltm"),
    *(".pptx", ".pptm", ".ppsx", ".ppsm", ".potx", ".potm"),
})
# libera-sign's exit status for a key or certificate that did not load.
NO_KEY = 3
NO_SIGNATURES: dict = {"count": 0, "data": []}
# Whitespace between the elements of a relationships part. x2t writes some in
# every .docx and .pptx it saves; core's signer leaves it out of what it
# digests, LibreOffice keeps it in, and so LibreOffice refused every such
# signature made here (measured 2026-11-03,
# tests/b_integration/host/test_signatures_libreoffice.py). With none there,
# the two digest the same bytes.
BETWEEN_ELEMENTS = re.compile(rb">\s+<")


class SigningError(Exception):
    """libera-sign could not do what it was asked."""


class KeyRefusedError(SigningError):
    """The key or its certificate did not load: a wrong passphrase, or a file
    that is neither."""


def is_signable(session: Session) -> bool:
    """Whether the editor offers signatures for this window's document.

    Not for a protected document in 0.7: the signer works on a zip, and an
    encrypted OOXML file is not one (decided 2026-11-01).
    """
    document = session.read_current_document()
    return (
        session.editor.converted
        and document is not None
        and document.suffix.lower() in SIGNABLE
        # A zip: an encrypted OOXML file is not one, and the editor asks
        # whether to offer signatures before its password is typed.
        and zipfile.is_zipfile(document)
        and not session.password
        # Nor File > New's copy of a blank, in the state folder: signed there,
        # it would be saved where the user chooses by x2t, which drops the
        # signature. Nor a file someone else has open.
        and not is_inside(session.scratch, document)
        and session.locked_by is None
        and session.layout.sign.is_file()
    )


def _run(session: Session, *args: str, passphrase: str | None = None) -> str:
    """libera-sign with `args`, its answer on standard output. Watched as x2t
    is: `verify` reads every signed document opened, its parts whole, and a
    hostile one could ask for gigabytes."""
    argv = [str(session.layout.sign), *args]
    try:
        run = convert.run_watched(
            argv,
            locate.make_tool_env(session.layout.bin),
            stdin="" if passphrase is None else passphrase + "\n",
        )
    except (OSError, convert.ConversionError) as e:
        msg = f"libera-sign {args[0]} did not finish: {e}"
        raise SigningError(msg) from e
    if run.returncode == NO_KEY:
        msg = "the key or its certificate did not load"
        raise KeyRefusedError(msg)
    if run.returncode != 0:
        logger.error("libera-sign %s: exit %s\n%s", args[0], run.returncode, run.stderr)
        msg = f"libera-sign {args[0]} failed (exit status {run.returncode})"
        raise SigningError(msg)
    return run.stdout


def list_signatures(session: Session) -> dict:
    """The document's signatures, as `DesktopOfflineAppDocumentSignatures`
    reads them, from the file on disk."""
    document = session.read_current_document()
    if not is_signable(session) or document is None or not saving.is_signed(document):
        return NO_SIGNATURES
    return json.loads(_run(session, "verify", str(document)))


def choose_certificate(
    session: Session, key: pathlib.Path, cert: pathlib.Path | None, passphrase: str
) -> ChosenCertificate:
    """Load a key, and its certificate when the key file holds none: the
    window's certificate from now on. Raises KeyRefusedError."""
    found = json.loads(
        _run(session, "info", str(key), str(cert or ""), passphrase=passphrase)
    )
    chosen = ChosenCertificate(key, cert, passphrase, found["name"], found["date"])
    session.certificate = chosen
    return chosen


def sign(
    session: Session, certificate_id: str, guid: str, images: tuple[str, str]
) -> dict:
    """Sign the document on disk with the window's certificate; the
    signatures it then has. `images` are the editor's PNG `data:` URLs, the
    signature line's valid and invalid pictures, both "" for an invisible
    signature."""
    chosen = session.certificate
    if chosen is None or chosen.id != certificate_id:
        msg = "no such certificate chosen in this window"
        raise SigningError(msg)
    document = _signable_document(session)
    _save_edits_first(session, document)
    work = pathlib.Path(tempfile.mkdtemp(dir=session.work, prefix="sign-"))
    try:
        pictures = [
            _write_picture(work, name, url)
            for name, url in zip(("valid.png", "invalid.png"), images, strict=True)
        ]
        staged = work / f"signed{document.suffix}"
        _run(
            session,
            "sign",
            str(_tight_relationships(document, work)),
            str(staged),
            str(chosen.key),
            str(chosen.cert or ""),
            guid,
            *pictures,
            passphrase=chosen.passphrase,
        )
        saving.replace_document(staged, document)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    logger.info("signed %s", document.name)
    return list_signatures(session)


def _tight_relationships(document: pathlib.Path, work: pathlib.Path) -> pathlib.Path:
    """A copy of `document` in `work` whose relationships parts have no
    whitespace between their elements, which changes nothing they say. A `<`
    is never literal inside an attribute's value, so `>`, spaces, `<` is
    always between two tags."""
    copy = work / f"tight{document.suffix}"
    with zipfile.ZipFile(document) as source, zipfile.ZipFile(copy, "w") as out:
        for part in source.infolist():
            data = source.read(part)
            if part.filename.endswith(".rels"):
                data = BETWEEN_ELEMENTS.sub(b"><", data)
            # The part's own entry, so its compression too.
            out.writestr(part, data)
    return copy


def remove_signature(session: Session, guid: str) -> dict:
    """Remove one signature, by its GUID, or all of them for "": the
    signatures the document then has. None, for a file that has none: after
    a Save As, the editor may still show the signatures of the file it left,
    and its Edit anyway removes them all."""
    current = session.read_current_document()
    if current is None or not saving.is_signed(current):
        return NO_SIGNATURES
    document = _signable_document(session)
    work = pathlib.Path(tempfile.mkdtemp(dir=session.work, prefix="unsign-"))
    try:
        staged = work / f"unsigned{document.suffix}"
        _run(session, "remove", str(document), str(staged), guid)
        saving.replace_document(staged, document)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    logger.info(
        "removed %s from %s",
        "a signature" if guid else "every signature",
        document.name,
    )
    return list_signatures(session)


def describe_signer(session: Session, index: int) -> dict:
    """The certificate of the document's signature at `index`, in the last
    list the editor was sent: its details, and its text."""
    document = _signable_document(session)
    return json.loads(_run(session, "certificate", str(document), str(index)))


def _save_edits_first(session: Session, document: pathlib.Path) -> None:
    """Edits the file does not have yet, saved first, once the user agrees.

    The editor asks itself when it knows of edits (SaveQuestion), but after a
    reload or a crash recovery it starts unmodified with the edits folded
    into what it shows, and the file on disk lacks them: signed as it is, the
    signature would cover what the user never saw.
    """
    if not session.unsaved_marker.is_file():
        return
    if not hooks.shell.confirm_save_before_signing(document):
        msg = "the document has edits that are not saved"
        raise SigningError(msg)
    saved = saving.save_document(session, saving.PLAIN_SAVE)
    if saved["error"] != saving.SaveOutcome.SAVED:
        msg = "the document's edits could not be saved"
        raise SigningError(msg)


def _signable_document(session: Session) -> pathlib.Path:
    document = session.read_current_document()
    if document is None or not is_signable(session):
        msg = "this window's document cannot be signed"
        raise SigningError(msg)
    return document


def _write_picture(work: pathlib.Path, name: str, url: str) -> str:
    """A signature line's picture, from the editor's `data:` URL, as a file
    the program reads; "" when there is none."""
    if not url:
        return ""
    head, _, data = url.partition(",")
    if not head.startswith("data:image/png;base64"):
        msg = "a signature's picture is not a PNG data URL"
        raise SigningError(msg)
    try:
        picture = base64.b64decode(data, validate=True)
    except binascii.Error as e:
        msg = "a signature's picture is not base64"
        raise SigningError(msg) from e
    path = work / name
    path.write_bytes(picture)
    return str(path)
