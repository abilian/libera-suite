#!/bin/sh
# Open a real window from a *released* Libera Suite, and prove something was drawn.
#
#   sh released-gui.sh                    the Flatpak the CDN serves now
#   LIBERA_ORIGIN=URL sh released-gui.sh  another origin's (`stage`'s, on localhost)
#   sh released-gui.sh --installed        the Flatpak installed here
#   sh released-gui.sh --pypi libera      a libera on $PATH
#
# By default it runs install.sh from the origin, as the install page says,
# into a Flatpak installation of its own under ~/.cache, so the machine's own
# Libera Suite stays as it is, and refuses one whose --version is not the
# release bundles/latest names, or LIBERA_VERSION, which install.sh reads too. Testing whatever was installed is how 0.7.0 was declared to draw a
# window by a 0.5.0 that happened to be on the builder. From a Mac, which can run
# none of this itself, `lb release publish`'s downloads copies it to every Linux
# builder (or --on one), runs it, and fetches the screenshots into build/out/.
# A builder missing the tools says so, with the line that installs them, and
# is not counted as a pass.
#
# `lb linux screenshot` does this from the build tree, in the test container. It
# proves the code opens a window; it says nothing about the artifact anybody
# downloads, which on Linux is a Flatpak whose GTK and WebKit come from the
# GNOME runtime rather than from the distribution. That is a different WebKit,
# and it is the one users get.
#
# It needs no checkout and no payload of its own -- the bundle carries its editors, and the blank it
# opens is taken out of whatever the application says its payload is.
#
# **Two failures look identical from outside and both are checked**: a window
# that never appears, and a window that appears empty because the editor did
# not load in it. The second is the interesting one, and a script that stopped
# at "the process is still running" would call it a pass.
#
# Requires: xvfb-run, dbus-run-session, xwininfo, and ImageMagick (`import` and
# `identify`).
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

ORIGIN="${LIBERA_ORIGIN:-https://cdn.abilian.com/libera}"
MODE=release
LAUNCH=
WANT=
DOC=
OUT=

# The verdict is a line of its own, __LIBERA__=ok or the reason, which is what
# `lb release publish`'s downloads reads: over ssh the exit status is the login
# shell's, and a word like PASS can turn up in a path or in the app's log.
say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
die()  {
    printf '\nFAIL: %s\n' "$*" >&2
    printf '__LIBERA__=%s\n' "$(printf '%s\n' "$*" | head -n 1)"
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
    --installed) MODE=flatpak ;;
    --pypi)    MODE=pypi; LAUNCH="${2:?--pypi wants the libera to run}"; shift ;;
    --doc)     DOC="${2:?--doc wants a file}"; shift ;;
    --out)     OUT="${2:?--out wants a path}"; shift ;;
    -h | --help) sed -n '2,17p' "$0" | sed 's/^#\{1,\} \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
    esac
    shift
done

OUT="${OUT:-${PWD}/released-gui.png}"

# --- what this machine can do -------------------------------------------------

missing=
for tool in xvfb-run dbus-run-session xwininfo import identify; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
[ -z "$missing" ] || die "this machine has no$missing
       Debian, Ubuntu:  sudo apt install xvfb dbus-daemon x11-utils imagemagick
       Fedora:          sudo dnf install xorg-x11-server-Xvfb dbus-daemon xorg-x11-utils ImageMagick"

# --- what to run, and on what document ----------------------------------------

case "$MODE" in
release)
    command -v flatpak >/dev/null 2>&1 || die "this machine has no flatpak"
    # Its own installation: install.sh installs --user, which is
    # FLATPAK_USER_DIR, and copies the menu entry into XDG_DATA_HOME. The
    # runtime downloads once into it, and stays.
    export XDG_DATA_HOME="$HOME/.cache/libera-released-gui"
    export FLATPAK_USER_DIR="$XDG_DATA_HOME/flatpak"
    mkdir -p "$FLATPAK_USER_DIR"
    WANT="${LIBERA_VERSION:-}"
    if [ -z "$WANT" ]; then
        WANT=$(curl -fsSL "$ORIGIN/bundles/latest" | tr -d ' \n\r') \
            || die "could not read $ORIGIN/bundles/latest"
    fi
    step "installing $WANT from $ORIGIN with install.sh, apart from this machine's own"
    # The install page's command. It reads LIBERA_ORIGIN and LIBERA_VERSION
    # itself; a failed download pipes nothing into sh, which the version
    # check below then catches.
    export LIBERA_ORIGIN="$ORIGIN"
    curl -fsSL "$ORIGIN/install.sh" | sh || die "install.sh failed"
    set -- flatpak run --user "$APP_ID"
    ask="flatpak run --user --command=sh $APP_ID -c"
    python="flatpak run --user --command=python3 $APP_ID"
    ;;
