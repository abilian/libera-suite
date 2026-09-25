#!/bin/sh
# Install Libera Suite, without root.
#
#     curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
#
# With options, which a pipe cannot pass on its own -- the shell needs `-s --`
# to know the rest of the line is for the script and not for itself:
#
#     curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
#     curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
#
# Read it first if you like; that is why it is served as text/plain and why it
# is short enough to read. It writes to two places and nowhere else:
#
#     ~/.local/bin/libera                     the command
#     ~/.local/share/libera/                  the virtualenv behind it
#
# and then asks `libera` to fetch its editor payload, which lands in the
# platform data directory (~/Library/Application Support/Libera Suite on macOS,
# ~/.local/share/Libera Suite on Linux). Nothing is written outside $HOME and
# nothing asks for a password.
#
# `--help` lists the options; they are defined once, in usage() below.
#
# Uninstalling is `rm -rf` on the two paths above plus the data directory,
# which `libera --payload-remove` will do for the third. A Flatpak install is
# `flatpak uninstall eu.liberasuite.Libera`, and then the menu entry this
# script copies into $XDG_DATA_HOME -- flatpak does not know about that copy,
# and an icon left behind launching nothing is worse than no icon:
#
#   rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop \
#         ~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.*
#
# **Every step asserts on what it produced**, never on an exit status: this
# project has been bitten repeatedly by tools that exit 0 having done nothing,
# and an installer is the worst place for it. See notes/lessons-learned.md.
set -eu

APP_ID=eu.liberasuite.Libera
ORIGIN="${LIBERA_ORIGIN:-https://cdn.abilian.com/libera}"
PREFIX="${LIBERA_PREFIX:-$HOME/.local}"
CHANNEL="${LIBERA_CHANNEL:-}"
PAYLOAD=yes
[ "${NO_PAYLOAD:-}" = "1" ] && PAYLOAD=no

say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
die()  { printf '\nFATAL: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# A heredoc and not `sed "$0"`. Piped into a shell there is no $0 to read --
# it is "bash" -- so reading the file printed `sed: bash: No such file or
# directory` for the one invocation this script exists to support.
usage() {
    cat <<'EOF'
Install Libera Suite, without root.

    curl -fsSL https://cdn.abilian.com/libera/install.sh | sh

With options:

    curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
    curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps

    --prefix DIR        install somewhere else (default: ~/.local)
    --channel flatpak   on Linux, the bundle: its own GTK and WebKit (default)
    --channel pip       the Python package instead, against the system GTK
    --no-payload        install the command and skip the 120 MB download
    --origin URL        somewhere other than the public origin
    --help

The environment variables those replace still work, so an older one-liner
keeps running: LIBERA_PREFIX, LIBERA_CHANNEL, NO_PAYLOAD, LIBERA_ORIGIN. An
option wins over the variable.

It writes to $PREFIX/bin/libera and $PREFIX/share/libera and nowhere else,
then asks libera to fetch its editor payload into the platform data
directory. Nothing goes outside $HOME and nothing asks for a password.

Uninstalling is `rm -rf` on those two paths; `libera --payload-remove` drops
the payload. A Flatpak install is `flatpak uninstall eu.liberasuite.Libera`,
then rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop and
~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.* -- the menu entry
this script copies there, which flatpak does not remove.
EOF
}

# Parsed before anything is computed from it, so that --prefix reaches $BIN.
while [ $# -gt 0 ]; do
    case "$1" in
    --prefix)  PREFIX="${2:?--prefix wants a directory}"; shift ;;
    --channel) CHANNEL="${2:?--channel wants flatpak or pip}"; shift ;;
    --origin)  ORIGIN="${2:?--origin wants a URL}"; shift ;;
    --no-payload) PAYLOAD=no ;;
    -h | --help)  usage; exit 0 ;;
    # A bare `--` is what `sh -s --` leaves behind when there are no options.
    --) ;;
    *) say "unknown option: $1"; say ""; usage; exit 2 ;;
    esac
    shift
done

