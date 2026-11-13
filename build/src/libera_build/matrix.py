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

Then, in another clean container of each, install.sh's pip path, the one a
user without Flatpak takes, from the staged origin (origin.staged), served on
the builder's loopback and reached over the host's network: where the
distribution's Python is 3.12 or newer it must install libera and convert a
document with it, and where it is older it must refuse, saying so.

The Flatpak is not what this checks. It carries its own runtime and does not
care what the distribution is; this is the payload the wheel installs.
"""

from __future__ import annotations

import functools
import http.server
import os
import re
import subprocess
import sys
import tempfile
import threading
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from libera_build.containers import Engine, Mount, Run, linux_platform
from libera_build.process import run_quietly
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

# The floor of every family docs/src/main/install.md names, then the newest
# Ubuntu LTS and Fedora, which users are likelier to have. Fully qualified:
# podman otherwise resolves short names through an alias table and says so on
# stderr, which is where the loader's error goes too.
DISTROS = (
    "docker.io/library/ubuntu:22.04",
    "docker.io/library/debian:12",
    "docker.io/library/fedora:36",
    "docker.io/library/almalinux:9",
    "docker.io/library/ubuntu:24.04",
    "docker.io/library/ubuntu:26.04",
    "docker.io/library/fedora:45",
)
# What the sample document says, so what a conversion must still say.
NEEDLE = "Second paragraph"
# The oldest Python install.sh's pip path accepts, as major * 100 + minor.
PYTHON_FLOOR = 312
REFUSAL = "no Python 3.12 or newer"

# A user's desktop has python3 and curl, and the image has neither; venv too,
# which install.sh names when it is missing. Then the install page's command,
# with the pip channel, and a document converted by what it installed.
PIP_PATH = """
if command -v apt-get > /dev/null; then
    apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \\
        python3 python3-venv curl ca-certificates > /dev/null
else
    dnf install -y -q python3 $(command -v curl > /dev/null || echo curl) > /dev/null
fi
python3 -c 'import sys; print("PYTHON=%d%02d" % sys.version_info[:2])'
curl -fsSL "$LIBERA_ORIGIN/install.sh" | sh -s -- --channel pip > "/w/$LOG" 2>&1
"$HOME/.local/bin/libera" --convert /w/note.txt -t odt -o "/w/$OUT" -q
"""

if TYPE_CHECKING:
    from collections.abc import Generator


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


def pip_path_in(
    engine: Engine, image: str, arch: str, origin: str, work: Path
) -> tuple[bool, str]:
    """install.sh's pip path in one clean container: whether it did what the
    distribution's Python calls for, and what it did."""
    name = image.rsplit("/", 1)[-1].replace(":", "-")
    log, out = f"install-{arch}-{name}.log", f"pip-{arch}-{name}.odt"
    env = {
        "LIBERA_ORIGIN": origin,
        "PIP_FIND_LINKS": f"{origin}/pypi/",
        "LOG": log,
        "OUT": out,
    }
    if version := os.environ.get("LIBERA_VERSION"):
        env["LIBERA_VERSION"] = version
    run_ = Run(
        image,
        ("sh", "-c", PIP_PATH),
        arch,
        mounts=(Mount(work, "/w"),),
        env=env,
        extra=("--quiet", "--network", "host"),
    )
    done = subprocess.run(
        engine.run_argv(run_), capture_output=True, text=True, check=False
    )
    said = (work / log).read_text(errors="replace") if (work / log).is_file() else ""
    return pip_verdict(done.stdout + done.stderr, said, work / out)


def pip_verdict(output: str, said: str, odt: Path) -> tuple[bool, str]:
    """Whether install.sh's pip path did right, and what it did, from what
    the container printed, what install.sh said and what it converted:
    installed and converted where Python is 3.12 or newer, refused with a
    reason where it is older."""
    found = re.search(r"^PYTHON=(\d)(\d\d)$", output, re.MULTILINE)
    if not found:
        lines = output.strip().splitlines()
        return False, f"no python3 to try: {lines[-1] if lines else 'no output'}"
    python = f"Python {found.group(1)}.{int(found.group(2))}"
    if int(found.group(1) + found.group(2)) < PYTHON_FLOOR:
        if REFUSAL in said:
            return True, f"refused, as it should on {python}"
        return False, f"{python} was not refused"
    if holds_text(odt, NEEDLE):
        return True, f"installed and converted, on {python}"
    tail = said.strip().splitlines()[-3:]
    return False, f"installed nothing that converts, on {python}: " + " / ".join(tail)


class Quiet(http.server.SimpleHTTPRequestHandler):
    """A file server that does not log each request to stderr."""

    @override
    def log_message(self, format: str, *args: Any) -> None:
        pass


@contextmanager
def served(zone: Path) -> Generator[str]:
    """`zone` over HTTP on this machine's loopback, for as long as needed."""
    handler = functools.partial(Quiet, directory=str(zone))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()


def run(zone: Path, arches: tuple[str, ...], engine: Engine | None = None) -> None:
    """Every architecture in `arches` (x86_64, arm64) against every image in
    DISTROS, from the staged origin `zone`: the converter alone, from the
    libera-core wheel in its pypi/, then install.sh's pip path."""
    engine = engine or Engine.here()
    engine.refuse_remote()
    dist = zone / "pypi"
    failed = 0
    with (
        tempfile.TemporaryDirectory(prefix="libera-matrix-") as scratch,
        served(zone) as origin,
    ):
        work = Path(scratch)
        make_sample(dist, work)
        (work / "note.txt").write_text(f"First paragraph\n\n{NEEDLE}\n")
        for arch in arches:
            archive = core_of(dist, arch)
            core = unpack(archive, work / f"core-{arch}")
            step(f"{arch}, from {archive}")
            for image in DISTROS:
                name = image.rsplit("/", 1)[-1]
                said = convert_in(engine, image, arch, core, work)
                x2t = "ok" if said is None else f"FAIL: {said}"
                say(f"    {name:<16} x2t         {x2t}")
                passed, did = pip_path_in(engine, image, arch, origin, work)
                say(f"    {name:<16} install.sh  {'' if passed else 'FAIL: '}{did}")
                failed += (said is not None) + (not passed)
    say()
    if failed:
        msg = f"{failed} combination(s) could not convert"
        raise RefusedError(msg)
    say("PASS")


if __name__ == "__main__":
    # On a Linux builder, which `distros` sends its part of the staged origin:
    # python3 -m libera_build.matrix ZONE ARCH...
    run(Path(sys.argv[1]), tuple(sys.argv[2:]))
