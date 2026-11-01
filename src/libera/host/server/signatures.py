"""A document's digital signatures: listing them, choosing a certificate,
signing, removing, and showing a signer's certificate (host.signing).

The page names a key file, a certificate file or a picture by its path, so
each must be one the user chose in an open dialog this window showed
(`Session.offered`, as for media): a page cannot have the host read a file of
its choosing.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import pathlib

from libera.host import hooks, language, signing
from libera.host.server.api import Refused, Request, Response, answer_json, endpoint

logger = logging.getLogger(__name__)

# What the editor shows when no certificate has been chosen: an empty id.
NO_CERTIFICATE = {"id": "", "name": "", "date": ""}


def _named_window(r: Request) -> None:
    """A request that names no window goes to the first one (session.lookup):
    for these, which read and use one window's certificate, it is refused, so
    that a page cannot sign with another window's."""
    if not r.get_query("session"):
        raise Refused(400, "a signature request names its window")


def _offered(r: Request, field: str) -> pathlib.Path | None:
    """The path in `field`, "" for none, when the user chose it."""
    named = r.read_field(field, str, "")
    if not named:
        return None
    path = pathlib.Path(named)
    if path not in r.session.offered:
        logger.warning("%s refused, never offered: %s", field, path)
        raise Refused(403, f"{field} was never chosen in this window")
    return path


def _signing(work):
    """`work`'s answer, a SigningError said as what it is."""
    try:
        return work()
    except signing.KeyRefusedError as e:
        raise Refused(403, str(e)) from e
    except signing.SigningError as e:
        raise Refused(500, str(e)) from e


@endpoint("GET", "signatures")
def serve_signatures(r: Request) -> Response:
    """The document's signatures, for DesktopOfflineAppDocumentSignatures."""
    _named_window(r)
    return answer_json(_signing(lambda: signing.list_signatures(r.session)))


@endpoint("GET", "certificate")
def serve_certificate(r: Request) -> Response:
    """The window's certificate, for the sign dialog: GetDefaultCertificate."""
    _named_window(r)
    chosen = r.session.certificate
    return answer_json(chosen.for_editor() if chosen else NO_CERTIFICATE)


@endpoint("POST", "certificate")
def choose_certificate(r: Request) -> Response:
    """A key, its certificate when the key holds none, and the passphrase,
    from the bridge's certificate dialog: the signer and dates they show."""
    _named_window(r)
    key = _offered(r, "key")
    if key is None:
        raise Refused(400, "no key file")
    cert = _offered(r, "cert")
    passphrase = r.read_field("passphrase", str, "")
    chosen = _signing(
        lambda: signing.choose_certificate(r.session, key, cert, passphrase)
    )
    return answer_json(chosen.for_editor())


def _changing(heading: str, work):
    """`work`'s answer; when it fails, the user is told too, under `heading`,
    since the editor shows nothing: the file is left as it was."""
    try:
        return _signing(work)
    except Refused:
        hooks.shell.tell(
            heading, language.translate("The document was left as it was.")
        )
        raise


def _name(r: Request) -> str:
    document = r.session.read_current_document()
    return document.name if document else ""


@endpoint("POST", "sign")
def sign(r: Request) -> Response:
    """Sign: the editor's Sign(id, guid, imageValid, imageInvalid)."""
    _named_window(r)
    body = r.read_json()
    certificate_id = str(body.get("id") or "")
    guid = str(body.get("guid") or "")
    images = (str(body.get("imageValid") or ""), str(body.get("imageInvalid") or ""))
    signed = _changing(
        language.translate("Libera Suite could not sign “{name}”", name=_name(r)),
        lambda: signing.sign(r.session, certificate_id, guid, images),
    )
    return answer_json(signed)


@endpoint("POST", "remove-signature")
def remove_signature(r: Request) -> Response:
    """RemoveSignature(guid), and RemoveAllSignatures with no GUID."""
    _named_window(r)
    guid = r.read_field("guid", str, "")
    left = _changing(
        language.translate(
            "Libera Suite could not remove the signature from “{name}”", name=_name(r)
        ),
        lambda: signing.remove_signature(r.session, guid),
    )
    return answer_json(left)


@endpoint("GET", "signer")
def serve_signer(r: Request) -> Response:
    """ViewCertificate(index): the certificate of a signature, by its place
    in the list the editor was last sent."""
    _named_window(r)
    try:
        index = int(r.get_query("index"))
    except ValueError as e:
        raise Refused(400, "index is a number") from e
    return answer_json(_signing(lambda: signing.describe_signer(r.session, index)))


@endpoint("POST", "save-question")
def ask_to_save_first(r: Request) -> Response:
    """SaveQuestion: a document is signed as it is on disk, so one with
    edits is saved first, once the user agrees."""
    _named_window(r)
    document = r.session.read_current_document()
    save = document is not None and hooks.shell.confirm_save_before_signing(document)
    return answer_json({"save": save})


@endpoint("GET", "image")
def serve_image(r: Request) -> Response:
    """GetImageBase64(path): a picture the user chose for a signature, as the
    `data:` URL the sign dialog draws."""
    _named_window(r)
    path = pathlib.Path(r.get_query("path"))
    if path not in r.session.offered:
        logger.warning("image refused, never offered: %s", path)
        raise Refused(403)
    kind = mimetypes.guess_type(path.name)[0] or ""
    if not kind.startswith("image/"):
        raise Refused(400, "not a picture")
    data = base64.b64encode(path.read_bytes()).decode()
    return Response(
        body=f"data:{kind};base64,{data}".encode(), content_type="text/plain"
    )
