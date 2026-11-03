"""Inside the LibreOffice reference container: what LibreOffice's own signature services
say of OOXML files, and files they sign. Run by `tests/support/libreoffice.py`, never here.

    python3 reference.py verify FILE...      a JSON line per file
    python3 reference.py sign IN OUT KEY     KEY a PKCS#12 file, its passphrase
                                             in LIBERA_PASSPHRASE

A package is opened as a plain zip storage. Opened as an OOXML one, which
hides `[Content_Types].xml`, every file had no signature at all (measured on
2026-11-03): the signature code tells OOXML from ODF by that part.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

import uno

PIPE = "libera_reference"
NSS = "/tmp/nss"
READ = uno.getConstantByName("com.sun.star.embed.ElementModes.READ")
READWRITE = uno.getConstantByName("com.sun.star.embed.ElementModes.READWRITE")
NoConnectError = uno.getClass("com.sun.star.connection.NoConnectException")


def key_store(key: str | None) -> None:
    """The NSS store LibreOffice signs from and checks against: empty, or
    holding `key`."""
    pathlib.Path(NSS).mkdir()
    subprocess.run(
        ["certutil", "-N", "-d", f"sql:{NSS}", "--empty-password"], check=True
    )
    if key:
        subprocess.run(
            [
                "pk12util",
                "-i",
                key,
                "-d",
                f"sql:{NSS}",
                "-W",
                os.environ["LIBERA_PASSPHRASE"],
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    os.environ["MOZILLA_CERTIFICATE_FOLDER"] = f"sql:{NSS}"


def office():
    """A headless LibreOffice, and its component context once it answers."""
    subprocess.Popen(
        [
            "soffice",
            "--headless",
            "--invisible",
            "--norestore",
            "--nologo",
            f"--accept=pipe,name={PIPE};urp;",
            "-env:UserInstallation=file:///tmp/profile",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    for _ in range(300):
        try:
            return resolver.resolve(
                f"uno:pipe,name={PIPE};urp;StarOffice.ComponentContext"
            )
        except NoConnectError:
            time.sleep(0.2)
    sys.exit("LibreOffice did not answer in a minute")


def service(ctx, name: str):
    return ctx.ServiceManager.createInstanceWithContext(name, ctx)


def storage(ctx, path: str, mode: int):
    zip_format = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    zip_format.Name, zip_format.Value = "StorageFormat", "ZipFormat"
    url = uno.systemPathToFileUrl(str(pathlib.Path(path).resolve()))
    args = (url, mode, uno.Any("[]com.sun.star.beans.PropertyValue", (zip_format,)))
    factory = service(ctx, "com.sun.star.embed.StorageFactory")
    return uno.invoke(factory, "createInstanceWithArguments", (args,))


def verify(ctx, path: str) -> dict:
    signatures = service(ctx, "com.sun.star.security.DocumentDigitalSignatures")
    found = signatures.verifyDocumentContentSignatures(storage(ctx, path, READ), None)
    return {
        "file": pathlib.Path(path).name,
        "signatures": [
            {
                "valid": bool(one.SignatureIsValid),
                "signer": one.Signer.SubjectName if one.Signer else "",
            }
            for one in found
        ],
    }


def sign(ctx, source: str, out: str) -> dict:
    shutil.copyfile(source, out)
    initializer = service(ctx, "com.sun.star.xml.crypto.SEInitializer")
    environment = initializer.createSecurityContext("").getSecurityEnvironment()
    (certificate,) = environment.getPersonalCertificates()
    signatures = service(ctx, "com.sun.star.security.DocumentDigitalSignatures")
    done = signatures.signDocumentWithCertificate(
        certificate, storage(ctx, out, READWRITE), None
    )
    return {"signed": bool(done), "signer": certificate.SubjectName}


def main() -> None:
    verb, *args = sys.argv[1:]
    key_store(args[2] if verb == "sign" else None)
    ctx = office()
    if verb == "verify":
        for path in args:
            print(json.dumps(verify(ctx, path)), flush=True)
    else:
        print(json.dumps(sign(ctx, args[0], args[1])), flush=True)


main()
