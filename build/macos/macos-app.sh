#!/bin/sh
# Assemble Libera.app.
#
#   build/macos/macos-app.sh [DEST]        default: build/out/Libera.app
#
#   STANDALONE=1 build/macos/macos-app.sh  everything inside the bundle
#
# By default a thin bundle: the launcher runs the libera package from the
# interpreter it was built against, this checkout's .venv. It is what makes
# double-click, "Open With" and a Dock icon work here; it cannot be handed to
# anyone. `libera --launcher-install` writes the same into ~/Applications, for
# whatever interpreter runs it, and is what an installed copy should use.
#
# STANDALONE=1 puts everything inside: uv's relocatable CPython at
# Contents/Resources/python, the wheel built from this tree installed into it,
# and the payload at Contents/Resources/python/share/libera/payload, where
# locate.find_bundled_dir finds it. The payload comes from PAYLOAD_FROM, by
# default this machine's built artifacts if it has them, else the public
# origin, and every hash is checked on the way in. Not signed or notarised yet.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
# build/, one up: the scripts here and their inputs live beside each other.
BUILD="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$BUILD/.." && pwd)"
APP="${1:-$BUILD/out/Libera.app}"

# The interpreter to launch with, resolved now rather than at run time: the
# bundle has no PATH to speak of when Finder starts it.
PYTHON="${PYTHON:-$REPO/.venv/bin/python3}"
STANDALONE="${STANDALONE:-0}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
[ -x "$PYTHON" ] || { echo "FATAL: no interpreter at $PYTHON (set PYTHON=)" >&2; exit 1; }
"$PYTHON" -c "import libera" 2>/dev/null || {
    echo "FATAL: $PYTHON cannot import libera -- run 'uv sync' first" >&2; exit 1; }

VERSION="$(sed -n 's/^version *= *"\(.*\)"/\1/p' "$REPO/pyproject.toml" | head -1)"
: "${VERSION:=0.0.0}"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

if [ "$STANDALONE" = 1 ]; then
    echo "==> interpreter: uv's CPython $PYTHON_VERSION"
    # Outside the project, or uv answers with the .venv.
    (cd /tmp && env -u VIRTUAL_ENV uv python install "$PYTHON_VERSION" >/dev/null)
    FOUND="$(cd /tmp && env -u VIRTUAL_ENV uv python find --managed-python --no-project "$PYTHON_VERSION")"
    BASE="$(cd "$(dirname "$FOUND")/.." && pwd -P)"
    HOME_IN_APP="$APP/Contents/Resources/python"
    cp -R "$BASE" "$HOME_IN_APP"
    # uv's interpreters refuse installs into themselves (PEP 668). This one is
    # ours now.
    find "$HOME_IN_APP/lib" -name EXTERNALLY-MANAGED -delete

    echo "==> libera, from this tree"
    WHEELS="$(mktemp -d)"
    (cd "$REPO" && uv build --wheel --out-dir "$WHEELS" >/dev/null)
    # Compiled now: a signed bundle cannot be written into, so nothing may be
    # left for the interpreter to compile and cache at run time.
    uv pip install --quiet --python "$HOME_IN_APP/bin/python3" --break-system-packages \
        --compile-bytecode "$WHEELS"/libera-*.whl
    rm -rf "$WHEELS"

    . "$BUILD/engine/common.sh"
    PAYLOAD_VERSION="$(payload_version "$REPO")"
    if [ -z "${PAYLOAD_FROM:-}" ] && [ -f "$OUT/dist/$PAYLOAD_VERSION/manifest.json" ]; then
        PAYLOAD_FROM="$OUT/dist/$PAYLOAD_VERSION"
    fi
    echo "==> payload $PAYLOAD_VERSION, from ${PAYLOAD_FROM:-the public origin}"
    PAYLOAD_FROM="${PAYLOAD_FROM:-}" "$HOME_IN_APP/bin/python3" - "$HOME_IN_APP/share/libera/payload" <<'PY'
import os, sys
from pathlib import Path
from libera.payload import installer
source = os.environ["PAYLOAD_FROM"] or None
installer.install(source=Path(source) if source and "://" not in source else source,
                  dest=Path(sys.argv[1]), say=lambda *_: None)
PY
    PYTHON="$HOME_IN_APP/bin/python3"
fi

