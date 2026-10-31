"""Protected documents, made the way a save makes one: a document opened,
then exported with its password, which x2t encrypts with (OLE for OOXML,
AES-CBC for OpenDocument). Needs a payload."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

from libera import payload as payload_mod
from libera.host import apps, convert, opening, session as sessions
from libera.host.session import Session

if TYPE_CHECKING:
    import pathlib

SECRET = "zqx-Secret-4471"
SENTENCE = "Libera keeps this sentence"


def open_in(app: apps.App, document: pathlib.Path, work: pathlib.Path) -> Session:
    session = Session(
        payload=payload_mod.resolve().root, work=work, document=document, app=app
    )
    sessions.configure(session)
    opening.open_document(session, document)
    return session


def make_protected(app: apps.App, ext: str, tmp_path: pathlib.Path) -> pathlib.Path:
    """A document of `app`'s kind, saved as `ext` under SECRET. Words and
    Tables hold SENTENCE; Slides is its blank."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    if app is apps.SLIDES:
        assert app.blank is not None
        source = payload_mod.resolve().root / "empty" / app.blank
    else:
        source = tmp_path / ("source.txt" if app is apps.WORDS else "source.csv")
        source.write_text(SENTENCE + "\n", encoding="utf-8")
    plain = open_in(app, source, tmp_path / "plain")
    plain.password = SECRET
    protected = tmp_path / f"Protected.{ext}"
    convert.export(plain, protected, app.ids_by_ext[ext], None)
    sessions.SESSIONS.clear()
    return protected


def is_encrypted(path: pathlib.Path) -> bool:
    if path.read_bytes().startswith(b"\xd0\xcf\x11\xe0"):
        return True  # OOXML: an OLE file holding EncryptionInfo and the package
    with zipfile.ZipFile(path) as package:
        return b"encryption-data" in package.read("META-INF/manifest.xml")
