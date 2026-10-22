"""`lb linux`: this repository's checks on Linux, in a container.

Everything about Libera Suite is verified on a Mac, and this is the one place
the host, the bridge and the editor are exercised on Linux at all. Two
containers already build things (the payload and the Flatpak) and neither runs
a test from tests/; this one does.

`test` and `gui` cover different halves and neither subsumes the other. The
suite drives `libera --serve` with headless Chromium, which is the editor and
the bridge but not the window; `gui` opens the window pywebview actually builds
on Linux -- GTK 3 and WebKitGTK, a stack that exists nowhere on macOS.

The scripts that run *inside* the container stay shell: running uv, pytest
and xvfb-run in a Debian image is what shell is for. What moved here is
everything around them: the engine, the image, the volumes, which payload.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera.payload import locate
from libera_build import repo, versions
from libera_build.buildbox import exported_dist
from libera_build.containers import Engine, Mount, Run, host_arch, interactive
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from pathlib import Path

# uv sync into /venv, and the payload installed the way a user installs it --
# through the manifest, with every hash checked. Both are volume-cached, so
# this is a no-op on the second run.
#
# UV_PYTHON=/usr/bin/python3 (in the Dockerfile) and the pyvenv.cfg line
# together, because neither works alone. PyGObject is not a wheel -- it is the
# distribution's /usr/lib/python3/dist-packages/gi -- so an environment built on
# a downloaded interpreter can never reach it whatever else is set, and one
# built on the system interpreter still cannot until system site-packages are
# switched on. Without both, gui.is_gtk_available() is False in here and every
# test that opens a window is testing the wrong machine. This is the same trap
# a user meets: `pipx install libera` reports no window on a box with every GTK
# package installed, and `pipx install --system-site-packages libera` reports
# one. gui.py says so.
#
# With a mounted payload the status check passes and nothing is installed;
# with artifacts it installs, which is what a user does.
#
# Playwright's own Chromium, which is not the system's: the keyboard, slideshow
# and start-window tests drive Playwright, which refuses to run against anything
# it did not install -- fifteen tests skipped on Linux for want of it, which
# reads as coverage the suite does not have. PLAYWRIGHT_BROWSERS_PATH points
# into the venv volume, so this is a download once and a no-op after.
#
# `lint` takes the environment and neither of the other two: a type checker
# reads no payload. It used to install one all the same, and so stopped the
# day the payload version moved ahead of every Linux payload here.
SYNC = """set -e
uv sync --group dev --quiet
sed -i 's/^include-system-site-packages = false/include-system-site-packages = true/' \\
    /venv/pyvenv.cfg
uv run --no-sync python -c 'import gi' \\
    || { echo 'FATAL: the venv still cannot import gi' >&2; exit 1; }"""
# Installs whenever /dist holds other artifacts than the last install's, and
# not only when no payload works: a payload rebuilt under the same version
# passes --payload-status, and the state volume kept the one before it.
PREPARE = f"""{SYNC}
if [ -e /dist/manifest.json ] && ! cmp -s /dist/manifest.json /state/installed-from.json
then
    uv run --no-sync libera --payload-install --from /dist \\
        && cp /dist/manifest.json /state/installed-from.json
else
    uv run --no-sync libera --payload-status >/dev/null 2>&1 \\
        || uv run --no-sync libera --payload-install --from /dist
