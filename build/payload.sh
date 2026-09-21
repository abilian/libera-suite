#!/bin/sh
# Build the editor payload: the JS half of the suite, plus the fonts and the
# doctrenderer wiring that x2t needs to run it.
#
#   build/payload.sh
#
# Needs `build.sh fetch sdkjs web-apps` and a built core (build.sh build).
# Output is $BUILD_ROOT/out/payload:
#
#   sdkjs/          editor bundles (SDK_PLATFORM=desktop -> the offline layer)
#   web-apps/       the UI
#   fonts/          web fonts, fetched over HTTP by the editor
#   empty/          blank documents (File > New), from document-templates
#   AllFonts.js     filesystem-path font list, for doctrenderer
#
# NB both upstream pipelines take BUILD_ROOT to mean the DocumentServer root
# they write into, which is not what it means to build.sh. Every invocation
# below sets it explicitly for that reason.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"

PAYLOAD="${PAYLOAD:-$OUT/payload}"

# web-apps rejects a major version below 6, so this cannot be our package
# version. It is the Euro-Office editor version, and it is what ends up in
# CApp.getAppName() and hence in the <Application> field of saved documents.
EO_VERSION="${EO_VERSION:-9.2.1}"

# Branding. THEME names a directory under web-apps/theme/ whose meta/config.json
# carries company_name, publisher_url, app_title, the logos and the attribution
# line -- that file is the brand surface, not this script.
COMPANY_NAME="${COMPANY_NAME:-Libera Suite}"
BLANK_LOCALE="${BLANK_LOCALE:-en-US}"
THEME="${THEME:-libera}"
PUBLISHER_URL="${PUBLISHER_URL:-https://abilian.com/}"
APP_COPYRIGHT="${APP_COPYRIGHT:-Copyright (C) Abilian SAS 2026. All rights reserved}"

# Both pipelines run their phases in parallel, and a webpack wants close to a
# gigabyte of V8 heap -- four at once is killed by the OOM killer on a 4 GB
# machine before a bundle is written. BUILD_JOBS caps a phase; 0 means "all of
# them", which is the upstream default and what a build machine wants.
#
# The same number that decides how many compilers the core build runs, because
# the constraint is the same one and two heuristics would drift. On a 4 GB box
# that is 1, on a 16 GB Mac 4 -- and four webpacks fit in 16 GB comfortably.
# See build/patches/{sdkjs,web-apps}/*BUILD_JOBS*.
BUILD_JOBS="${BUILD_JOBS:-$(build_jobs)}"
export BUILD_JOBS

# V8 picks its own heap ceiling from the cgroup limit, not from what the work
# needs -- so a *smaller* container makes webpack aim lower and die sooner,
# with memory still unused. Measured on arm64, BUILD_JOBS=1 throughout:
#
#   2 GB container   FATAL heap out of memory, peak 1340 MB
#   3 GB container   FATAL heap out of memory, peak 2880 MB
#   4 GB container   passes, peak 3452 MB
#
# The biggest bundle wants 1.5-2 GB of old space, and only a 4 GB cgroup makes
# V8 offer that much on its own. Below that, say the number: the same 2 GB
# container then passes, in 168s instead of dying. It needs swap to do it --
# which is the same thing the core build needs on a machine this size.
#
# Only on small machines. A build box's V8 already picks more than this, and
# setting it there would be a ceiling rather than a floor.
JS_HEAP_MB="${JS_HEAP_MB:-2048}"
if [ "$(usable_gb)" -lt 6 ] && [ -z "${NODE_OPTIONS:-}" ]; then
    NODE_OPTIONS="--max-old-space-size=$JS_HEAP_MB"
    export NODE_OPTIONS
    echo "==> JS build jobs: $BUILD_JOBS, heap ${JS_HEAP_MB}MB (from $(usable_gb) GB usable)"
    echo "    Little memory here, so this is slow and wants swap: V8 is being"
    echo "    given more heap than the container has RAM, deliberately."
else
    echo "==> JS build jobs: $BUILD_JOBS (from $(usable_gb) GB usable)"
fi

[ -x "$OUT/core/bin/x2t" ] || { echo "FATAL: no x2t -- run build.sh build" >&2; exit 1; }
for repo in sdkjs web-apps; do
    [ -d "$SRC/$repo" ] || { echo "FATAL: no $SRC/$repo -- run build.sh fetch $repo" >&2; exit 1; }
