#!/bin/sh
# Run this repository's tests on Linux.
#
# Everything about Libera Suite is verified on a Mac. Two containers already build
# things -- build/docker.sh the payload, build/flatpak.sh the Flatpak -- and
# neither runs a test from tests/. This is the third, and it is the only place
# the host, the bridge and the editor are exercised on Linux at all.
#
#   build/test-linux.sh image       build (or rebuild) the test image
#   build/test-linux.sh versions    what that image is pinned to
#   build/test-linux.sh lint        ruff, ty, pyrefly and mypy, on Linux
#   build/test-linux.sh test [...]  the suite, arguments passed to pytest
#   build/test-linux.sh gui         a real GTK window, under Xvfb, screenshotted
#   build/test-linux.sh dialog      the GTK question the host asks, answered
#   build/test-linux.sh shell       poke around inside
#
#   ARCH=amd64   x86_64 instead of this machine's architecture
#   DIST=DIR     payload artifacts to install from (default: the container build's)
#   PAYLOAD=DIR  an unpacked payload to use as-is, when no DIST matches
#                this checkout's PAYLOAD_VERSION
#
# `test` and `gui` cover different halves and neither subsumes the other. The
# suite drives `libera --serve` with headless Chromium, which is the editor and
# the bridge but not the window; `gui` opens the window pywebview actually
# builds on Linux -- GTK 3 and WebKitGTK, a stack that exists nowhere on macOS.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
. "$HERE/common.sh"

case "$(uname -m)" in
arm64 | aarch64) HOST_ARCH=arm64 ;;
*) HOST_ARCH=amd64 ;;
esac
ARCH="${ARCH:-$HOST_ARCH}"
IMAGE="$(local_image "${IMAGE:-libera-test-linux-$ARCH}")"
# Two volumes, because both are expensive and neither belongs in the repository:
# the virtualenv with Linux wheels, and the installed payload.
VENV="${VENV:-libera-test-venv-$ARCH}"
STATE="${STATE:-libera-test-state-$ARCH}"

PAYLOAD_VERSION="$(sed -n 's/^version *= *//p' "$HERE/payload.version" | tr -d '"')"

# Where the artifacts are, asked of docker.sh rather than recomputed here.
# $OUT/dist is where a *native* `payload-dist` writes; a container build leaves
# them under $BUILD_ROOT/linux-$ARCH, and only docker.sh knows that layout --
# it moves with BUILD_DIR and with the architecture. This default said
# "the container build's" and named the native path, so on a Linux box, where
# every artifact comes out of the container, `make lint-linux` and
# `make test-linux` both refused to run against a payload that was right there.
# release.sh has always asked the same question, the same way.
if [ -z "${DIST:-}" ]; then
    DIST="$(ARCH="$ARCH" sh "$HERE/docker.sh" export 2>/dev/null || :)"
    # Nothing built in a container: fall back to the native dist, and let the
    # check below say which directory it wanted.
    [ -n "$DIST" ] || DIST="$OUT/dist/$PAYLOAD_VERSION"
fi

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }

# And when there are no artifacts at all, an installed payload of any version,
# the way tests/conftest.py does it for the suite. Without this the only way in
# was to know the path and type `PAYLOAD=$HOME/.local/share/...` -- which is the
# same friction, one directory along, as the `export LIBERA_PAYLOAD` that
# conftest.py now removes. `resolve()` refuses these because it wants
# PAYLOAD_VERSION exactly; a window check does not care which payload drew the
# window, only that one did.
#
# The paths are locate.py's state_dir(), restated here because this script is
# shell and already re-derives PAYLOAD_VERSION from payload.version the same
# way. If those move, they move in two places.
if [ -z "${PAYLOAD:-}" ] && [ ! -d "$DIST" ]; then
    case "$(uname -s)" in
    Darwin) installed="$HOME/Library/Application Support/Libera Suite/payload" ;;
    *)      installed="${XDG_DATA_HOME:-$HOME/.local/share}/libera/payload" ;;
    esac
    if [ -d "$installed" ]; then
        # Newest first, and by number: a plain sort puts 0.10 before 0.9.
        for version in $(ls -1 "$installed" 2>/dev/null | sort -t. -k1,1nr -k2,2nr); do
            # The two files is_complete() would not do without. A fuller
            # check lives in Python and this only has to beat "nothing".
            if [ -x "$installed/$version/bin/x2t" ] && [ -d "$installed/$version/sdkjs" ]; then
                PAYLOAD="$installed/$version"
                say "==> no artifacts in $DIST; using the installed payload $version"
                say "    $PAYLOAD  (PAYLOAD=DIR overrides)"
                break
            fi
        done
    fi
