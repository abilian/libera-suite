#!/bin/sh
# Rebuild what every Libera.app is made of, into the package:
#
#   src/libera/macos/Libera        the executable, from launcher.m
#   src/libera/macos/Libera.icns   the icon, from src/libera/icon.svg
#
# Both are committed, so that `libera --launcher-install` needs no compiler on
# the user's machine; run this after changing either source, and commit what
# it writes. Universal, and for macOS 11 on, so the one binary serves every Mac
# the package can be installed on, whatever the payload itself supports.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="$REPO/src/libera/macos"
PYTHON="${PYTHON:-$REPO/.venv/bin/python3}"
mkdir -p "$OUT"

command -v clang >/dev/null || { echo "FATAL: clang not found (Xcode command line tools)" >&2; exit 1; }
echo "==> launcher"
clang -O2 -Wall -Werror -arch arm64 -arch x86_64 -mmacosx-version-min=11.0 \
    -framework Cocoa -o "$OUT/Libera" "$HERE/launcher.m"
echo "==> icon"
"$PYTHON" "$HERE/macos-icon.py" "$OUT/Libera.icns"
rm -rf "$OUT/Libera.iconset"