case "$CHANNEL" in
"" | flatpak | pip) ;;
*) die "--channel takes flatpak or pip, not $CHANNEL" ;;
esac

BIN="$PREFIX/bin"
VENV="$PREFIX/share/libera"

# Does this command actually run? `--help` and not `--version`, because
# `--version` arrived after 0.1.1 and this script has to work against whatever
# the origin is serving, including the release before the one that added it.
# --payload-install is in the help of every version there has ever been.
runs() {
    text="$("$@" --help 2>&1 || :)"
    case "$text" in
    *--payload-install*) return 0 ;;
    esac
    printf '%s' "$text"
    return 1
}

# What landed, for the last line. `--version` names the application and the
# payload together where it exists; before 0.2.0 it did not, so the package
# metadata answers instead.
describe() {
    "$@" --version 2>/dev/null && return 0
    if [ -x "$VENV/bin/python" ]; then
        "$VENV/bin/python" -c \
            'import importlib.metadata as m; print("libera", m.version("libera"))'
        return 0
    fi
    say "libera (installed; this release is older than --version)"
}

# --- what machine is this ------------------------------------------------------

os="$(uname -s)"
machine="$(uname -m)"
case "$os" in
Darwin) os=macos ;;
Linux)  os=linux ;;
*) die "Libera Suite runs on Linux and macOS; this is $os." ;;
esac
case "$machine" in
arm64 | aarch64) arch=arm64 ;;
x86_64 | amd64)  arch=amd64 ;;
*) die "no build for $machine." ;;
esac

if [ "$os" = macos ] && [ "$arch" = amd64 ]; then
    die "Intel Macs are not built yet: there is no core-macos-x86_64, and no
       machine here to build one on. Apple Silicon works today."
fi

say "Libera Suite, on $os/$arch."

# --- Linux gets the Flatpak, because the Python package cannot bring GTK -------
#
# `pip install libera` puts the host in place and cannot install GTK, WebKitGTK
# or PyGObject, which are system packages. The Flatpak bundle carries the lot:
# the GNOME runtime supplies the toolkit and the payload is inside the bundle,
# so there is no second download and no version to keep in step.
#
# The fallback exists for a machine with no Flatpak and a system Python that
# already has PyGObject. It is the narrower path and it is checked, not assumed.

