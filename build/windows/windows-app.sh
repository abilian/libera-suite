#!/bin/sh
# Libera Suite for Windows: the frozen application and its installer.
#
#   sh build/windows/windows-app.sh          icon, freeze, installer
#
# Freezes the environment `uv run` syncs, which holds the components that
# `uv sync` builds (an hour the first time, minutes after a `payload build`),
# and needs build/windows/windows-setup.ps1's tools, Inno Setup among them.
# With BUNDLE_WHEELS, a folder holding libera, libera-core and libera-web as
# wheels, it freezes a new environment of those instead, under the version
# they carry: what a release does, which builds them once and labels them.
# Writes:
#
#   $OUT/windows/Libera Suite/                the frozen application
#   $OUT/windows/Libera-Suite-Setup-<v>.exe   what a user downloads
#
# The mirror of build/macos/macos-app.sh, with one difference that matters: the
# macOS .app runs the interpreter it was built beside, while this carries its
# own, because a Windows user has no Python and should not need one.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
# build/, one up: the scripts here and their inputs live beside each other.
BUILD="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$BUILD/.." && pwd)"
. "$BUILD/engine/common.sh"

[ -n "$EXE" ] || { echo "FATAL: this builds the Windows application; run it on Windows" >&2; exit 1; }

WORK="$OUT/windows"
VENV=""
if [ -n "${BUNDLE_WHEELS:-}" ]; then
    WHEELS_DIR="$(cygpath -u "$BUNDLE_WHEELS")"
    set -- "$WHEELS_DIR"/libera-*.whl
    [ $# = 1 ] && [ -f "$1" ] || { echo "FATAL: not one libera wheel in $WHEELS_DIR: $*" >&2; exit 1; }
    LIBERA_WHEEL="$1"
    APP_VERSION="$(basename "$LIBERA_WHEEL" | cut -d- -f2)"
    PAYLOAD_VERSION="$APP_VERSION"
    VENV="$WORK/venv"
else
    PAYLOAD_VERSION="$(payload_version "$REPO")"
    APP_VERSION="$(sed -n 's/^version *= *"\(.*\)"/\1/p' "$REPO/pyproject.toml" | head -1)"
fi
# The numbers alone, for what Windows reads as a version: 0.4.0 of 0.4.0rc1.
# Inno Setup refuses anything else in VersionInfoVersion, and the resource
# below has four numeric fields.
APP_NUMBERS="$(echo "$APP_VERSION" | sed 's/[^0-9.].*//')"
# PyInstaller, pinned: its bootloader is what users run, so a new one is a
# change to review rather than something a rebuild picks up.
PYINSTALLER="pyinstaller==6.16.0"

ISCC=""
for c in "/c/Program Files (x86)/Inno Setup 6/ISCC.exe" "$LOCALAPPDATA/Programs/Inno Setup 6/ISCC.exe"; do
    c="$(cygpath -u "$c" 2>/dev/null || echo "$c")"
    [ -x "$c" ] && { ISCC="$c"; break; }
done
[ -n "$ISCC" ] || { echo "FATAL: no Inno Setup; run build/windows/windows-setup.ps1" >&2; exit 1; }

EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
[ -x "$EDGE" ] || { echo "FATAL: no Edge at $EDGE, which draws the icon" >&2; exit 1; }

mkdir -p "$WORK"

# --- the icon -----------------------------------------------------------------
# src/libera/icon.svg, rasterised by Edge -- the engine WebView2 draws the
# application with -- at 1024 and scaled down, because headless Edge will not
# make a window smaller than about 500 pixels and a 256 render comes out
# cropped. Transparent, so the rounded corners stay round on any background.
echo "==> icon"
ICONWORK="$WORK/icon"
rm -rf "$ICONWORK" && mkdir -p "$ICONWORK"
cp "$REPO/src/libera/icon.svg" "$ICONWORK/"
printf '%s' '<!doctype html><html><body style="margin:0;background:transparent"><img src="icon.svg" style="display:block;width:100vw;height:100vh"></body></html>' \
    > "$ICONWORK/icon.html"
"$EDGE" --headless=new --disable-gpu --no-first-run --hide-scrollbars \
    --default-background-color=00000000 --window-size=1024,1024 \
    --screenshot="$(cygpath -w "$ICONWORK/icon1024.png")" \
    "file:///$(cygpath -m "$ICONWORK/icon.html")" >/dev/null 2>&1 || true
ICON="$WORK/Libera.ico"
uv run --no-project --with pillow python - "$(cygpath -m "$ICONWORK/icon1024.png")" "$(cygpath -m "$ICON")" <<'PY'
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGBA")
# Content, not the exit code: a render that failed is a blank or opaque square.
corner, middle = im.getpixel((0, 0)), im.getpixel((512, 512))
assert im.size == (1024, 1024), f"icon rendered at {im.size}"
assert corner[3] == 0, f"icon corner is not transparent: {corner}"
assert middle[3] == 255 and middle[:3] != (255, 255, 255), f"icon has no tile: {middle}"
im.save(sys.argv[2], sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
print(f"    {sys.argv[2]}")
PY

# --- version resource -----------------------------------------------------------
# What Explorer's Properties > Details and the Task Manager show.
VERSION_FILE="$WORK/version.txt"
v4="$(echo "$APP_NUMBERS" | awk -F. '{printf "%d, %d, %d, 0", $1, $2, $3}')"
cat > "$VERSION_FILE" <<VER
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($v4), prodvers=($v4)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Abilian'),
      StringStruct('FileDescription', 'Libera Suite'),
      StringStruct('FileVersion', '$APP_VERSION'),
      StringStruct('ProductName', 'Libera Suite'),
      StringStruct('ProductVersion', '$APP_VERSION'),
      StringStruct('LegalCopyright', 'Abilian and the Libera Suite contributors')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
VER

# --- freeze -----------------------------------------------------------------------
# The Python that freezes, and whose libera it finds: this checkout's, synced
# by uv, or the new environment of the given wheels, their dependencies from
# PyPI, libera's own from that folder alone (nothing else has its version).
SRC="$REPO/src"
if [ -n "$VENV" ]; then
    echo "==> the environment, from $WHEELS_DIR"
    rm -rf "$VENV"
    uv venv -q -p 3.12 "$VENV"
    uv pip install -q --python "$VENV" --find-links "$WHEELS_DIR" "$LIBERA_WHEEL" "$PYINSTALLER"
    SRC=""
    # lb runs this with PYTHONPATH naming the checkout's src/, and a libera
    # found there first is the checkout's, at its own version, not the
    # wheel's: the frozen tree said payload 0.7.4 to wheels of 0.7.4+9d5f75f.
    unset PYTHONPATH
fi
py() {
    if [ -n "$VENV" ]; then "$VENV/Scripts/python.exe" "$@"
    else uv run --with "$PYINSTALLER" python "$@"
    fi
}

echo "==> freeze ($PYINSTALLER, libera $APP_VERSION, payload $PAYLOAD_VERSION)"
rm -rf "$WORK/freeze" "$WORK/Libera Suite"
(
    cd "$REPO"
    LIBERA_ICON="$(cygpath -w "$ICON")" \
    LIBERA_SRC="${SRC:+$(cygpath -w "$SRC")}" \
    LIBERA_VERSION_FILE="$(cygpath -w "$VERSION_FILE")" \
        py -m PyInstaller --noconfirm --log-level WARN \
            --distpath "$(cygpath -w "$WORK")" \
            --workpath "$(cygpath -w "$WORK/freeze")" \
            "$(cygpath -w "$HERE/libera.spec")"
)
APP="$WORK/Libera Suite"
for f in Libera.exe libera-cli.exe; do
    [ -f "$APP/$f" ] || { echo "FATAL: the frozen tree has no $f" >&2; exit 1; }
done

# The frozen program, asked what it is: an import that the analysis missed
# fails here, at a prompt, rather than on a user's double-click.
echo "==> the frozen application"
"$APP/libera-cli.exe" -V
# --payload-status reaches the payload code, which -V does not, and says where
# the payload was found: the components frozen with it, or the bundle is
# broken. A missed module is a traceback, and its exit status alone cannot
# tell it from a payload not found.
said="$("$APP/libera-cli.exe" --payload-status 2>&1)" || :
if ! printf '%s\n' "$said" | grep -q '^found via: *components$'; then
    echo "FATAL: the frozen application did not find its components:" >&2
    printf '%s\n' "$said" | sed 's/^/    /' >&2
    exit 1
fi
printf '%s\n' "$said" | head -n 1 | sed 's/^/    /'
du -sh "$APP" | sed 's/^/    /'

# --- installer ----------------------------------------------------------------------
echo "==> associations, from src/libera/host/apps.py"
ASSOC="$WORK/associations.iss"
(cd "$REPO" && py "$(cygpath -w "$HERE/associations.py")" "$(cygpath -w "$ASSOC")")
echo "    $(grep -c 'OpenWithProgids' "$ASSOC") extensions"

echo "==> installer (Inno Setup)"
MSYS2_ARG_CONV_EXCL='*' "$ISCC" /Q \
    "/DAppVersion=$APP_VERSION" \
    "/DAppNumbers=$APP_NUMBERS" \
    "/DAppDir=$(cygpath -w "$APP")" \
    "/DIconFile=$(cygpath -w "$ICON")" \
    "/DAssociations=$(cygpath -w "$ASSOC")" \
    "/DOutputDir=$(cygpath -w "$WORK")" \
    "$(cygpath -w "$HERE/libera.iss")"
SETUP="$WORK/Libera-Suite-Setup-$APP_VERSION.exe"
[ -s "$SETUP" ] || { echo "FATAL: Inno Setup wrote no $SETUP" >&2; exit 1; }
echo
echo "installer: $SETUP ($(du -h "$SETUP" | cut -f1))"

# Beside the Flatpak bundles, which is where `lb release publish` uploads
# from, with its SHA-256 in sha256sum's format: install.ps1 checks the
# download against it, and anyone can by hand with Get-FileHash.
BUNDLES="$REPO/build/out/bundles"
mkdir -p "$BUNDLES"
cp "$SETUP" "$BUNDLES/"
( cd "$BUNDLES" && sha256sum "$(basename "$SETUP")" > "$(basename "$SETUP").sha256" )
echo "bundle:    $BUNDLES/$(basename "$SETUP") (+ .sha256)"