fi

[ $# -gt 0 ] || { sed -n '3,20p' "$0" | sed 's/^#\{1,\} \{0,1\}//'; exit 2; }

build_image() { "$ENGINE" build --platform "linux/$ARCH" -t "$IMAGE" "$HERE/test-linux"; }

case "$1" in
image) build_image; exit $? ;;
esac

"$ENGINE" image inspect "$IMAGE" >/dev/null 2>&1 || { step "building the image first"; build_image; }

run() {
    cmd="$1"
    shift

    set -- --rm --pull=never \
        --platform "linux/$ARCH" \
        -v "$REPO:/repo" \
        -v "$VENV:/venv" \
        -v "$STATE:/state" \
        -e XDG_DATA_HOME=/state \
        -e HOME=/state \
        -w /repo \
        "$@"

    # PAYLOAD=DIR: an already-unpacked payload, instead of installing artifacts
    # from $DIST. LIBERA_PAYLOAD is taken as given and its version is not
    # checked -- deliberately, per payload/locate.py -- which is the only way in
    # when the checkout's PAYLOAD_VERSION has moved ahead of every payload on
    # the machine. Here that is 0.3 against a 0.1 and a 0.2, so
    # `--payload-install --from /dist` refuses with "manifest is for payload
    # 0.2, this libera needs 0.3" and no window check can run at all.
    if [ -n "${PAYLOAD:-}" ]; then
        set -- "$@" -v "$PAYLOAD:/payload:ro" -e LIBERA_PAYLOAD=/payload
    fi

    # And the artifacts, only when they are there. Every caller used to pass
    # this mount itself, so a $DIST that does not exist -- which is the default
    # now that PAYLOAD_VERSION is 0.3 and no 0.3 dist has been built here --
    # made the engine refuse to start with "statfs .../dist/0.3: no such file
    # or directory", before anything had a chance to say what it wanted.
    if [ -d "$DIST" ]; then
        set -- "$@" -v "${DIST}:/dist:ro"
    fi

    # pytest's cache and __pycache__ would otherwise land in the bind-mounted
    # repository, owned by root on a Linux host and mixed in with the Mac's own.
    set -- "$@" -e PYTHONPYCACHEPREFIX=/tmp/pycache

    if [ -t 0 ] && [ -t 1 ]; then
        set -- -it "$@"
    fi
    if [ -d /sys/fs/selinux ]; then
        set -- --security-opt label=disable "$@"
    fi

    "$ENGINE" run "$@" "$IMAGE" -c "$cmd"
}

# uv sync into /venv, and the payload installed the way a user installs it --
# through the manifest, with every hash checked. Both are volume-cached, so
# this is a no-op on the second run.
#
# Not `make payload-install`: that shells back out to build/docker.sh export,
# which is the other container.
prepare() {
    [ -n "${PAYLOAD:-}" ] || [ -d "$DIST" ] || {
        say "FATAL: no payload artifacts in $DIST" >&2
        say "       build them:  BUILD_DIR=... ARCH=$ARCH sh build/docker.sh all" >&2
        say "       then export: ARCH=$ARCH sh build/docker.sh export" >&2
        say "       or point at a directory with DIST=" >&2
        exit 1
    }
    step "venv and payload"
    # UV_PYTHON=/usr/bin/python3 (in the Dockerfile) and the pyvenv.cfg line
    # together, because neither works alone. PyGObject is not a wheel -- it is the distribution's
    # /usr/lib/python3/dist-packages/gi -- so an environment built on a
    # downloaded interpreter can never reach it whatever else is set, and one
    # built on the system interpreter still cannot until system site-packages
    # are switched on. Without both, gui.is_gtk_available() is False in here
    # and every test that opens a window is testing the wrong machine.
    #
    # This is the same trap a user meets: `pipx install libera` reports no
    # window on a box with every GTK package installed, and `pipx install
    # --system-site-packages libera` reports one. gui.py says so now.
    run "set -e
        uv sync --group dev --quiet
        sed -i 's/^include-system-site-packages = false/include-system-site-packages = true/' \
            /venv/pyvenv.cfg
        uv run --no-sync python -c 'import gi' \
            || { echo 'FATAL: the venv still cannot import gi' >&2; exit 1; }
        # With PAYLOAD=DIR this passes on the mounted payload and installs
        # nothing; with DIST it installs, which is what a user does.
        uv run --no-sync libera --payload-status >/dev/null 2>&1 \
            || uv run --no-sync libera --payload-install --from /dist
        # Playwright's own Chromium, which is not the same browser as the
        # system one. tests/c_e2e/conftest.py starts a raw subprocess and is
        # happy with \$CHROMIUM; the keyboard, slideshow and start-window
        # tests drive Playwright, which refuses to run against anything it did
        # not install -- fifteen tests skipped on Linux for want of it, which
        # reads as coverage the suite does not have.
        #
        # PLAYWRIGHT_BROWSERS_PATH points into the venv volume, so this is a
        # download once and a no-op after.
        uv run --no-sync playwright install chromium >/dev/null 2>&1 \
            || { echo 'FATAL: playwright could not install a browser' >&2; exit 1; }"
}