fi
uv run --no-sync playwright install chromium >/dev/null 2>&1 \\
    || {{ echo 'FATAL: playwright could not install a browser' >&2; exit 1; }}"""

# The type checkers, on Linux. `sys.platform` is a fact at check time, so a
# checker on a Mac prunes every non-macOS branch before looking at it. Two real
# defects lived in those branches -- a `Window | None` dereferenced in
# set_fullscreen and a list with no inferrable element type in
# find_front_window -- both invisible on the Mac and reported on the first
# Linux run. A check that never ran elsewhere is a check of where it ran.
LINT = """set -e
uv run --no-sync ruff check
uv run --no-sync ruff format --check
uv run --no-sync ty check src build/src
uv run --no-sync pyrefly check src build/src
uv run --no-sync mypy src build/src"""

# The three questions the host asks, on the platform where they were answered
# "no" without asking. gui-smoke opens a window; this one opens a dialog.
DIALOG = """set -e
xvfb-run -a --server-args='-screen 0 1600x1000x24' \\
    uv run --no-sync python build/test-linux/dialog-smoke.py"""

# The screen is bigger than WINDOW_SIZE because Xvfb has no window manager:
# nothing re-places a window, and pywebview centres it, so a 1400-wide window
# on a 1280-wide screen sat at x=-60 with its menu bar off the edge.
#
# WEBKIT_DISABLE_COMPOSITING_MODE and LIBGL_ALWAYS_SOFTWARE because Xvfb has no
# GPU: without them WebKit tries an accelerated path, and what comes back is a
# window that maps and never paints -- exactly the failure gui-smoke.py looks
# for, so it would report a bug that is not one.
#
# Two documents of different types, because that is the shape a beta tester
# reported as impossible against the Flatpak, and the code that opens the
# second is not the code that opens the first.
GUI = """set -e
uv run --no-sync python tests/support/make_sample_docx.py /tmp/sample.docx >/dev/null
root=$(uv run --no-sync python -c \\
    'from libera.payload import locate; print(locate.resolve().root)')
