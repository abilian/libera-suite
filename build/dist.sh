#!/bin/sh
# Assemble the distributable payload artifacts.
#
#   build/dist.sh [--fonts core|full]     build the tarballs, then the manifest
#   build/dist.sh --manifest-only         just the manifest, over what is there
#
# Needs a built core (build.sh build) and a built payload (payload.sh). Writes
# $BUILD_ROOT/out/dist/<payload-version>/ -- the tarballs that go on the static
# origin, plus the manifest the wheel verifies them against. See
# notes/05-packaging.md.
#
# --manifest-only is for the last step of a release, where the artifacts have
# arrived from several machines and the only thing left is to describe them.
# The manifest was always a description of a directory -- it globs *.tar.gz and
# reads the platform out of each filename -- and only needed a payload because
# this script rebuilt the tarballs first. On a Linux box that builds in the
# container, there is no native payload to rebuild them from and never was.
#
# gzip, not zstd. Measured on the editors tree: gzip 78 MB, zstd -19 59 MB, both
# decompressing in about a second. 24% is not worth a binary dependency on every
# platform when stdlib tarfile reads gzip natively.
set -eu

# Apple's tar stores extended attributes as AppleDouble members -- a `._name`
# beside every file that has any -- and the build tree collects them (quarantine,
# provenance) just by living on an external volume. Half of editors.tar.gz was
# `._` entries, and every install unpacked 1548 stray files that the editor
# then had to be told to ignore. GNU tar neither reads the variable nor
# produces the files, so this is safe on Linux.
export COPYFILE_DISABLE=1

HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"

PAYLOAD="${PAYLOAD:-$OUT/payload}"
FONT_SET="core"
MANIFEST_ONLY=0
while [ $# -gt 0 ]; do
    case "$1" in
    --fonts) FONT_SET="$2"; shift 2 ;;
    --manifest-only) MANIFEST_ONLY=1; shift ;;
    *) echo "FATAL: unknown argument $1" >&2; exit 2 ;;
    esac
done

VERSION="$(sed -n 's/^version *= *//p' "$HERE/payload.version" | tr -d '"')"
[ -n "$VERSION" ] || { echo "FATAL: no version in build/payload.version" >&2; exit 1; }

case "$(uname -s)-$(uname -m)" in
Darwin-arm64)  PLATFORM="macos-arm64" ;;
Darwin-x86_64) PLATFORM="macos-x86_64" ;;
Linux-x86_64)  PLATFORM="linux-x86_64" ;;
Linux-aarch64) PLATFORM="linux-arm64" ;;
*) PLATFORM="" ;;
esac
# Only a build needs to know what this machine is. A manifest reads the
# platform out of each filename, so it runs anywhere.
if [ "$MANIFEST_ONLY" = "0" ] && [ -z "$PLATFORM" ]; then
    echo "FATAL: unsupported platform $(uname -s)-$(uname -m)" >&2
    exit 1
fi

DIST="$OUT/dist/$VERSION"
STAGE="$OUT/dist/.stage"
rm -rf "$STAGE"
mkdir -p "$DIST" "$STAGE"

if [ "$MANIFEST_ONLY" = "0" ]; then

[ -x "$OUT/core/bin/x2t" ] || { echo "FATAL: no x2t -- run build.sh build" >&2; exit 1; }
[ -d "$PAYLOAD/sdkjs" ] || { echo "FATAL: no payload -- run payload.sh" >&2; exit 1; }

# --- native, per platform -----------------------------------------------------
# DoctRenderer.config is deliberately excluded: it holds absolute paths and is
# written on the target at install time.
echo "==> core ($PLATFORM)"
mkdir -p "$STAGE/bin/tools"
cp -R "$OUT/core/bin/." "$STAGE/bin/"
rm -f "$STAGE/bin/DoctRenderer.config"
cp "$OUT/core/tools/allfontsgen" "$STAGE/bin/tools/"
tar -czf "$DIST/core-$PLATFORM.tar.gz" -C "$STAGE" bin
rm -rf "$STAGE/bin"

# --- editors, platform-neutral ------------------------------------------------
# Words, Tables, Slides and Diagrams. pdfeditor is left out: nothing routes to
# it yet (see src/libera/host/apps.py).
echo "==> editors"
mkdir -p "$STAGE/web-apps/apps" "$STAGE/sdkjs"
cp -R "$PAYLOAD/web-apps/vendor" "$STAGE/web-apps/"
for d in api common documenteditor spreadsheeteditor presentationeditor visioeditor; do
    cp -R "$PAYLOAD/web-apps/apps/$d" "$STAGE/web-apps/apps/"
