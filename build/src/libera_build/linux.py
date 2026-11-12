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

from libera_build import components, versions
from libera_build.containers import (
    Engine,
    Mount,
    Run,
    host_arch,
    interactive,
    linux_platform,
)
from libera_build.repo import REPO, build_root
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from pathlib import Path

# uv sync into /venv, and the components installed the way a user installs
# them: from their wheels. The workspace's own would be built in here, which
# has none of the build's tools. The venv is volume-cached.
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
uv sync --group dev --quiet \\
    --no-install-package libera-core --no-install-package libera-web
sed -i 's/^include-system-site-packages = false/include-system-site-packages = true/' \\
    /venv/pyvenv.cfg
uv run --no-sync python -c 'import gi' \\
    || { echo 'FATAL: the venv still cannot import gi' >&2; exit 1; }"""


# The wheels each time: a rebuild keeps the version, and uv would keep the
# first install. Into /venv by name: uv pip reads no UV_PROJECT_ENVIRONMENT,
# and would find the mounted checkout's .venv. With a payload mounted
# instead, LIBERA_PAYLOAD names it, which resolve() takes first.
def prepare(arch: str) -> str:
    return f"""{SYNC}
if [ -d /wheels ]; then
    uv pip install --python /venv/bin/python --quiet --no-deps --reinstall \\
        /wheels/{core_wheels(arch)} /wheels/libera_web-*.whl
fi
uv run --no-sync playwright install chromium >/dev/null 2>&1 \\
    || {{ echo 'FATAL: playwright could not install a browser' >&2; exit 1; }}"""


def core_wheels(arch: str) -> str:
    """This platform's libera-core wheels, as a glob. The folder can hold others,
    which uv refuses to install beside it: a Mac's, or one under an older tag,
    since `uv build --out-dir` only ever adds."""
    return f"libera_core-*-{components.TAGS[linux_platform(arch)]}.whl"


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
    wheels: Path | None = None  # the component wheels to install
    payload: Path | None = None  # a payload folder, used as is
    lang: str | None = None  # the container's LANG, which picks the host's language
    pytest_args: tuple[str, ...] = ()


def choose_payload(options: LinuxOptions, arch: str) -> tuple[Path | None, Path | None]:
    """The component wheels to install, or a payload folder to mount.

    The wheels by default, because installing them is what a user does: the
    folder asked for, else the one `lb components build` writes, which on a
    Linux machine of this architecture holds its core.
    """
    if options.payload:
        return None, options.payload
    version = versions.payload_version(REPO)
    wheels = options.wheels or build_root() / "out" / "wheels" / version
    if list(wheels.glob(core_wheels(arch))):
        return wheels, None
    msg = (
        f"no libera-core wheel for {linux_platform(arch)} in {wheels}\n"
        f"  build them on Linux:  lb on {linux_platform(arch)} components build\n"
        "  or point at them: --wheels DIR, or at a payload: --payload DIR"
    )
    raise RefusedError(msg)


def mounts_for(arch: str, wheels: Path | None, payload: Path | None) -> list[Mount]:
    """The repository, two volumes, and the components. Two volumes because
    both are expensive and neither belongs in the repository: the virtualenv
    with Linux wheels, and the state a run leaves."""
    mounts = [
        Mount(REPO, "/repo"),
        Mount(f"libera-test-venv-{arch}", "/venv"),
        Mount(f"libera-test-state-{arch}", "/state"),
    ]
    if payload:
        mounts.append(Mount(payload, "/payload", read_only=True))
    if wheels:
        mounts.append(Mount(wheels, "/wheels", read_only=True))
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
    ready = prepare(options.arch or host_arch())
    return {
        "versions": "cat /etc/libera-test-image.txt",
        "shell": "exec /bin/bash",
        "lint": f"{SYNC}\n{LINT}",
        "test": f"{ready}\n{test}",
        "dialog": f"{ready}\n{DIALOG}",
        "gui": f"{ready}\n{GUI}",
        "gui-test": f"{ready}\n{GUI_TEST}",
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
    wheels, payload = choose_payload(options, arch) if needs_payload else (None, None)
    step(f"{options.action}, on Linux ({arch})")
    argv = engine.run_argv(
        Run(
            image,
            ("-c", script_for(options)),
            arch,
            mounts=tuple(mounts_for(arch, wheels, payload)),
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
