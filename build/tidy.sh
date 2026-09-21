#!/bin/sh
# Remove every build on this machine.
#
#   make tidy        say what would go, and how much
#   make tidy YES=1  do it
#
# Two places hold builds and both go: the repository, where the Flatpak's
# builddir and ostree store are the bulk of it, and $BUILD_ROOT, which is the
# payload, the native core and the two Linux container trees. On the laptop
# this was written on that is 1.4 GB and 44 GB respectively.
#
# $BUILD_ROOT/src goes too. It is a clone of six upstream repositories at the
# pinned SHAs, so it is a build input rather than a build -- but it lives in
# the build area, `payload-fetch` recreates it, and leaving 6.5 GB behind
# after a command called tidy would be its own surprise.
#
# **Dry by default.** Not a guard against the person who typed it: they asked.
# It is that this deletes a day of V8, ICU and container builds, and seeing the
# list first costs one extra word. `YES=1` is that word.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
. "$HERE/common.sh"

# Everything the repository's own builds write. All of it is gitignored; the
# check that it stays that way is in tests, because `rm -rf build` once took
# the patch queue with it.
REPO_PATHS="build/out
build/flatpak/.flatpak-builder
build/flatpak/builddir
build/flatpak/repo
build/flatpak/wheels
build/flatpak/payload
build/flatpak/payload.tmp
docs/site
docs/.cache
dist
.pytest_cache
.ruff_cache
.mypy_cache
htmlcov"

size_of() { du -sh "$1" 2>/dev/null | cut -f1; }

listed=""
total_k=0

note() {
    [ -e "$1" ] || return 0
    listed="$listed
  $(size_of "$1")\t$1"
    total_k=$((total_k + $(du -sk "$1" 2>/dev/null | cut -f1)))
}

for p in $REPO_PATHS; do note "$REPO/$p"; done
for p in "$REPO"/build/flatpak/*.flatpak; do note "$p"; done
note "$BUILD_ROOT"

if [ -z "$listed" ]; then
    echo "    nothing to tidy"
    exit 0
fi

printf '%b\n' "$listed" | sed "s|$REPO/|  |; s|$REPO\$|  .|"
echo
echo "    $((total_k / 1024 / 1024)) GB in total"

if [ "${YES:-}" != "1" ]; then
    echo
    echo "    nothing removed. To do it:  make tidy YES=1"
    exit 0
fi

echo
for p in $REPO_PATHS; do rm -rf "$REPO/$p"; done
rm -rf "$REPO"/build/flatpak/*.flatpak
rm -rf "$BUILD_ROOT"
# adt owns its own caches and knows where they are.
(cd "$REPO" && adt clean >/dev/null 2>&1) || true
echo "    removed. $BUILD_ROOT is gone too, so the next payload build starts"
echo "    from the fetch: make payload-all"
