#!/bin/sh
# Open a real window from a *released* Libera Suite, and prove something was drawn.
#
#   sh build/released-gui.sh                    here: the installed Flatpak
#   sh build/released-gui.sh --pypi libera      here: a libera on $PATH
#   sh build/released-gui.sh --on fedora.zt     there, and bring the shot back
#   sh build/released-gui.sh --all              every Linux builder, from here
#
# `--all` is the one to reach for on a Mac, which can run none of this itself:
# it takes the machines out of build/builders.toml, copies this script to each,
# runs it, and fetches the screenshots into build/out/. A builder missing the
# tools says so, with the line that installs them, and is not counted as a pass.
#
# `make gui-linux` does this from the build tree, in the test container. It
# proves the code opens a window; it says nothing about the artifact anybody
# downloads, which on Linux is a Flatpak whose GTK and WebKit come from the
# GNOME runtime rather than from the distribution. That is a different WebKit,
# and it is the one users get.
#
# Run it on the machine that has the release installed. It needs no checkout
# and no payload of its own -- the bundle carries its editors, and the blank it
# opens is taken out of whatever the application says its payload is.
#
# **Two failures look identical from outside and both are checked**: a window
# that never appears, and a window that appears empty because the editor did
# not load in it. The second is the interesting one, and a script that stopped
# at "the process is still running" would call it a pass.
#
# Requires: xvfb-run, xwininfo, and ImageMagick (`import` and `identify`).
# Deliberately not scrot and PIL, which is what build/test-linux/gui-smoke.py
# uses: those are in the test image, and this has to run on a plain host.
set -eu

APP_ID=eu.liberasuite.Libera

# Long enough for x2t to convert and the editor to paint. The editor's own load
# is the slow half and has been seen to take twenty seconds on a cold payload.
TIMEOUT=90
# Then this much more, mapped but not necessarily painted. That gap is what
# would otherwise pass.
SETTLE=10
# Below this the window is a flat rectangle: a failed load, or a WebKit that
# never painted. A loaded editor has a toolbar, a ruler and a page in it. Same
# figure as gui-smoke.py, arrived at the same way.
MIN_COLOURS=24

MODE=flatpak
LAUNCH=
DOC=
OUT=
ON=
ALL=

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Non-interactive, and ServerAlive because the editor's own load can be slow
# and a dropped idle session would look exactly like a window that never came.
SSH="ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30"

say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
die()  { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
    --flatpak) MODE=flatpak ;;
    --pypi)    MODE=pypi; LAUNCH="${2:?--pypi wants the libera to run}"; shift ;;
    --doc)     DOC="${2:?--doc wants a file}"; shift ;;
    --out)     OUT="${2:?--out wants a path}"; shift ;;
    --on)      ON="${2:?--on wants an ssh target}"; shift ;;
    --all)     ALL=1 ;;
    -h | --help) sed -n '2,14p' "$0" | sed 's/^#\{1,\} \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
    esac
    shift
done

OUT="${OUT:-${PWD}/released-gui.png}"

# --- driving it somewhere else ------------------------------------------------
#
# This Mac has no flatpak, no Xvfb and no X server, so the only way it can
# answer "does the released Linux artifact draw a window" is to ask a machine
# that can. The script copies itself rather than being installed anywhere: it
# is one file and a builder is not a place to keep state.

on_host() {
    host=$1 platform=${2:-$1}
    shot="$REPO/build/out/released-gui-$platform.png"

    step "$platform on $host"
    $SSH "$host" true 2>/dev/null || { say "    unreachable"; return 1; }
    scp -q -o BatchMode=yes "$SELF" "$host:/tmp/released-gui.sh" || {
        say "    could not copy the script there"; return 1; }

    # bash -l because xvfb-run is often in a login-only PATH (linuxbrew puts it
    # there), and the verdict is read out of what it printed: over ssh an exit
    # status describes the shell, including its logout scripts.
    out=$($SSH "$host" bash -lc "'sh /tmp/released-gui.sh --out /tmp/released-gui.png'" 2>&1) || :
    printf '%s\n' "$out" | sed 's/^/    /'

    case "$out" in
    *PASS*) ;;
    *) return 1 ;;
    esac

    mkdir -p "$REPO/build/out"
    scp -q -o BatchMode=yes "$host:/tmp/released-gui.png" "$shot" || {
        say "    it passed and the screenshot did not come back"; return 1; }
    say "    $shot"
    return 0
}