done

# sdkjs has no lockfile, web-apps has one. Only install when missing: these
# land in the pinned source tree, and `build.sh fetch` cleans them out again.
[ -d "$SRC/sdkjs/build/node_modules" ]    || (cd "$SRC/sdkjs/build"    && npm install --no-audit --no-fund)
[ -d "$SRC/web-apps/build/node_modules" ] || (cd "$SRC/web-apps/build" && npm ci --no-audit --no-fund)

# Both pipelines *deploy* into $PAYLOAD -- they copy, and they never delete.
# So a payload directory that is reused across builds accumulates everything
# every earlier configuration ever put there, and nothing anywhere says so.
#
# That is not hypothetical. It shipped ONLYOFFICE's favicon out of a container
# whose source tree no longer contained one, because the patch that removed it
# could only remove it from the *source*; the copy from the build before was
# still sitting in the output. Euro-Office's eo_logo_*.svg outlived the theme
# that asked for them the same way.
#
# Cheap, too: webpack's cache is in the source tree, not here, so this costs
# the deploy copies and not a rebuild. Measured either way at about two
# minutes a pipeline.
rm -rf "$PAYLOAD/sdkjs" "$PAYLOAD/web-apps"

echo "==> sdkjs ($COMPANY_NAME $EO_VERSION, desktop)"
# SDK_PLATFORM=desktop is what adds common/Local/common.js, word/Local/api.js
# and common/Local/license.js -- the entire JS delta between the web build and
# the offline one. Without it the bundle has no AscDesktopEditor support at all.
# The pipeline takes everything through the environment and rejects argv.
# Both pipelines read BUILD_ROOT as the DocumentServer *root* and append their
# own directory to it -- sdkjs via resolveBuildRoot(), web-apps directly. Give
# either one "$PAYLOAD/sdkjs" and the output lands in $PAYLOAD/sdkjs/sdkjs.
(cd "$SRC/sdkjs/build" && env \
    BUILD_ROOT="$PAYLOAD" \
    PRODUCT_VERSION="$EO_VERSION" BUILD_NUMBER=0 \
    COMPANY_NAME="$COMPANY_NAME" \
    PUBLISHER_URL="$PUBLISHER_URL" APP_COPYRIGHT="$APP_COPYRIGHT" \
    SDK_PLATFORM=desktop \
    node scripts/build-pipeline.cjs)

# Our themes live in this repo, not in the pinned tree. Assemble the active one
# into web-apps before building: additive, so it needs no patch, and
# `build.sh fetch` cleans it away again.
#
# Standalone since we have our own artwork. It used to be copied over
# theme/euro-office and take their logo and LESS; inheriting a logo we were
# never going to keep only meant the day it changed was a surprise.
if [ -d "$HERE/theme/$THEME" ]; then
    echo "==> theme $THEME"
    THEME_DIR="$SRC/web-apps/theme/$THEME"
    rm -rf "$THEME_DIR"
    mkdir -p "$THEME_DIR"
    cp -R "$HERE/theme/$THEME/." "$THEME_DIR/"

    # Four filenames are hardcoded in upstream's LESS, and two of them --
    # about/logo_s.svg and about/logo-white_s.svg -- hold ONLYOFFICE's own
    # wordmark in the stock tree. deploy-theme-images.js *overlays* the
    # theme's img/ onto that tree rather than replacing it, so a file of the
    # right name here is the only thing that takes the stock one out of the
    # payload. Landing on upstream's names is also why nothing in our LESS has
    # to override a logo: about.less and header.less pick these up by default.
    #
    # Copied rather than committed four times over: the same drawing in four
    # files is four things to keep in step, and the names are upstream's
    # business rather than the brand's.
    IMG="$THEME_DIR/assets/img"
    for pair in \
        header/wordmark-ink.svg:header/dark-logo_s.svg \
        header/wordmark-paper.svg:header/header-logo_s.svg \
        header/wordmark-ink.svg:about/logo_s.svg \
        header/wordmark-paper.svg:about/logo-white_s.svg
    do
        from="${pair%%:*}"
        to="${pair#*:}"
        [ -f "$IMG/$from" ] || { echo "FATAL: theme has no $from" >&2; exit 1; }
        mkdir -p "$IMG/$(dirname "$to")"
        cp "$IMG/$from" "$IMG/$to"
    done