flatpak)
    flatpak info "$APP_ID" >/dev/null 2>&1 || die \
        "$APP_ID is not installed.
       curl -fsSL https://cdn.abilian.com/libera/install.sh | sh"
    set -- flatpak run "$APP_ID"
    ask="flatpak run --command=sh $APP_ID -c"
    python="flatpak run --command=python3 $APP_ID"
    ;;
pypi)
    command -v "$LAUNCH" >/dev/null 2>&1 || [ -x "$LAUNCH" ] || die \
        "no such command: $LAUNCH"
    set -- "$LAUNCH"
    ask="sh -c"
    python=
    ;;
esac
LAUNCHER="$*"

step "what is installed here"
version=$("$@" --version) || die "$LAUNCHER --version said nothing"
say "$version"
if [ -n "$WANT" ]; then
    case "$version" in
    "libera $WANT "*) ;;
    *) die "this is not the published $WANT: $version" ;;
    esac
fi

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

# Each Xvfb gets a session bus of its own. On the login's bus, systemd starts
# the desktop portal without a DISPLAY, its GTK backend times out on every
# call, and WebKit, which asks the portal first, never loaded the page: a
# black window on Ubuntu 26.04 (linux-arm64, 0.7.3's stage), where the same
# bundle on a private bus drew the editor in 15 s.
xvfb-run -a --server-args='-screen 0 1600x1000x24' dbus-run-session -- sh -c "
    # xvfb-run starts Xvfb, sleeps three seconds and runs this whether Xvfb
    # listens or not, with its errors sent to /dev/null. An Xvfb that cannot
    # start (Linuxbrew's, missing its libLLVM, on 2026-11-10) then shows up as
    # the app's 'cannot open display', which blames the app.
    tries=0
    while [ ! -S /tmp/.X11-unix/X\${DISPLAY#:} ]; do
        [ \$tries -lt 20 ] || { echo \"__NOXVFB__ \$DISPLAY\"; exit; }
        sleep 0.5
        tries=\$((tries + 1))
    done
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
*__NOXVFB__*) die "Xvfb never listened on ${verdict#*__NOXVFB__ }
       Does it start at all?  $(command -v Xvfb) :120" ;;
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

# --- five minutes in each editor ------------------------------------------------
#
# five-minutes.sh, beside this script with the gui tier's driver, which `lb`
# sends: a blank in each editor typed into, saved, and opened again, run with
# the Flatpak's own Python, so its WebKit and its payload. Not for --pypi,
# whose Python is whatever was on $PATH.

if [ -n "$python" ]; then
    here=$(dirname "$0")
    [ -f "$here/five-minutes.sh" ] && [ -f "$here/released-gui-driver.py" ] \
        || die "no five-minutes.sh and released-gui-driver.py beside $0"
    step "five minutes in each editor, under Xvfb"
    five="$HOME/.cache/libera-released-gui/five"
    rm -rf "$five"
    # shellcheck disable=SC2086  # $python is a command of several words
    said=$(xvfb-run -a --server-args='-screen 0 1600x1000x24' \
        dbus-run-session -- env WEBKIT_DISABLE_COMPOSITING_MODE=1 LIBGL_ALWAYS_SOFTWARE=1 \
        sh "$here/five-minutes.sh" "$here/released-gui-driver.py" "$five" $python)
    printf '%s\n' "$said" | sed 's/^/    /'
    for editor in DOCX XLSX PPTX; do
        case "$said" in
        *"FIVE_$editor=ok"*) ;;
        *) die "five minutes in a .$(printf '%s' "$editor" | tr '[:upper:]' '[:lower:]'): $(printf '%s\n' "$said" | sed -n "s/^FIVE_$editor=//p")" ;;
        esac
    done
fi

step "PASS"
say "    a released $LAUNCHER opened $(basename "$DOC") and drew it."
echo "__LIBERA__=ok"