if [ -n "$ALL" ]; then
    # The one inventory, read by the one parser -- build/origin.sh consumes the
    # same lines. A machine list spelt twice is a machine list that disagrees.
    builders=$(python3 "$REPO/build/remote.py" --print-builders /unused) || die \
        "could not read build/builders.toml"

    tried=0 failed=0
    for line in $(printf '%s\n' "$builders" | awk -F'\t' \
        '$1 ~ /^linux-/ && $2 != "local" { print $1 "," $2 }'); do
        platform=${line%%,*}; target=${line#*,}
        tried=$((tried + 1))
        on_host "$target" "$platform" || failed=$((failed + 1))
    done

    [ "$tried" -gt 0 ] || die "no remote Linux builders in build/builders.toml"
    step "$((tried - failed)) of $tried builder(s) drew a window"
    [ "$failed" -eq 0 ] || exit 1
    exit 0
fi

if [ -n "$ON" ]; then
    on_host "$ON" || exit 1
    exit 0
fi

# --- what this machine can do -------------------------------------------------

missing=
for tool in xvfb-run xwininfo import identify; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
[ -z "$missing" ] || die "this machine has no$missing
       Debian, Ubuntu:  sudo apt install xvfb x11-utils imagemagick
       Fedora:          sudo dnf install xorg-x11-server-Xvfb xorg-x11-utils ImageMagick"

# --- what to run, and on what document ----------------------------------------

case "$MODE" in
flatpak)
    flatpak info "$APP_ID" >/dev/null 2>&1 || die \
        "$APP_ID is not installed.
       curl -fsSL https://cdn.abilian.com/libera/install.sh | sh"
    set -- flatpak run "$APP_ID"
    ask="flatpak run --command=sh $APP_ID -c"
    ;;
pypi)
    command -v "$LAUNCH" >/dev/null 2>&1 || [ -x "$LAUNCH" ] || die \
        "no such command: $LAUNCH"
    set -- "$LAUNCH"
    ask="sh -c"
    ;;
esac
LAUNCHER="$*"

step "what is installed here"
"$@" --version || die "$LAUNCHER --version said nothing"

# The blank comes out of the payload the application reports, never a path
# written here: in a bundle it is inside /app, and a `find` over a guessed
# directory is how this sort of check comes to test nothing.
if [ -z "$DOC" ]; then
    DOC="$HOME/released-gui.docx"
    # shellcheck disable=SC2086  # $ask is a command prefix, deliberately split
    # shellcheck disable=SC2016  # single quotes on purpose: $root and $HOME must
    #                              expand inside the sandbox, not out here
    $ask '
        set -eu
        root=$(libera --payload-status | sed -n "s/^payload: *//p")
        [ -n "$root" ] || { echo "no payload" >&2; exit 1; }
        blank=$(find "$root" -name new.docx | head -1)
        [ -n "$blank" ] || { echo "no new.docx under $root" >&2; exit 1; }
        cp "$blank" "$HOME/released-gui.docx"
    ' || die "could not take a blank document out of the payload"
    [ -f "$DOC" ] || die "the blank was not written to $DOC
       In a Flatpak this needs --filesystem=home, which the manifest grants."
fi
say "    document: $DOC ($(wc -c < "$DOC" | tr -d ' ') bytes)"

# --- open it, under a display that does not exist -----------------------------
#
# The screen is bigger than the window so that Xvfb, which has no window
# manager, does not clip it. WEBKIT_DISABLE_COMPOSITING_MODE and
# LIBGL_ALWAYS_SOFTWARE because Xvfb has no GPU: without them WebKit either
# fails to create a GL context or renders nothing, which looks exactly like the
# empty window this is looking for.

step "a real window, under Xvfb"
rm -f "$OUT"
log=$(mktemp)
trap 'rm -f "$log"' EXIT

xvfb-run -a --server-args='-screen 0 1600x1000x24' sh -c "
    export WEBKIT_DISABLE_COMPOSITING_MODE=1 LIBGL_ALWAYS_SOFTWARE=1
    $LAUNCHER -v '$DOC' >'$log' 2>&1 &
    app=\$!

    waited=0
    while [ \$waited -lt $TIMEOUT ]; do
        kill -0 \$app 2>/dev/null || { echo '__GONE__'; break; }
        if xwininfo -root -tree 2>/dev/null | grep -qi 'released-gui\|Libera'; then
            echo '__WINDOW__'
            break
        fi
        sleep 1
        waited=\$((waited + 1))
    done

    # Mapped is not painted. This wait is the whole point of the colour count
    # that follows it.
    sleep $SETTLE
    import -window root '$OUT' 2>/dev/null || echo '__NOSHOT__'
    kill \$app 2>/dev/null || :
    wait \$app 2>/dev/null || :
" > "$log.outer" 2>&1 || :

verdict=$(cat "$log.outer" 2>/dev/null || echo)
rm -f "$log.outer"

case "$verdict" in
*__GONE__*)   die "$LAUNCHER exited before a window appeared
$(sed 's/^/       | /' "$log")" ;;
*__WINDOW__*) ;;
*) die "no window after ${TIMEOUT}s
$(sed 's/^/       | /' "$log")" ;;
esac

# --- did anything get drawn in it ---------------------------------------------

[ -f "$OUT" ] || die "no screenshot was taken ($OUT)"
colours=$(identify -format '%k' "$OUT" 2>/dev/null || echo 0)
size=$(identify -format '%wx%h' "$OUT" 2>/dev/null || echo '?')

say "    window opened, $colours colours in a $size screenshot"
say "    $OUT"
[ "$colours" -ge "$MIN_COLOURS" ] || die \
    "only $colours colours -- the window opened empty.
       The editor did not load in it. Look at $OUT."

step "PASS"
say "    a released $LAUNCHER opened $(basename "$DOC") and drew it."