# The launcher loads the library the plist names, so the bundle is only
# written, never linked: the executable and the icon come prebuilt from the
# package (build/macos/launcher.sh), and the plist from the same code as
# `libera --launcher-install` (src/libera/launcher/macos.py). Thin: absolute
# paths into this machine. Standalone: paths inside the bundle, relative to
# Contents.
LIBRARY="$("$PYTHON" -c 'from libera.launcher import macos; print(macos.find_python_library())')"
[ -f "$LIBRARY" ] || { echo "FATAL: no Python library at $LIBRARY to load" >&2; exit 1; }
if [ "$STANDALONE" = 1 ]; then
    LAUNCH_AS="Resources/python/bin/python3"
    LOAD_AS="Resources/python/lib/$(basename "$LIBRARY")"
else
    LAUNCH_AS="$PYTHON"
    LOAD_AS="$LIBRARY"
fi

# LSMinimumSystemVersion, read off the binary rather than asserted beside it.
#
# It said 11.0 for as long as this script has existed, and the shipped x2t
# reports `minos 14.0` -- built against an Xcode SDK with no deployment target,
# so it takes the SDK's. A user on Big Sur, Monterey or Ventura therefore got a
# bundle that launched and a converter that could not load: the promise in the
# metadata, the refusal at the first save.
#
# Asking the artifact means the two cannot drift apart again. Put a deployment
# target on the core build and this follows it down without being told.
X2T="$("$PYTHON" -c 'from libera import payload; print(payload.resolve().x2t)' 2>/dev/null || true)"
MIN_MACOS=""
if [ -n "$X2T" ] && [ -x "$X2T" ]; then
    MIN_MACOS="$(otool -l "$X2T" |
        awk '/LC_BUILD_VERSION/ { found = 1 } found && $1 == "minos" { print $2; exit }')"
fi
# Nothing to ask, so the last measured value. The branch above corrects it the
# moment a payload is present, which is every case that ships.
: "${MIN_MACOS:=14.0}"

echo "==> bundle (minimum macOS $MIN_MACOS)"
"$PYTHON" - "$APP" "$LAUNCH_AS" "$LOAD_AS" "$MIN_MACOS" <<'PY'
import sys
from pathlib import Path
from libera.launcher import macos
app, python, library, min_macos = sys.argv[1:]
macos.write_bundle(Path(app), python=python, library=library, min_macos=min_macos)
PY

if [ "$STANDALONE" = 1 ]; then
    # Last, because everything above still runs bin/python3 or reads include/.
    echo "==> bytecode, then what the bundle does not run"
    # All of it, compiled now: the launcher writes no bytecode into the bundle,
    # and only about half of uv's interpreter came compiled (299 of 686
    # modules), so the rest would have been compiled again at every start.
    "$HOME_IN_APP/bin/python3" -m compileall -q -j 0 "$HOME_IN_APP/lib" >/dev/null
    L="$HOME_IN_APP/lib/python$PYTHON_VERSION"
    # The interpreter runs inside the launcher, so its own executable (a
    # second, static copy, 17 MB) and the headers go. Tk, IDLE, pip and
    # ensurepip have no caller here, and PyObjCTest is pyobjc's test suite
    # (16 MB). No sys.executable is ever run on macOS: the one use, in
    # launcher/desktop.py, writes the Linux desktop entry.
    rm -rf "$HOME_IN_APP/bin" "$HOME_IN_APP/include" "$HOME_IN_APP/lib/pkgconfig" \
        "$HOME_IN_APP"/lib/libtcl* "$HOME_IN_APP"/lib/tcl* "$HOME_IN_APP"/lib/tk* \
        "$HOME_IN_APP"/lib/itcl* "$HOME_IN_APP"/lib/thread* \
        "$L/tkinter" "$L/idlelib" "$L/turtledemo" "$L/turtle.py" "$L/ensurepip" \
        "$L/lib2to3" "$L"/lib-dynload/_tkinter.* \
        "$L/site-packages/PyObjCTest" "$L/site-packages/pip" "$L"/site-packages/pip-*.dist-info
    # The compiled copies of what just went.
    find "$HOME_IN_APP" -name "turtle.*.pyc" -delete
    echo "    $(du -sh "$HOME_IN_APP" | cut -f1) for Python and the payload"
fi

# Finder caches bundle metadata aggressively; without this the document types
# are not noticed until logout.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "$APP" 2>/dev/null || true

echo
echo "app: $APP"
echo "  open it:            open '$APP'"
echo "  open a document:    open -a '$APP' FILE.docx"
