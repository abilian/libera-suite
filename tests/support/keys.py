"""Keys to sign with: a certificate a test authority issued, so that the
signer and the issuer differ, in a PKCS#12 file or as PEM files."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

if TYPE_CHECKING:
    import pathlib

PASSPHRASE = "zqx-Pass-4471"
SIGNER = "Zoé Signataire"
ISSUER = "Zqx Test CA"


def _certificate(key):
    issuer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    start = dt.datetime(2026, 3, 5, tzinfo=dt.UTC)
    return (
        x509
        .CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, SIGNER)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ISSUER)]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(dt.datetime(2036, 11, 20, tzinfo=dt.UTC))
        .sign(issuer_key, hashes.SHA256())
    )


def make_pkcs12(folder: pathlib.Path, passphrase: str = PASSPHRASE) -> pathlib.Path:
    """A PKCS#12 file holding a key and its certificate."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "signer.p12"
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"signer",
            key,
            _certificate(key),
            None,
            serialization.BestAvailableEncryption(passphrase.encode()),
        )
    )
    return path


def make_pem(
    folder: pathlib.Path, passphrase: str = PASSPHRASE
) -> tuple[pathlib.Path, pathlib.Path]:
    """A key and its certificate, as two PEM files."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    folder.mkdir(parents=True, exist_ok=True)
    key_path, cert_path = folder / "signer.key", folder / "signer.crt"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(passphrase.encode()),
        )
    )
    cert_path.write_bytes(_certificate(key).public_bytes(serialization.Encoding.PEM))
    return key_path, cert_path