fi

echo "==> web-apps (theme=$THEME)"
(cd "$SRC/web-apps/build" && env \
    BUILD_ROOT="$PAYLOAD" \
    PRODUCT_VERSION="$EO_VERSION" BUILD_NUMBER=0 \
    THEME="$THEME" APP_COPYRIGHT="$APP_COPYRIGHT" \
    node scripts/build-pipeline.js)

# web-apps also emits sdkjs-assets/, a legacy path from when it had to supply
# the SDK's images and Native scripts itself. The sdkjs pipeline above already
# writes a complete tree, so this is redundant -- drop it rather than leave two
# copies of the same assets to disagree later.
rm -rf "$PAYLOAD/sdkjs-assets"

# The embedded viewer's logo, which no theme can reach.
#
# It is the last ONLYOFFICE drawing in the payload, and it needs a second pass
# because the theme mechanism cannot reach it. deploy-theme-images.js takes a
# theme's embed/logo.svg to apps/<editor>/embed/resources/img/, one per editor
# -- while the only stylesheet that asks for an embed logo,
# common/embed/resources/less/common.less:267, reads
# common/embed/resources/img/logo.svg, which nothing writes. So those four
# would be unreferenced and upstream's would still be the one that renders.
# Hence no embed/logo.svg in our theme, and this instead.
#
# Ink rather than paper: that stylesheet puts it on a light bar.
EMBED_LOGO="$PAYLOAD/web-apps/apps/common/embed/resources/img/logo.svg"
OUR_WORDMARK="$HERE/theme/$THEME/assets/img/header/wordmark-ink.svg"
if [ -d "$HERE/theme/$THEME" ] && [ -f "$EMBED_LOGO" ]; then
    [ -f "$OUR_WORDMARK" ] || {
        echo "FATAL: theme $THEME has no header/wordmark-ink.svg for the embed logo" >&2
        exit 1
    }
    cp "$OUR_WORDMARK" "$EMBED_LOGO"
fi

# The blank documents, from document-templates: new/<locale>/new.docx and its
# pptx/xlsx siblings, 45 locales.
#
# Do NOT substitute core/Common/empty/*.bin for these. That file looks like a
# ready-made blank and is not one: converted to docx it yields
# <w:u w:val="dash"/> and w:line="65" as *document defaults*, so every document
# built on it renders underlined with its lines piled on top of each other.
# Upstream's own x2t produces identical output from it, so the values are in
# the .bin. This repo is the real source.
echo "==> blank documents ($BLANK_LOCALE)"
BLANK_SRC="$SRC/document-templates/new/$BLANK_LOCALE"
[ -d "$BLANK_SRC" ] || { echo "FATAL: no templates for $BLANK_LOCALE -- run build.sh fetch document-templates" >&2; exit 1; }
rm -rf "$PAYLOAD/empty"
mkdir -p "$PAYLOAD/empty"
cp "$BLANK_SRC"/new.* "$PAYLOAD/empty/"

# The defaults these carry are what every new document inherits, so check them
# rather than trust them.
python3 - "$PAYLOAD/empty/new.docx" <<'CHECK'
import re, sys, zipfile
d = re.search(r"<w:docDefaults>.*?</w:docDefaults>",
              zipfile.ZipFile(sys.argv[1]).read("word/styles.xml").decode("utf-8", "replace"), re.S)
assert d, "blank template has no docDefaults"
assert "<w:u " not in d.group(0), "blank template carries a default underline"
line = re.search(r'w:line="(\d+)"', d.group(0))
assert line is None or int(line.group(1)) >= 200, f"blank template leading is {line.group(1)}"
CHECK

# One payload root, as notes/05-packaging.md defines it: the binaries belong
# under it, so LIBERA_PAYLOAD pointing here is a payload the host accepts.
# A symlink rather than a copy, so a rebuilt core is picked up with no action.
ln -sfn "$OUT/core/bin" "$PAYLOAD/bin"

generate_fonts "$PAYLOAD"

