#!/bin/sh
# OpenSSL from vcpkg, for Windows.
#
#   sh build/vcpkg.sh openssl     print the prefix, installing it if needed
#
# **Why this exists.** OpenSSL 1.1.1w does not build here. nmake reports
# `U1073: don't know how to make '"apps\apps.c"'` for a file that is present,
# complete and named in a rule byte-identical to the one three lines above it
# that works. Ten hypotheses died against that, including the whole makefile,
# read in full. notes/14-windows.md has the list so nobody repeats it.
#
# So this stops explaining it and sources OpenSSL from somewhere that works.
# Patch 0024 makes core take `EO_CORE_OPENSSL_DIR`; a vcpkg triplet directory
# holds include/ and lib/ exactly where core already looks, so there is no
# translation layer here and no cmake glue, only a path.
#
# **Classic mode, deliberately.** Manifest mode would read core's vcpkg.json,
# which lists hunspell, and vcpkg would build a second one beside the one
# build_3rdparty.py already built. Nothing else in the build changes: no
# toolchain file, no CMAKE_PREFIX_PATH, no effect on any other component.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"

# Static CRT, because the rest of the build is /MT. Mixing runtimes links and
# then fails at run time on a freed allocation, which is a worse day than a
# link error. `x64-windows` is the dynamic default and is the wrong one here.
TRIPLET="${VCPKG_TRIPLET:-x64-windows-static}"

# GitHub's windows images ship vcpkg and set VCPKG_INSTALLATION_ROOT. A desktop
# usually has VCPKG_ROOT. Failing both, clone it beside the build tree.
vcpkg_root() {
    for d in "${VCPKG_ROOT:-}" "${VCPKG_INSTALLATION_ROOT:-}" "$BUILD_ROOT/vcpkg"; do
        [ -n "$d" ] || continue
        [ -x "$d/vcpkg.exe" ] || [ -x "$d/vcpkg" ] || continue
        echo "$d"
        return 0
    done

    echo "==> no vcpkg found; cloning into $BUILD_ROOT/vcpkg" >&2
    git clone --depth 1 https://github.com/microsoft/vcpkg.git "$BUILD_ROOT/vcpkg" >&2
    ( cd "$BUILD_ROOT/vcpkg" && ./bootstrap-vcpkg.bat -disableMetrics >&2 )
    [ -x "$BUILD_ROOT/vcpkg/vcpkg.exe" ] || {
        echo "FATAL: bootstrap-vcpkg.bat left no vcpkg.exe" >&2
        exit 1
    }
    echo "$BUILD_ROOT/vcpkg"
}

cmd_openssl() {
    root="$(vcpkg_root)"
    exe="$root/vcpkg.exe"
    [ -x "$exe" ] || exe="$root/vcpkg"
    prefix="$root/installed/$TRIPLET"

    # Already there is the common case, and vcpkg takes twenty seconds to work
    # that out for itself.
    if ! [ -f "$prefix/lib/libssl.lib" ]; then
        echo "==> vcpkg install openssl:$TRIPLET (from $root)" >&2
        # From the vcpkg root: run it anywhere near core's vcpkg.json and it
        # switches to manifest mode and installs that file's list instead.
        ( cd "$root" && "$exe" install "openssl:$TRIPLET" --disable-metrics >&2 )
    fi

    # Asserted on the two files core will link, not on vcpkg's exit code. A
    # port can install headers and no import library, and the next thing to
    # notice would be a link error in doctrenderer twenty minutes later.
    for lib in libssl libcrypto; do
        [ -f "$prefix/lib/$lib.lib" ] || {
            echo "FATAL: vcpkg installed no $lib.lib in $prefix/lib" >&2
            ls -1 "$prefix/lib" 2>&1 | sed 's/^/    /' >&2
            exit 1
        }
    done

    # Which OpenSSL this actually is. vcpkg tracks 3.x while core's own build
    # pins 1.1.1w, and that is a real difference rather than a detail: 3.0
    # keeps most of the 1.1.1 API but deprecates a good deal of it. Printing
    # the version means a later compile error has somewhere to start.
    v="$(sed -n 's/.*OPENSSL_VERSION_TEXT *"\(OpenSSL [^"]*\)".*/\1/p' \
        "$prefix/include/openssl/opensslv.h" 2>/dev/null | head -1)"
    echo "==> ${v:-OpenSSL, version unread} at $prefix" >&2

    echo "$prefix"
}

case "${1:-}" in
openssl) cmd_openssl ;;
*)
    echo "usage: $0 openssl" >&2
    exit 2
    ;;
esac
