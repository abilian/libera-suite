#!/bin/sh
# Can doctrenderer use macOS's JavaScriptCore instead of building V8?
#
#   make doctrenderer-jsc         build doctrenderer against JavaScriptCore
#   make doctrenderer-jsc-check   convert a document with it, and with V8, and compare
#
# **Exploratory.** Nothing shipped uses this yet; it answers one question,
# which is whether the Mac build needs V8 at all.
#
# It might not. upstream abstracts the JS engine behind js_internal/js_base.h
# and carries two implementations: js_internal/v8 and js_internal/jsc. The
# second is Objective-C++ against Apple's JavaScriptCore framework, and qmake
# turns it on for macOS by default (`core_mac { !use_v8: CONFIG +=
# use_javascript_core }`). The CMake port we build with defaults it *off*, so
# we build V8 on the Mac too: half an hour, and five of the 21 core patches.
#
# What this cannot answer is Linux, where jsc_base.mm does not apply: it is
# ObjC++ and links a framework. WebKitGTK ships a JavaScriptCore with a C API,
# but that is a third implementation of js_base.h rather than a port of this
# one.
#
# The scratch build reuses the third-party tree the ordinary build made --
# EO_CORE_3RD_PARTY_*_DIR are cache variables -- so build_3rdparty.py finds
# every ok_marker and skips, and configuring takes seconds rather than
# rebuilding V8, ICU and boost.
#
# `check` swaps one file: x2t loads @rpath/libdoctrenderer.dylib dynamically
# and both builds carry the same install name and rpaths, so no relink is
# needed. It restores the original on the way out however it exits, because
# leaving a swapped library in a build tree is a trap for whoever builds next.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"

[ "$(uname -s)" = "Darwin" ] || {
    echo "FATAL: JavaScriptCore here means Apple's framework, so this is macOS only." >&2
    echo "       On Linux the equivalent is a new backend against WebKitGTK's C API." >&2
    exit 1
}

JSC_DIR="$OUT/core-jsc"
JSC_LIB="$JSC_DIR/bin/libdoctrenderer.dylib"
LIVE_LIB="$OUT/core/bin/libdoctrenderer.dylib"

cmd_build() {
    [ -d "$OUT/core/third_party/install" ] || {
        echo "FATAL: no third-party tree at $OUT/core/third_party/install." >&2
        echo "       Run the ordinary build first: make payload-configure" >&2
        exit 1
    }
    mkdir -p "$JSC_DIR"
    echo "==> configure, reusing the third-party tree"
    (
        cd "$JSC_DIR"
        cmake -G Ninja \
            -DCMAKE_BUILD_TYPE=Release \
            -DUSE_JAVASCRIPT_CORE=1 \
            -DEO_CORE_OUTPUT_DIR="$JSC_DIR/bin" \
            -DEO_CORE_TOOLS_DIR="$JSC_DIR/tools" \
            -DEO_CORE_3RD_PARTY_WORK_DIR="$OUT/core/third_party/work" \
            -DEO_CORE_3RD_PARTY_INSTALL_DIR="$OUT/core/third_party/install" \
            "$SRC/core" >"$JSC_DIR/configure.log" 2>&1
    ) || { tail -20 "$JSC_DIR/configure.log" >&2; exit 1; }

    echo "==> ninja doctrenderer"
    (cd "$JSC_DIR" && ninja doctrenderer) >"$JSC_DIR/build.log" 2>&1 ||
        { tail -30 "$JSC_DIR/build.log" >&2; exit 1; }

    # Linking is a weaker statement than it looks, and this is the one that
    # says which engine is actually in there.
    otool -L "$JSC_LIB" | grep -q JavaScriptCore ||
        { echo "FATAL: $JSC_LIB does not link JavaScriptCore" >&2; exit 1; }

    echo "    $JSC_LIB"
    echo "    links $(otool -L "$JSC_LIB" | sed -n 's/.*\(JavaScriptCore.framework.*\)/\1/p' | head -1)"
    echo "    next: make doctrenderer-jsc-check"
}

# The line smoke.sh prints about the PDF it made: pages, embedded fonts, text
# operators. Comparing those is the point -- "it did not crash" would pass on a
# blank page.
pdf_line() { grep -E "page\(s\)" "$1" | tail -1 | sed 's/^ *//'; }

cmd_check() {
    [ -f "$JSC_LIB" ] || {
        echo "FATAL: no JavaScriptCore build yet. Run: make doctrenderer-jsc" >&2
        exit 1
    }
    [ -f "$LIVE_LIB" ] || {
        echo "FATAL: no ordinary build at $LIVE_LIB -- run make payload-core" >&2
        exit 1
    }

    keep="$(mktemp -d)"
    cp "$LIVE_LIB" "$keep/libdoctrenderer-v8.dylib"
    # However this exits, the tree goes back. A swapped library left behind is
    # a trap for whoever builds next, and they would have no reason to look.
    trap 'cp "$keep/libdoctrenderer-v8.dylib" "$LIVE_LIB" 2>/dev/null || true; rm -rf "$keep"' \
        EXIT INT TERM

    echo "==> V8, for a baseline"
    sh "$HERE/smoke.sh" >"$keep/v8.log" 2>&1 ||
        { echo "FAIL: the ordinary build does not pass smoke either" >&2
          tail -12 "$keep/v8.log" >&2; exit 1; }
    v8_pdf="$(pdf_line "$keep/v8.log")"
    echo "    $v8_pdf"

    echo "==> JavaScriptCore"
    cp "$JSC_LIB" "$LIVE_LIB"
    ok=0
    sh "$HERE/smoke.sh" >"$keep/jsc.log" 2>&1 || ok=1
    jsc_pdf="$(pdf_line "$keep/jsc.log")"
    [ "$ok" = 0 ] || {
        echo "FAIL: smoke did not pass with JavaScriptCore" >&2
        tail -12 "$keep/jsc.log" >&2
        exit 1
    }
    echo "    $jsc_pdf"

    echo
    if [ "$v8_pdf" = "$jsc_pdf" ]; then
        echo "PASS: same PDF from both engines."
    else
        echo "DIFFERENT: the PDF is not the same." >&2
        echo "  V8:              $v8_pdf" >&2
        echo "  JavaScriptCore:  $jsc_pdf" >&2
        exit 1
    fi
}

case "${1:-}" in
build) cmd_build ;;
check) cmd_check ;;
*) echo "usage: doctrenderer-jsc.sh {build|check}" >&2; exit 2 ;;
esac