# Spell checking. sdkjs already carries the Hunspell engine as a web worker
# (sdkjs/common/spell/spell/, wasm plus a JS fallback) and the desktop bundle
# ships it -- what the desktop build leaves out is spell.js, the wrapper that
# starts the worker, because upstream's own host spell-checks in C++ instead.
# We drive the worker from the browser side, so we need the wrapper and the
# dictionaries it fetches over HTTP.
echo "==> dictionaries"
cp "$SRC/sdkjs/common/spell/spell.js" "$PAYLOAD/sdkjs/common/spell/spell.js"
rm -rf "$PAYLOAD/dictionaries"
mkdir -p "$PAYLOAD/dictionaries"
count=0
grep -vE '^[[:space:]]*#|^[[:space:]]*$' "$HERE/dictionaries.txt" | while read -r lang; do
    src="$SRC/dictionaries/$lang"
    [ -f "$src/$lang.aff" ] && [ -f "$src/$lang.dic" ] || {
        echo "FATAL: no $lang.aff/.dic in $src" >&2; exit 1; }
    mkdir -p "$PAYLOAD/dictionaries/$lang"
    cp "$src/$lang.aff" "$src/$lang.dic" "$PAYLOAD/dictionaries/$lang/"
done || exit 1
count="$(find "$PAYLOAD/dictionaries" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
[ "$count" -gt 0 ] || { echo "FATAL: no dictionaries copied" >&2; exit 1; }
echo "    $count languages"


# Slide themes. sdkjs ships the eleven designs as .pptx under
# slide/themes/src/ and nothing else: themes.js and the per-theme binaries are
# generated artifacts, listed in sdkjs/.gitignore and produced by a
# DocumentServer packaging step we do not have. web-apps' own build README
# lists the resulting 404 under "known issues, outside web-apps scope".
#
# The contract is small (sdkjs/slide/Drawing/ThemeLoader.js): themes.js sets
# AscCommon.g_defaultThemes to a list of names, and theme N is loaded from
# themeN/theme.bin -- which is an Editor.bin, exactly what the three-argument
# x2t form writes. So generate both.
echo "==> slide themes"
THEMES="$PAYLOAD/sdkjs/slide/themes"
if [ -d "$THEMES/src" ]; then
    rm -rf "$THEMES"/theme[0-9]* "$THEMES/themes.js"
    n=0
    names=""
    # Sorted, because the numbering in the filenames *is* the theme order: the
    # loader asks for themeN by index into g_defaultThemes.
    for src in "$THEMES"/src/*.pptx; do
        n=$((n + 1))
        mkdir -p "$THEMES/theme$n"
        if ! built x2t "$src" "$THEMES/theme$n/theme.bin" \
                "$PAYLOAD/sdkjs/common/font_selection.bin" >/dev/null 2>&1; then
            echo "FATAL: x2t could not convert theme $(basename "$src")" >&2
            exit 1
        fi
        [ -s "$THEMES/theme$n/theme.bin" ] || {
            echo "FATAL: empty theme.bin for $(basename "$src")" >&2; exit 1; }
        # "05_green leaf.pptx" -> "Green leaf"
        label="$(basename "$src" .pptx | sed 's/^[0-9]*_//')"
        label="$(printf '%s' "$label" | cut -c1 | tr '[:lower:]' '[:upper:]')$(printf '%s' "$label" | cut -c2-)"
        names="$names\"$label\","
    done
    printf 'window["AscCommon"] = window["AscCommon"] || {};\nwindow["AscCommon"]["g_defaultThemes"] = [%s];\n' \
        "$(printf '%s' "$names" | sed 's/,$//')" > "$THEMES/themes.js"
    echo "    $n themes"
else
    echo "    no themes/src in the payload -- skipped"
fi

# x2t looks for DoctRenderer.config beside its own binary, and the one shipped
# in upstream packages has relative paths for the DocumentServer tree.
echo "==> DoctRenderer.config"
cat > "$OUT/core/bin/DoctRenderer.config" <<CONF
<Settings>
<file>$PAYLOAD/sdkjs/common/Native/native.js</file>
<file>$PAYLOAD/sdkjs/common/Native/jquery_native.js</file>
<allfonts>$PAYLOAD/AllFonts.js</allfonts>
<file>$PAYLOAD/web-apps/vendor/xregexp/xregexp-all-min.js</file>
<sdkjs>$PAYLOAD/sdkjs</sdkjs>
</Settings>
CONF

echo
echo "payload: $PAYLOAD"
du -sh "$PAYLOAD"/* 2>/dev/null | sed 's/^/  /'