cp "$root/empty/new.pptx" /tmp/sample.pptx
export WEBKIT_DISABLE_COMPOSITING_MODE=1 LIBGL_ALWAYS_SOFTWARE=1
xvfb-run -a --server-args='-screen 0 1600x1000x24' \\
    uv run --no-sync python build/test-linux/gui-smoke.py \\
        /tmp/sample.docx /tmp/sample.pptx /repo/build/out/gui-linux.png"""


# tests/d_gui: the application in a real GTK window, as pytest rather than as
# a script. Same display and same software rendering as GUI above, and for the
# same reasons; `-m gui` is what the root conftest wants before it will let
# them run at all.
GUI_TEST = """set -e
export WEBKIT_DISABLE_COMPOSITING_MODE=1 LIBGL_ALWAYS_SOFTWARE=1
xvfb-run -a --server-args='-screen 0 1600x1000x24' \\
    uv run --no-sync pytest -p no:cacheprovider -m gui"""


@dataclass(frozen=True)
class LinuxOptions:
    action: str
    arch: str | None = None  # default: this machine's
    dist: Path | None = None  # payload artifacts to install from
    payload: Path | None = None  # an unpacked payload, used as is
    lang: str | None = None  # the container's LANG, which picks the host's language
    pytest_args: tuple[str, ...] = ()


def newest_complete_payload(data_dir: Path) -> Path | None:
    """The newest installed payload that is complete, of any version.

    `resolve()` wants PAYLOAD_VERSION exactly; a window check does not care
    which payload drew the window, only that one did. Newest by number: a plain
    sort puts 0.10 before 0.9.
    """
    if not data_dir.is_dir():
        return None
    found = [d for d in data_dir.iterdir() if d.is_dir() and locate.is_complete(d)]

    def key(d: Path) -> tuple[int, ...]:
        return tuple(int(p) if p.isdigit() else -1 for p in d.name.split("."))

    return max(found, key=key, default=None)


def choose_payload(options: LinuxOptions, arch: str) -> tuple[Path | None, Path | None]:
    """The artifacts to install from, or failing those a payload to mount.

    Artifacts first, because installing them is what a user does: the ones
    asked for, else the container build's, else a native build's. Then an
    unpacked payload: the one asked for, else the newest installed here.
    """
    if options.payload:
        return None, options.payload
    dist = (
        options.dist or exported_dist(arch) or repo.dist(versions.payload_version(REPO))
    )
    if dist.is_dir():
        return dist, None
    if found := newest_complete_payload(locate.get_data_dir()):
        say(f"==> no artifacts in {dist}; using the installed payload {found.name}")
        say(f"    {found}  (--payload DIR overrides)")
        return None, found
    msg = (
        f"no payload artifacts in {dist}, and no installed payload\n"
        f"  build them:  lb payload container --arch {arch}\n"
        "  or point at a directory: --dist DIR, or a payload: --payload DIR"
    )
    raise RefusedError(msg)


def mounts_for(arch: str, dist: Path | None, payload: Path | None) -> list[Mount]:
    """The repository, two volumes, and the payload. Two volumes because both
    are expensive and neither belongs in the repository: the virtualenv with
    Linux wheels, and the installed payload."""
    mounts = [
        Mount(REPO, "/repo"),
        Mount(f"libera-test-venv-{arch}", "/venv"),
        Mount(f"libera-test-state-{arch}", "/state"),
    ]
    if payload:
        mounts.append(Mount(payload, "/payload", read_only=True))
    # Only when they are there: mounting a directory that does not exist made
    # the engine refuse to start, before anything could say what it wanted.
    if dist and dist.is_dir():
        mounts.append(Mount(dist, "/dist", read_only=True))
    return mounts


def env_for(payload: Path | None, lang: str | None = None) -> dict[str, str]:
    env = {
        "XDG_DATA_HOME": "/state",
        "HOME": "/state",
        # __pycache__ would otherwise land in the bind-mounted repository,
        # owned by root on a Linux host and mixed in with the Mac's own.
        "PYTHONPYCACHEPREFIX": "/tmp/pycache",
    }
    # A mounted payload is taken as given and its version not checked --
    # deliberately, per payload/locate.py -- which is the only way in when
    # this checkout's PAYLOAD_VERSION has moved ahead of every payload here.
    if payload:
        env["LIBERA_PAYLOAD"] = "/payload"
    # The host reads LC_ALL, LC_MESSAGES, then LANG (host/language.py); the
    # image sets none, so LANG alone decides.
    if lang:
        env["LANG"] = lang
    return env


def script_for(options: LinuxOptions) -> str:
    """What runs in the container for an action, preparation included."""
    # -p no:cacheprovider, like PYTHONPYCACHEPREFIX: nothing this run does
    # should show up in `git status` on the host. Quoted, because the line is
    # shell: -k "bridge and save" is one argument.
    test = shlex.join([
        *("uv", "run", "--no-sync", "pytest", "-p", "no:cacheprovider"),
        *options.pytest_args,
    ])
    return {
        "versions": "cat /etc/libera-test-image.txt",
        "shell": "exec /bin/bash",
        "lint": f"{SYNC}\n{LINT}",
        "test": f"{PREPARE}\n{test}",
        "dialog": f"{PREPARE}\n{DIALOG}",
        "gui": f"{PREPARE}\n{GUI}",
        "gui-test": f"{PREPARE}\n{GUI_TEST}",
    }[options.action]


def run(options: LinuxOptions, engine: Engine | None = None) -> int:
    engine = engine or Engine.here()
    engine.refuse_remote()
    arch = options.arch or host_arch()
    image = engine.image(f"libera-test-linux-{arch}")
    build = engine.build_argv(image, REPO / "build" / "test-linux", arch=arch)
    if options.action == "image":
        return subprocess.call(build)
    if not engine.has_image(image):
        step("building the image first")
        if status := subprocess.call(build):
            return status

    needs_payload = options.action not in {"versions", "shell", "lint"}
    dist, payload = choose_payload(options, arch) if needs_payload else (None, None)
    if dist is not None:
        versions.stamp_bundled_manifest(REPO, dist)
    step(f"{options.action}, on Linux ({arch})")
    argv = engine.run_argv(
        Run(
            image,
            ("-c", script_for(options)),
            arch,
            mounts=tuple(mounts_for(arch, dist, payload)),
            env=env_for(payload, options.lang),
            workdir="/repo",
            interactive=interactive(),
            extra=("--pull=never",),
        )
    )
    status = subprocess.call(argv)
    if options.action == "gui" and status == 0:
        say("    screenshot: build/out/gui-linux.png")
    return status