# Put the menu entry somewhere the session can already see.
#
# `flatpak install --user` exports the .desktop and the icon into
# $XDG_DATA_HOME/flatpak/exports/share, and a desktop shell finds that only if
# XDG_DATA_DIRS names it. /etc/profile.d/flatpak.sh arranges that at login, so
# a session older than the flatpak package does not have it -- and that is
# exactly the state this script sends people into, because when flatpak is
# missing it says "install flatpak, then re-run this" and they re-run it in the
# same shell. The install then works and nothing appears in the menu, which
# reads as a failed install. `flatpak run` also prints a paragraph about the
# search path, which reads as a broken one.
#
# $XDG_DATA_HOME itself is searched unconditionally, so a copy there is visible
# at once, with no logout and nothing for anyone to export. The app id is the
# filename, so when the session does catch up this overrides the exported entry
# rather than doubling it.
#
# Not fatal if it cannot be done: the application is installed either way, and
# `flatpak run` works. Say so and carry on.
mirror_desktop_entry() {
    exports="${XDG_DATA_HOME:-$HOME/.local/share}/flatpak/exports/share"
    data="${XDG_DATA_HOME:-$HOME/.local/share}"
    entry="$exports/applications/eu.liberasuite.Libera.desktop"

    if [ ! -f "$entry" ]; then
        say "    no exported desktop entry at $entry"
        say "    the menu entry will appear when you next log in"
        return 0
    fi

    mkdir -p "$data/applications" || return 0
    cp "$entry" "$data/applications/eu.liberasuite.Libera.desktop" || {
        say "    could not copy the desktop entry into $data/applications"
        return 0
    }

    # Every size flatpak exported, not just the scalable one: a shell that wants
    # 48x48 and finds only SVG shows a blank tile on some themes.
    for icon in "$exports"/icons/hicolor/*/apps/eu.liberasuite.Libera.*; do
        [ -f "$icon" ] || continue
        dir="$data/icons/hicolor/$(basename "$(dirname "$(dirname "$icon")")")/apps"
        mkdir -p "$dir" && cp "$icon" "$dir/" || :
    done

    # Assert on content, not on cp's exit status.
    [ -f "$data/applications/eu.liberasuite.Libera.desktop" ] || {
        say "    the desktop entry did not land in $data/applications"
        return 0
    }

    # So the shell notices without being restarted. Absent on a minimal system,
    # and its absence costs a refresh rather than the entry.
    if have update-desktop-database; then
        update-desktop-database "$data/applications" >/dev/null 2>&1 || :
    fi
    if have gtk-update-icon-cache; then
        gtk-update-icon-cache -qtf "$data/icons/hicolor" >/dev/null 2>&1 || :
    fi
    say "    menu entry: $data/applications/eu.liberasuite.Libera.desktop"
}

install_flatpak() {
    step "fetching the bundle"
    version="$(curl -fsSL "$ORIGIN/bundles/latest" 2>/dev/null | tr -d ' \n\r')" \
        || die "cannot reach $ORIGIN"
    case "$version" in
    "" | *[!0-9.]*) die "$ORIGIN/bundles/latest does not name a version ($version)" ;;
    esac

    bundle="${TMPDIR:-/tmp}/libera-$version-$arch.flatpak"
    url="$ORIGIN/bundles/libera-$version-$arch.flatpak"
    say "    $url"
    curl -fsSL -o "$bundle" "$url" || die "download failed: $url"

    # A CDN that answers a missing object with an HTML error page returns 200
    # for it, and `curl -f` is not enough on its own.
    size="$(wc -c < "$bundle" | tr -d ' ')"
    [ "$size" -gt 10000000 ] || die \
        "$url gave $size bytes, which is not a bundle.
       $(head -c 200 "$bundle")"

    step "installing"
    # The bundle carries the application and not the runtime, so Flathub has to
    # be a known remote before org.gnome.Platform can be resolved.
    flatpak remote-add --user --if-not-exists flathub \
        https://dl.flathub.org/repo/flathub.flatpakrepo >/dev/null 2>&1 || :

    # --reinstall when it is already there. Without it `flatpak install` of a
    # bundle refuses with "already installed" and exits non-zero, which this
    # script then reported as a fatal error -- for the ordinary case of running
    # the installer twice, or upgrading. A bundle carries no remote to update
    # from, so replacing it is the only way forward, and it is local and quick.
    if flatpak info "$APP_ID" >/dev/null 2>&1; then
        say "    $APP_ID is already installed; replacing it with $version"
        set -- --reinstall
    else
        set --
    fi
    flatpak install --user -y --noninteractive "$@" "$bundle" \
        || die "flatpak install failed"
    rm -f "$bundle"

    # Assert on content: ask the installed application what it is.
    output="$(runs flatpak run "$APP_ID")" || die \
        "flatpak install reported success and the application does not run:
       $output"

    step "desktop entry"
    mirror_desktop_entry

    step "done"
    say "    $(describe flatpak run "$APP_ID")"
    say ""
    # The menu first, because it is the one that works in the session that just
    # ran this: `flatpak run` in this same shell prints a paragraph about
    # XDG_DATA_DIRS that has nothing to do with anything being wrong.
    say "    open:   Libera Suite, in your applications menu"
    say "    run:    flatpak run $APP_ID"
    exit 0
}

# --- the Python package --------------------------------------------------------

find_python() {
    # 3.12 is the floor in pyproject.toml. Named versions first: `python3` on
    # Ubuntu 22.04 is 3.10, and that is the release this project's own glibc
    # floor targets, so the common case is a system Python that is too old and
    # a newer one installed beside it.
    for candidate in python3.14 python3.13 python3.12 python3; do
        have "$candidate" || continue
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' \
            2>/dev/null; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

install_pip() {
    python="$(find_python)" || die \
        "no Python 3.12 or newer on this machine.
       macOS:  brew install python@3.13
       Linux:  your distribution's python3.12 package, or
               curl -LsSf https://astral.sh/uv/install.sh | sh
               and then: uv tool install libera"

    say "    python  $python ($("$python" -c 'import platform;print(platform.python_version())'))"

    # --system-site-packages on Linux and not on macOS. On Linux the host needs
    # the distribution's PyGObject, which pip cannot supply; on macOS the
    # toolkit is pyobjc, which is wheels, and an isolated environment is the
    # cleaner one.
    if [ "$os" = linux ]; then
        venv_flags="--system-site-packages"
    else
        venv_flags=""
    fi

    step "installing libera into $VENV"
    rm -rf "$VENV"
    # shellcheck disable=SC2086  # venv_flags is one optional flag, deliberately unquoted
    "$python" -m venv $venv_flags "$VENV" || die \
        "could not create a virtualenv.
       On Debian and Ubuntu this usually means the python3-venv package."
    [ -x "$VENV/bin/python" ] || die "$VENV/bin/python is not there after venv"

    "$VENV/bin/python" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || :
    "$VENV/bin/python" -m pip install --quiet libera || die "pip install libera failed"

    [ -x "$VENV/bin/libera" ] || die \
        "pip reported success and $VENV/bin/libera is not there."

    step "linking $BIN/libera"
    mkdir -p "$BIN"
    ln -sf "$VENV/bin/libera" "$BIN/libera"

    # Assert on content. A symlink that exists says nothing about whether it
    # resolves to something that runs.
    output="$(runs "$BIN/libera")" || die \
        "pip reported success and $BIN/libera does not run:
       $output"
    say "    $(describe "$BIN/libera")"
}

install_payload() {
    if [ "$PAYLOAD" = no ]; then
        step "skipping the payload (--no-payload)"
        say "    fetch it later with:  libera --payload-install"
        return 0
    fi
    step "fetching the editor payload (about 120 MB)"
    "$BIN/libera" --payload-install || die \
        "the payload did not install.
       The command is there; run \`libera --payload-install\` to retry."
}

check_linux_toolkit() {
    # The one thing pip cannot fix, checked before it is needed rather than
    # discovered at the first blank window.
    "$VENV/bin/python" - <<'EOF' 2>/dev/null || return 1
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2  # noqa: F401  (import is the test)
EOF
}

# --- which path ----------------------------------------------------------------

if [ "$os" = linux ] && [ "$CHANNEL" != pip ]; then
    if have flatpak; then
        install_flatpak
    else
        say ""
        say "    No flatpak here, so this falls back to the Python package."
        say "    The Flatpak is the better Linux install: it brings its own GTK"
        say "    and WebKit, which pip cannot. To use it instead:"
        say ""
        say "        <your package manager> install flatpak, then re-run this."
        say ""
    fi
fi

install_pip

if [ "$os" = linux ] && ! check_linux_toolkit; then
    step "installed, and it cannot open a window yet"
    say "    The command works and the toolkit is missing. libera needs GTK 3,"
    say "    WebKitGTK 4.1 and PyGObject from your distribution:"
    say ""
    say "        Debian, Ubuntu:  sudo apt install python3-gi gir1.2-webkit2-4.1 \\"
    say "                             libgtk-3-0 gir1.2-gtk-3.0"
    say "        Fedora:          sudo dnf install python3-gobject webkit2gtk4.1"
    say ""
    say "    Or install flatpak and re-run this script, which needs none of them."
    say ""
    say "    Meanwhile \`libera --serve FILE\` opens the editor in your browser."
fi

install_payload

step "done"
say "    $(describe "$BIN/libera")"
say ""
case ":$PATH:" in
*":$BIN:"*) say "    run:  libera" ;;
*)
    say "    $BIN is not on your PATH. Either run it by path:"
    say "        $BIN/libera"
    say "    or add it:"
    # $BIN and not a hardcoded ~/.local/bin: with --prefix the advice would
    # otherwise name a directory nothing was installed into.
    say "        echo 'export PATH=\"$BIN:\$PATH\"' >> ~/.profile"
    ;;
esac