done
for d in documenteditor spreadsheeteditor presentationeditor visioeditor; do
    # The desktop suite needs main/ only; mobile, forms and embed are the web
    # product's other entry points and nothing here links to them.
    rm -rf "$STAGE/web-apps/apps/$d/mobile" \
           "$STAGE/web-apps/apps/$d/forms" \
           "$STAGE/web-apps/apps/$d/embed"
    # 500 MB of help across the four, in eight languages, which nothing can
    # reach: upstream hardcodes canHelp = false. It is also ONLYOFFICE's
    # manual, not ours. When Libera Suite has its own documentation this comes back
    # -- see notes/04-plan.md.
    rm -rf "$STAGE/web-apps/apps/$d/main/resources/help"
done
for d in common word cell slide visio vendor; do
    cp -R "$PAYLOAD/sdkjs/$d" "$STAGE/sdkjs/"
done
# The theme .pptx sources are the input to payload.sh's theme generation, not
# something the editor reads: it loads themeN/theme.bin. 2.1 MB of duplicates.
rm -rf "$STAGE/sdkjs/slide/themes/src"
[ -f "$STAGE/sdkjs/slide/themes/themes.js" ] || {
    echo "FATAL: no slide themes -- run payload.sh" >&2; exit 1; }
# The generated font files travel with the fonts, not the editors.
rm -f "$STAGE/sdkjs/common/AllFonts.js" "$STAGE/sdkjs/common/font_selection.bin"
rm -rf "$STAGE/sdkjs/common/Images/fonts_thumbnail"*

# doctrenderer writes a V8 code cache next to each bundle the first time it
# runs one -- `sdkjs/word/sdk-all.cache`, 8 MB, 2.9 of them compressed.
#
# Three things wrong with shipping it, and the third is why this is a `find`
# and not a named file. It is a **V8 code cache**: keyed to the architecture
# and to the exact V8 build that wrote it, sitting in the one artifact that
# goes to macOS arm64, Linux x86_64 and Linux arm64 alike. It makes the
# artifact **nondeterministic**: it is here only when something ran the
# converter before dist.sh, which on a release is smoke.sh and on a bare
# payload build is nothing -- the same tree packaged twice gave 47.6 MB and
# 44.7 MB, and that was how this was found. And it is **regenerated locally in
# a second**, like AllFonts.js three lines above, for the same reason.
find "$STAGE/sdkjs" -name '*.cache' -delete
cp -R "$PAYLOAD/empty" "$STAGE/"
# Spell-check dictionaries: platform-neutral, and the engine that reads them
# is already inside sdkjs/common/spell.
[ -d "$PAYLOAD/dictionaries" ] || { echo "FATAL: no dictionaries -- run payload.sh" >&2; exit 1; }
cp -R "$PAYLOAD/dictionaries" "$STAGE/"

# Nothing brand-shaped in here that we did not put there.
#
# "No ONLYOFFICE artifacts, ever" includes their images, and every payload this
# project built shipped some until the theme and the patch queue caught up.
# Both of those work by *name* -- overwrite theirs, or delete it -- and a name
# is exactly what fails silently when upstream adds or renames one. Nothing in
# the build would have said a word; it was found by listing the directory.
#
# So list it here, where the shipped set is known, and compare against what our
# own theme and patches put there. An allowlist rather than a blocklist,
# because the file we have not thought of is the whole point.
#
# Matched on the name and not the content: `grep -ril onlyoffice` across ten
# thousand images finds nothing at all. A logo is geometry, not a string.
echo "==> brand check"
# The four names upstream hardcodes, which payload.sh writes our wordmark to,
# plus the embed logo and the two the theme ships under their own names.
OURS="dark-logo_s.svg header-logo_s.svg logo_s.svg logo-white_s.svg logo.svg
wordmark-ink.svg wordmark-paper.svg"
strays=""
found=0
for f in $(find "$STAGE/web-apps" "$STAGE/sdkjs" \
               \( -iname '*logo*' -o -iname '*favicon*' -o -iname '*apple-touch*' \
                  -o -iname '*wordmark*' -o -iname '*brand*' \) \
               -type f 2>/dev/null); do
    found=$((found + 1))
    case " $(echo $OURS) " in
    *" $(basename "$f") "*) ;;
    *) strays="$strays$(echo "$f" | sed "s|$STAGE/||")
" ;;
    esac
done
if [ -n "$strays" ]; then
    echo "FATAL: artwork in the payload that is not ours:" >&2
    printf '%s' "$strays" | sed 's/^/    /' >&2
    echo "  Look at it before deciding. If it is upstream's, take it out in" >&2
    echo "  build/patches/web-apps/ or write over it in payload.sh; if it is" >&2
    echo "  ours, add the name to OURS above." >&2
    exit 1
fi
[ "$found" -gt 0 ] || { echo "FATAL: no brand artwork at all -- the theme did not land" >&2; exit 1; }
echo "    $found brand files, all ours"

tar -czf "$DIST/editors.tar.gz" -C "$STAGE" sdkjs web-apps empty dictionaries
rm -rf "$STAGE/sdkjs" "$STAGE/web-apps" "$STAGE/empty" "$STAGE/dictionaries"

