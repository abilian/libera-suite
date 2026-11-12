"""`lb release check`'s distros phase: does the Linux converter about to be
published run where we say it runs?

For each architecture and each image, it unpacks that architecture's
libera-core wheel, as `stage` left it for this commit, into a clean container
and has x2t convert a docx to odt, the way the host runs it, then looks for
the document's text in what came out. The glibc
floor was wrong once already: the x86_64 core built on noble needed GLIBC 2.38
and would not load on Ubuntu 22.04 or Debian 12 (notes/13). Its first run
found the install page claiming Fedora 35 and RHEL 9, where glibc 2.34 cannot
load a core that needs 2.35.

The Flatpak is not what this checks. It carries its own runtime and does not
care what the distribution is; this is the payload the wheel installs.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from libera_build.containers import Engine, Mount, Run, linux_platform
from libera_build.process import run_quietly
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

# The floor of every family docs/src/main/install.md names, and the newest
# Ubuntu LTS. Fully qualified: podman otherwise resolves short names through an
# alias table and says so on stderr, which is where the loader's error goes too.
DISTROS = (
    "docker.io/library/ubuntu:22.04",
    "docker.io/library/debian:12",
    "docker.io/library/fedora:36",
    "docker.io/library/almalinux:9",
    "docker.io/library/ubuntu:24.04",
)
# What the sample document says, so what a conversion must still say.
NEEDLE = "Second paragraph"


def holds_text(odt: Path, needle: str) -> bool:
    """Whether a converted document says what it should. The text, not the
    exit status: x2t has written well-formed empty documents and exited 0
    before (CLAUDE.md, "things that fail silently")."""
    try:
        xml = zipfile.ZipFile(odt).read("content.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
    return needle in re.sub(r"<[^>]+>", "", xml)


def make_sample(dist: Path, work: Path) -> Path:
    """The sample docx, built on the blank the staged libera-web wheel ships,
    so that nothing but the staged files is needed."""
    blank = work / "new.docx"
    webs = sorted(dist.glob("libera_web-*.whl"))
    if not webs:
        msg = f"no libera-web wheel in {dist}"
        raise RefusedError(msg)
    blank.write_bytes(zipfile.ZipFile(webs[-1]).read("libera_web/empty/new.docx"))
    sample = work / "in.docx"
    run_quietly(
        [sys.executable, str(REPO / "tests/support/make_sample_docx.py"), str(sample)],
        "the sample document",
        env={**os.environ, "LIBERA_BLANK": str(blank)},
    )
    return sample


def core_of(dist: Path, arch: str) -> Path:
    """That architecture's libera-core wheel."""
    machine = "aarch64" if linux_platform(arch).endswith("arm64") else "x86_64"
    wheels = sorted(dist.glob(f"libera_core-*-manylinux_*_{machine}.whl"))
    if not wheels:
        msg = f"no libera-core wheel for {machine} in {dist}"
        raise RefusedError(msg)
    return wheels[-1]


def unpack(archive: Path, into: Path) -> Path:
    """A libera-core wheel, unpacked: the directory holding its bin/. zipfile
    drops the modes, which pip restores from the entries, so does this."""
    with zipfile.ZipFile(archive) as whl:
        for entry in whl.infolist():
            whl.extract(entry, into)
            if mode := entry.external_attr >> 16 & 0o777:
                (into / entry.filename).chmod(mode)
    return into / "libera_core"


def convert_in(
    engine: Engine, image: str, arch: str, core: Path, work: Path
) -> str | None:
    """Convert the sample in one clean container: None if the text came
    through, else the first thing the container said, which is where the
    loader names a missing symbol version."""
    out = f"out-{arch}-{image.replace(':', '-').replace('/', '-')}.odt"
    run_ = Run(
        image,
        ("/core/bin/x2t", "/w/in.docx", f"/w/{out}"),
        arch,
        mounts=(Mount(core, "/core", read_only=True), Mount(work, "/w")),
        env={"LD_LIBRARY_PATH": "/core/bin", "APPLICATION_NAME": "Libera Suite"},
        extra=("--quiet",),
    )
    done = subprocess.run(
        engine.run_argv(run_), capture_output=True, text=True, check=False
    )
    if holds_text(work / out, NEEDLE):
        return None
    lines = (done.stdout + done.stderr).strip().splitlines()
    return lines[0] if lines else "no output"


def run(dist: Path, arches: tuple[str, ...], engine: Engine | None = None) -> None:
    """Every architecture in `arches` (x86_64, arm64) against every image in
    DISTROS, from the libera-core and libera-web wheels in `dist`."""
    engine = engine or Engine.here()
    engine.refuse_remote()
    failed = 0
    with tempfile.TemporaryDirectory(prefix="libera-matrix-") as scratch:
        work = Path(scratch)
        make_sample(dist, work)
        for arch in arches:
            archive = core_of(dist, arch)
            core = unpack(archive, work / f"core-{arch}")
            step(f"{arch}, from {archive}")
            for image in DISTROS:
                said = convert_in(engine, image, arch, core, work)
                name = image.rsplit("/", 1)[-1]
                if said is None:
                    say(f"    {name:<16} ok")
                else:
                    failed += 1
                    say(f"    {name:<16} FAIL: {said}")
    say()
    if failed:
        msg = f"{failed} combination(s) could not convert"
        raise RefusedError(msg)
    say("PASS")