# The type checkers, on Linux.
#
# `sys.platform` is a fact at check time, so a checker on a Mac prunes every
# non-macOS branch before looking at it. Two real defects lived in those
# branches -- a `Window | None` dereferenced in set_fullscreen and a list with
# no inferrable element type in find_front_window -- and both were invisible here
# and reported on the first Linux run.
#
# The suite's own lesson, applied to lint: a check that never ran elsewhere is
# a check of where it ran.
cmd_lint() {
    prepare
    step "ruff, ty, pyrefly and mypy, on Linux"
    run "set -e
        uv run --no-sync ruff check
        uv run --no-sync ruff format --check
        uv run --no-sync ty check src
        uv run --no-sync pyrefly check src
        uv run --no-sync mypy src"
}

cmd_test() {
    prepare
    step "pytest"
    # -p no:cacheprovider for the same reason as PYTHONPYCACHEPREFIX: nothing
    # this run does should show up in `git status` on the host.
    run "uv run --no-sync pytest -p no:cacheprovider $*"
}

# The three questions the host asks, on the platform where they were answered
# "no" without asking. gui-smoke opens a window; this one opens a dialog.
cmd_dialog() {
    prepare
    step "the GTK question, under Xvfb"
    run "set -e
        xvfb-run -a --server-args='-screen 0 1600x1000x24' \
            uv run --no-sync python build/test-linux/dialog-smoke.py"
}

cmd_gui() {
    prepare
    step "a real window, under Xvfb"
    # The screen is bigger than WINDOW_SIZE because Xvfb has no window
    # manager: nothing constrains or re-places a window, and pywebview centres
    # it, so a 1400-wide window on a 1280-wide screen sat at x=-60 with its
    # menu bar and its left toolbar off the edge. A real desktop's WM clamps to
    # the work area; this had to be given room instead.
    #
    # WEBKIT_DISABLE_COMPOSITING_MODE and LIBGL_ALWAYS_SOFTWARE because Xvfb has
    # no GPU: without them WebKit tries an accelerated path, and what comes back
    # is a window that maps and never paints -- which is exactly the failure
    # gui-smoke.py is looking for, so it would report a real bug that is not one.
    # Two documents, and of different types, because that is the shape a beta
    # tester reported as impossible against the Flatpak -- and because the code
    # that opens the second one is not the code that opens the first.
    # app.py's _open_rest had a wait that waited for nothing; a harness with one
    # document cannot tell. The payload ships a blank of each kind, so the
    # presentation costs a copy.
    run "set -e
        uv run --no-sync python tests/support/make_sample_docx.py /tmp/sample.docx >/dev/null
        root=\$(uv run --no-sync python -c 'from libera.payload import locate; print(locate.resolve().root)')
        cp \"\$root/empty/new.pptx\" /tmp/sample.pptx
        export WEBKIT_DISABLE_COMPOSITING_MODE=1 LIBGL_ALWAYS_SOFTWARE=1
        xvfb-run -a --server-args='-screen 0 1600x1000x24' \
            uv run --no-sync python build/test-linux/gui-smoke.py \
                /tmp/sample.docx /tmp/sample.pptx /repo/build/out/gui-linux.png"
    say "    screenshot: build/out/gui-linux.png"
}

case "$1" in
versions) run "cat /etc/libera-test-image.txt" ;;
lint)     cmd_lint ;;
test)     shift; cmd_test "$@" ;;
gui)      cmd_gui ;;
dialog)   cmd_dialog ;;
shell)    run "exec /bin/bash" ;;
*)        say "unknown command: $1" >&2; exit 2 ;;
esac
