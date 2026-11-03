"""LibreOffice as the reference for what an OOXML signature is worth.

A second implementation, written apart from ours (core's `COOXMLVerifier`
and `COOXMLSigner`), whose verdict a test takes as the expected one. Its
verdicts come from its own UNO services, which `reference.py` runs inside a
container: the machine's LibreOffice belongs to whoever uses it, and a
headless one started beside theirs is not ours to start.

The image is Debian's LibreOffice, built the first time a test asks for it
and named by the hash of its Dockerfile, so a change to it builds a new one.
Both files are in `libreoffice-reference/`. With no container engine
running, the tests that need it skip: on the Mac that is OrbStack or Docker
stopped, and fedora.zt runs them with podman.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
from dataclasses import dataclass

import pytest
from libera_build.containers import Engine, Mount, Run, host_arch

HERE = pathlib.Path(__file__).parent / "libreoffice-reference"
# Debian's packages, the first time: a couple of minutes.
BUILD_SECONDS = 20 * 60
# LibreOffice's start, then a few files: a few seconds.
RUN_SECONDS = 5 * 60


class LibreOfficeError(RuntimeError):
    """LibreOffice did not answer: a fault of the reference, never a verdict."""


@dataclass(frozen=True)
class Signature:
    valid: bool
    signer: str  # the certificate's subject, "CN=..."


@dataclass(frozen=True)
class LibreOffice:
    engine: Engine
    image: str
    work: pathlib.Path

    def verify(self, paths: list[pathlib.Path]) -> list[list[Signature]]:
        """The signatures of each file, as LibreOffice judges them, in order."""
        folder = self._fresh("verify")
        names = []
        for i, path in enumerate(paths):
            names.append(f"{i}-{path.name}")
            shutil.copyfile(path, folder / names[-1])
        lines = self._run(folder, "verify", *names)
        if [line["file"] for line in lines] != names:
            msg = f"LibreOffice answered for {len(lines)} of {len(names)} files"
            raise LibreOfficeError(msg)
        return [
            [Signature(s["valid"], s["signer"]) for s in line["signatures"]]
            for line in lines
        ]

    def sign(
        self,
        document: pathlib.Path,
        out: pathlib.Path,
        key: pathlib.Path,
        passphrase: str,
    ) -> None:
        """`document` signed by LibreOffice into `out`, with the PKCS#12 `key`.

        Refused unless LibreOffice then finds the signature valid itself:
        what a test makes of it is otherwise a verdict on nothing.
        """
        folder = self._fresh("sign")
        shutil.copyfile(document, folder / f"in{document.suffix}")
        shutil.copyfile(key, folder / "key.p12")
        (line,) = self._run(
            folder,
            "sign",
            f"in{document.suffix}",
            f"out{document.suffix}",
            "key.p12",
            env={"LIBERA_PASSPHRASE": passphrase},
        )
        signed = folder / f"out{document.suffix}"
        if not line["signed"] or not signed.is_file():
            msg = f"LibreOffice did not sign {document.name}: {line}"
            raise LibreOfficeError(msg)
        (own,) = self.verify([signed])
        if not own or not all(s.valid for s in own):
            msg = f"LibreOffice does not accept its own signature: {own}"
            raise LibreOfficeError(msg)
        shutil.copyfile(signed, out)

    def _fresh(self, verb: str) -> pathlib.Path:
        folder = self.work / f"{verb}-{len(list(self.work.iterdir()))}"
        folder.mkdir()
        shutil.copyfile(HERE / "reference.py", folder / "reference.py")
        return folder

    def _run(
        self, folder: pathlib.Path, *args: str, env: dict[str, str] | None = None
    ) -> list[dict]:
        run = Run(
            image=self.image,
            command=("python3", "reference.py", *args),
            arch=host_arch(),
            mounts=(Mount(folder, "/w"),),
            env=env or {},
            workdir="/w",
        )
        done = subprocess.run(
            self.engine.run_argv(run),
            capture_output=True,
            text=True,
            timeout=RUN_SECONDS,
            check=False,
        )
        if done.returncode:
            msg = f"LibreOffice's container failed ({done.returncode}):\n{done.stderr[-3000:]}"
            raise LibreOfficeError(msg)
        return [
            json.loads(line)
            for line in done.stdout.splitlines()
            if line.startswith("{")
        ]


def reference(work: pathlib.Path) -> LibreOffice:
    """LibreOffice in its container, built if need be; a skip with no engine."""
    engine = Engine.here()
    if not shutil.which(engine.name):
        pytest.skip(f"no {engine.name}: the LibreOffice reference runs in a container")
    answer = subprocess.run(
        [engine.name, "info"], capture_output=True, timeout=60, check=False
    )
    if answer.returncode:
        pytest.skip(f"{engine.name} is not running: the LibreOffice reference needs it")
    engine.refuse_remote()
    tag = hashlib.sha256((HERE / "Dockerfile").read_bytes()).hexdigest()[:12]
    image = engine.image(f"libera-libreoffice-reference:{tag}")
    if not engine.has_image(image):
        built = subprocess.run(
            engine.build_argv(image, HERE, arch=host_arch()),
            capture_output=True,
            text=True,
            timeout=BUILD_SECONDS,
            check=False,
        )
        if built.returncode:
            msg = f"the LibreOffice image did not build:\n{built.stderr[-3000:]}"
            raise LibreOfficeError(msg)
    work.mkdir(parents=True, exist_ok=True)
    return LibreOffice(engine, image, work)
