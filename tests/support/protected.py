"""Protected documents, made the way a save makes one: a document opened,
then exported with its password, which x2t encrypts with (OLE for OOXML,
AES-CBC for OpenDocument). Needs a payload."""

from __future__ import annotations

import base64
import hashlib
import re
import zipfile
import zlib
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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


def make_protected(
    app: apps.App, ext: str, tmp_path: pathlib.Path, password: str = SECRET
) -> pathlib.Path:
    """A document of `app`'s kind, saved as `ext` under `password`, or under
    none when it is "". Words and Tables hold SENTENCE; Slides is its blank."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    if app is apps.SLIDES:
        assert app.blank is not None
        source = payload_mod.resolve().root / "empty" / app.blank
    else:
        source = tmp_path / ("source.txt" if app is apps.WORDS else "source.csv")
        source.write_text(SENTENCE + "\n", encoding="utf-8")
    plain = open_in(app, source, tmp_path / "plain")
    plain.password = password
    protected = tmp_path / f"{'Protected' if password else 'Plain'}.{ext}"
    convert.export(plain, protected, app.ids_by_ext[ext], None)
    sessions.SESSIONS.clear()
    return protected


def is_encrypted(path: pathlib.Path) -> bool:
    if path.read_bytes().startswith(b"\xd0\xcf\x11\xe0"):
        return True  # OOXML: an OLE file holding EncryptionInfo and the package
    with zipfile.ZipFile(path) as package:
        if "META-INF/manifest.xml" not in package.namelist():
            return False  # OOXML in the clear
        return b"encryption-data" in package.read("META-INF/manifest.xml")


def tamper(path: pathlib.Path) -> None:
    """Make an encrypted OOXML file fail its integrity check and nothing
    else: one character of the HMAC its EncryptionInfo stores, in clear
    XML, changed. The package still decrypts and reads as it did, so only
    the check can refuse it. Changing the package itself garbles a block of
    the ZIP, which x2t then refuses whatever the check says."""
    data = path.read_bytes()
    value = data.index(b'encryptedHmacValue="') + len(b'encryptedHmacValue="')
    flipped = b"B" if data[value : value + 1] == b"A" else b"A"
    path.write_bytes(data[:value] + flipped + data[value + 1 :])


def _attribute(entry: str, name: str) -> str:
    found = re.search(rf'manifest:{name}="([^"]+)"', entry)
    assert found is not None, name
    return found.group(1)


def read_odf_parts(path: pathlib.Path, password: str) -> dict[str, tuple[bytes, int]]:
    """Each encrypted part of an ODF file x2t wrote, decrypted as LibreOffice
    does (SHA-256 start key, PBKDF2-SHA1, AES-256-CBC): its text, and how
    many bytes of W3C padding ended it. A part whose padding is not where
    its deflate stream ends raises: LibreOffice refuses those."""
    parts = {}
    with zipfile.ZipFile(path) as package:
        manifest = package.read("META-INF/manifest.xml").decode()
        for entry in re.findall(
            r"<manifest:file-entry .*?</manifest:file-entry>", manifest, re.DOTALL
        ):
            name = re.search(r'manifest:full-path="([^"]+)"', entry)
            assert name is not None
            assert "aes256-cbc" in _attribute(entry, "algorithm-name")
            assert _attribute(entry, "key-derivation-name") == "PBKDF2"
            start = hashlib.sha256(password.encode()).digest()
            key = hashlib.pbkdf2_hmac(
                "sha1",
                start,
                base64.b64decode(_attribute(entry, "salt")),
                int(_attribute(entry, "iteration-count")),
                32,
            )
            iv = base64.b64decode(_attribute(entry, "initialisation-vector"))
            decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
            plain = decryptor.update(package.read(name.group(1))) + decryptor.finalize()
            pad = plain[-1]
            assert 1 <= pad <= 16, f"{name.group(1)}: no padding block"
            inflater = zlib.decompressobj(-15)
            text = inflater.decompress(plain[:-pad]) + inflater.flush()
            assert inflater.eof, f"{name.group(1)}: cut short"
            assert not inflater.unused_data, f"{name.group(1)}: no padding"
            assert len(text) == int(_attribute(entry, "size")), name.group(1)
            parts[name.group(1)] = (text, pad)
    return parts
