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
# anyone.
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

echo "==> icon"
"$PYTHON" "$HERE/macos-icon.py" "$APP/Contents/Resources/Libera.icns"
rm -rf "$APP/Contents/Resources/Libera.iconset"

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

echo "==> launcher"
# Compiled, not a shell script: the bundle's executable has to be the process
# that stays, or the open-document Apple Event is delivered to a bundle that
# exec() has already replaced. See build/macos/launcher.m.
command -v clang >/dev/null || { echo "FATAL: clang not found (Xcode command line tools)" >&2; exit 1; }
# The interpreter runs inside the launcher, so the launcher links the base
# interpreter's library: the framework's own binary for a framework build
# (Homebrew's, python.org's), libpythonX.Y.dylib otherwise. Asked of the
# interpreter, not of python3-config, whose -L names the prefix Homebrew was
# configured with -- /opt/homebrew -- which on this machine is another Homebrew
# with another build of 3.12.
eval "$("$PYTHON" - <<'PY'
import os, sys, sysconfig
v = sysconfig.get_config_var
if v("PYTHONFRAMEWORK"):
    lib = os.path.join(sys.base_prefix, v("PYTHONFRAMEWORK"))
else:
    lib = os.path.join(v("LIBDIR"), v("LDLIBRARY"))
print(f"PY_INCLUDE='{sysconfig.get_paths()['include']}'")
print(f"PY_LIB='{os.path.realpath(lib)}'")
PY
)"
[ -f "$PY_LIB" ] || { echo "FATAL: no Python library at $PY_LIB to embed" >&2; exit 1; }
# What the launcher runs as, and the library it loads. Thin: absolute paths
# into this machine. Standalone: paths inside the bundle, the interpreter's
# relative to Contents (launcher.m resolves it) and the library's to the
# launcher itself.
if [ "$STANDALONE" = 1 ]; then
    LAUNCH_AS="Resources/python/bin/python3"
    LOAD_AS="@executable_path/../Resources/python/lib/$(basename "$PY_LIB")"
else
    LAUNCH_AS="$PYTHON"
    LOAD_AS="$PY_LIB"
fi
clang -O2 -Wall -Werror -framework Cocoa -I"$PY_INCLUDE" "$PY_LIB" \
    -DLIBERA_PYTHON="\"$LAUNCH_AS\"" \
    -o "$APP/Contents/MacOS/Libera" "$HERE/launcher.m"
# The library records its install name, not the path it was linked from, and
# Homebrew's names the configured prefix too. Load the file that was linked,
# or its copy in the bundle.
RECORDED="$(otool -L "$APP/Contents/MacOS/Libera" | awk 'NR > 1 && /[Pp]ython/ { print $1; exit }')"
if [ "$RECORDED" != "$LOAD_AS" ]; then
    install_name_tool -change "$RECORDED" "$LOAD_AS" "$APP/Contents/MacOS/Libera" 2>/dev/null
    # arm64 runs nothing unsigned, and changing a load command voids the
    # linker's ad-hoc signature.
    codesign --force --sign - "$APP/Contents/MacOS/Libera"
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

echo "==> Info.plist (minimum macOS $MIN_MACOS)"
# The heredoc below is unquoted, because $VERSION and $MIN_MACOS have to expand.
# That means backticks inside it are command substitution, including inside an
# XML comment: two identifiers written in markdown habit as `org.libre...` were
# run as commands, printed "command not found", and were deleted from every
# Info.plist this script has ever written. Use double quotes in the comments.
# CFBundleDocumentTypes is what puts Libera Suite in Finder's "Open With" and lets a
# double-click reach us. LSHandlerRank Alternate: we claim to handle these, not
# to own them -- taking .docx away from whatever the user already uses would be
# rude for something this early.
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Libera</string>
  <key>CFBundleDisplayName</key><string>Libera Suite</string>
  <key>CFBundleIdentifier</key><string>eu.liberasuite.Libera</string>
  <key>CFBundleExecutable</key><string>Libera</string>
  <key>CFBundleIconFile</key><string>Libera.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <!-- Without NSPrincipalClass, AppKit never finishes launching the
       application and the open-document event is never delivered. -->
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>LSMinimumSystemVersion</key><string>$MIN_MACOS</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSHumanReadableCopyright</key>
  <string>Copyright © 2026 Abilian SAS. Includes modified AGPL v3 components from Euro-Office, a fork of ONLYOFFICE by Ascensio System SIA.</string>
  <!-- The macOS half of src/libera/launcher.desktop, and the two are meant to
       stay the same set: one entry per format host/apps.py routes to an
       editor and the system has a name for. This declared Words alone, so
       macOS never offered to open a .xlsx or a .pptx that Libera Suite opens
       perfectly well -- the Linux entry had claimed all three since it was
       written. Measured both ways against
       NSWorkspace.URLsForApplicationsToOpenURL_: before, .docx yes and .xlsx
       and .pptx no; after, all three.

       Every identifier here was read out of the system rather than
       remembered, by asking UTType.typeWithFilenameExtension_ for each
       extension in apps.py. Two of its answers are deliberately not used.
       "org.libreoffice.visio-document" for .vsdx comes from LibreOffice being
       installed on the machine that asked, not from macOS, so claiming it
       would be claiming another application's type; Visio is therefore the one
       format the .desktop declares and this does not. And
       "com.microsoft.word.doc" is left out with it: .doc opens and cannot be
       saved, so offering to edit one leads somewhere Save does not go.

       One dict per editor rather than per format, because Open With shows
       CFBundleTypeName and "Spreadsheet" is more use there than four entries
       each naming one extension. -->
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeName</key><string>Word Document</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array>
        <string>org.openxmlformats.wordprocessingml.document</string>
        <string>org.oasis-open.opendocument.text</string>
        <string>public.rtf</string>
        <string>public.plain-text</string>
      </array>
    </dict>
    <dict>
      <key>CFBundleTypeName</key><string>Spreadsheet</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array>
        <string>org.openxmlformats.spreadsheetml.sheet</string>
        <string>org.oasis-open.opendocument.spreadsheet</string>
        <string>public.comma-separated-values-text</string>
        <string>public.tab-separated-values-text</string>
      </array>
    </dict>
    <dict>
      <key>CFBundleTypeName</key><string>Presentation</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array>
        <string>org.openxmlformats.presentationml.presentation</string>
        <string>org.oasis-open.opendocument.presentation</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
PLIST

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
    # launcher.py, writes the Linux desktop entry.
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