# --- fonts, platform-neutral, sources only ------------------------------------
# The web fonts are generated on the target: doctrenderer reads the real TTFs,
# and AllFonts.js records their absolute paths, so neither can be built here.
echo "==> fonts ($FONT_SET)"
resolve_core_fonts
mkdir -p "$STAGE/fonts-src"
if [ "$FONT_SET" = "full" ]; then
    cp -R "$CORE_FONTS/." "$STAGE/fonts-src/"
    rm -rf "$STAGE/fonts-src/.git"
else
    list="$HERE/fonts-$FONT_SET.txt"
    [ -f "$list" ] || { echo "FATAL: no font list $list" >&2; exit 1; }
    grep -vE '^[[:space:]]*#|^[[:space:]]*$' "$list" | while read -r name; do
        [ -e "$CORE_FONTS/$name" ] || { echo "FATAL: no font $name in $CORE_FONTS" >&2; exit 1; }
        cp -R "$CORE_FONTS/$name" "$STAGE/fonts-src/"
    done
fi
# Licence files travel with the fonts they cover.
for f in "$CORE_FONTS"/LICENSE* "$CORE_FONTS"/README*; do
    [ -f "$f" ] && cp "$f" "$STAGE/fonts-src/"
done
tar -czf "$DIST/fonts-$FONT_SET.tar.gz" -C "$STAGE" fonts-src
rm -rf "$STAGE/fonts-src"

fi  # MANIFEST_ONLY

# --- manifest -----------------------------------------------------------------
# The wheel ships this and verifies downloads against it, so the origin is
# untrusted storage. Provenance is recorded here because a shipped binary has to
# name the source it was built from -- see notes/05-packaging.md on licensing.
echo "==> manifest"
python3 - "$DIST" "$VERSION" "$PLATFORM" "$FONT_SET" "$HERE" <<'PY'
import hashlib, json, pathlib, subprocess, sys, time

dist, version, platform, font_set, here = (pathlib.Path(sys.argv[1]), *sys.argv[2:5], pathlib.Path(sys.argv[5]))

def sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def git(*args):
    try:
        return subprocess.run(["git", "-C", str(here.parent), *args],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None

pins = {}
section = None
for line in (here / "pins.toml").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith("["):
        section = line.strip("[]")
    elif section == "repos" and "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        pins[k.strip()] = v.split("#")[0].strip().strip('"')

# Every artifact in the directory, not just this run's. A release needs one
# core per platform, built on each and collected here, so the platform has to
# come from the filename -- labelling them all with whichever machine wrote the
# manifest last would hand macOS users a Linux build.
artifacts = []
for p in sorted(dist.glob("*.tar.gz")):
    if p.name.startswith("core-"):
        kind, art_platform = "core", p.name[len("core-") : -len(".tar.gz")]
    else:
        kind, art_platform = p.name.split(".")[0].split("-")[0], None
    artifacts.append({
        "name": p.name,
        "kind": kind,
        "platform": art_platform,
        "size": p.stat().st_size,
        "sha256": sha256(p),
    })

manifest = {
    "payload_version": version,
    "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "font_set": font_set,
    "artifacts": artifacts,
    # Corresponding source, per AGPL: a pinned SHA plus a patch series that
    # applies to it cleanly. Repositories are public; we do not host tarballs.
    "source": {
        "pins": pins,
        "libera_commit": git("rev-parse", "HEAD"),
        "libera_dirty": bool(git("status", "--porcelain")),
        # One host, because one host answers. 05-packaging.md wants two, so
        # that the AGPL obligation outlives our interest in any particular
        # forge, and the SourceHut mirror is not up under this name yet:
        # git.sr.ht/~sfermigier/libera-suite is a 404 and the repository that
        # exists is still called muchado. A corresponding-source pointer that
        # does not resolve reads as compliance without being it, which is
        # worse than naming one host and meaning it. Add the second back when
        # it is there.
        "repositories": [
            "https://github.com/abilian/libera-suite",
        ],
        "upstream": "https://github.com/Euro-Office",
    },
}
(dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
for a in artifacts:
    print(f"    {a['name']:26} {a['size'] / 1e6:7.1f} MB  {a['sha256'][:16]}…")
if manifest["source"]["libera_dirty"]:
    print("    WARNING: built from a dirty tree; provenance is not reproducible")

platforms = sorted(a["platform"] for a in artifacts if a["kind"] == "core")
print(f"    platforms: {', '.join(platforms)}")
PY

# The wheel verifies downloads against this, which is what makes the origin
# untrusted storage. It is a source file, so a release commits it -- and a
# release needs every platform's core sitting in $DIST first.
if [ "${INSTALL_MANIFEST:-0}" = "1" ]; then
    cp "$DIST/manifest.json" "$HERE/../src/libera/manifest.json"
    echo "    manifest installed into the wheel"
fi

rm -rf "$STAGE"
echo
echo "dist: $DIST"
