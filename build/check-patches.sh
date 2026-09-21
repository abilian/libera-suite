#!/bin/sh
# Does the patch queue still apply cleanly to the pinned sources?
#
#   build/check-patches.sh
#
# A scratch worktree per patched repo, so this disturbs no working tree and
# forces no rebuild: a worktree shares the object store, and the whole thing
# costs seconds. Run it after editing patches/ and after bumping a pin.
#
# Needs the sources fetched (build.sh fetch). Nothing is built.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"

status=0

for dir in "$HERE"/patches/*/; do
    repo="$(basename "$dir")"
    src="$SRC/$repo"
    [ -d "$src/.git" ] || {
        echo "SKIP $repo: no checkout at $src -- run build.sh fetch $repo"
        continue
    }

    sha="$(sed -n "s/^$repo *= *\"\([0-9a-f]*\)\".*/\1/p" "$HERE/pins.toml" | head -1)"
    [ -n "$sha" ] || { echo "FAIL $repo: no pin in pins.toml" >&2; status=1; continue; }

    n="$(ls "$dir"/*.patch 2>/dev/null | wc -l | tr -d ' ')"
    work="$(mktemp -d)"
    rm -rf "$work"   # git worktree add wants the path not to exist

    # --keep-cr for the same reason build.sh needs it: upstream keeps CRLF
    # files, git am parses a patch as mail, and mailinfo strips the trailing CR
    # from every line -- after which no context matches and the series is
    # rejected with nothing to suggest line endings were involved.
    if git -C "$src" worktree add --quiet --detach "$work" "$sha" 2>/dev/null &&
       git -C "$work" am --keep-non-patch --keep-cr "$dir"/*.patch >"$work.log" 2>&1; then
        echo "  ok   $repo: $n/$n applied to $(echo "$sha" | cut -c1-10)"
    else
        echo "  FAIL $repo: the series no longer applies; see $work.log" >&2
        sed -n '/^Applying\|error\|Patch failed/p' "$work.log" 2>/dev/null | tail -5 >&2
        status=1
    fi
    git -C "$src" worktree remove --force "$work" 2>/dev/null || rm -rf "$work"
    [ "$status" -eq 0 ] && rm -f "$work.log"
done

[ "$status" -eq 0 ] && echo "patch queue: clean"
exit "$status"
