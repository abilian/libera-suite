#!/bin/sh
# What this machine needs before it can build the payload, and how to get it.
#
#   build/toolchain.sh check     what is missing, and the line that installs it
#   build/toolchain.sh install   install it
#   build/toolchain.sh list      just the package names, one line
#
# `check` is a prerequisite of every payload target, because everything it
# looks for fails late and in somebody else's words:
#
#   The glib .pc files are V8's, because its gn args set use_sysroot=false and
#   it compiles against the host's glib. gn gen fails *after* depot_tools has
#   fetched V8 -- measured at 991 seconds on Fedora 43 -- and the message is
#   about pkg-config rather than about a package you have not installed.
#
#   llvm-ar is V8's too: is_clang=true makes gcc_toolchain.gni set `ar` to it,
#   so V8 compiles a hundred files and then fails at the first AR step with a
#   path and no package name anywhere in it.
#
#   The static C++ link is ICU's own namespace probe. Its Linux configure line
#   is CXXFLAGS=-static-libstdc++ -static-libgcc, that probe is the first thing
#   it links, and a missing libstdc++.a therefore surfaces as "Namespace
#   support is required to build ICU" -- a message with nothing about static
#   linking in it.
#
#   FindBin and IPC::Cmd are what OpenSSL's Configure reaches for. Debian's
#   perl has them; Fedora's minimal perl does not.
#
#   Bare `python` is what boost's nc-build.py runs to drive depinst.py, and
#   Ubuntu has shipped no /usr/bin/python since 20.04. The failure is a
#   FileNotFoundError out of the middle of a traceback that never names boost.
#
# **One table serves check and install**, so the thing that verifies and the
# thing that installs cannot disagree. That was the whole reason the first
# version of this was worth writing: the same list lived in the Dockerfile and
# nowhere else, so the container had it and a native build had nothing.
#
# Debian, Fedora and Arch have measured package names. openSUSE is a
# best-effort mapping; anything else gets the tool names and no command,
# because inventing a package name we have not checked is worse than saying we
# do not know.
#
# libtoolize rather than libtool: Debian's `libtool` package ships only
# libtoolize, /usr/bin/libtool lives in libtool-bin, and libtoolize is what
# autoreconf calls.
set -eu

# V8 8.9 does not compile under clang 16 or later: -Wenum-constexpr-conversion
# became an error, and src/base/bit-field.h:43 trips it in every
# torque-generated file -- about a hundred of them, a hundred files into a
# thirty-minute build. The container pins clang 14 for exactly this reason, so
# a native build has to be pointed at one too.
#
# Checked on Linux alone. The Mac builds V8 with whatever Xcode ships and does
# not hit this, which is a measurement rather than a theory: that build works.
V8_CLANG_MAX=15
# And on Linux arm64 nc-build.py demands 13 exactly, around its
# `targetarch == "arm64"` check. x86_64 has no such gate, only the ceiling.
V8_CLANG_ARM64=13

LINUX_TOOLS="gcc g++ make cmake ninja clang clang++ ld.lld llvm-ar git curl
             python python3 perl pkg-config autoconf automake libtoolize patch
             patchelf file xz zip unzip node npm"
# The Mac builds core natively and nothing else: no clang packages to install
# (Xcode brings them), no patchelf, no static libstdc++.
MACOS_TOOLS="clang clang++ make cmake ninja git curl python3 perl node npm"

# Windows compiles with MSVC, and `cl` is not on PATH until vcvarsall has run.
# V8's nc-build.py finds Visual Studio and runs vcvarsall itself, so the thing
# to check for is the installation, not the compiler: see check_visual_studio.
#
# perl and nasm are OpenSSL's, as they are everywhere, except that on Windows
# the assembler is a separate download rather than a package the compiler
# brings. python is spelt without the 3 here: the Windows installers and the
# Microsoft Store shim both provide `python`, and `python3` often does not
# exist at all.
WINDOWS_TOOLS="cmake ninja git curl python perl node npm nasm"

# ID first, then ID_LIKE, which is what a derivative sets.
family() {
    [ "$(uname -s)" = "Darwin" ] && { echo macos; return; }
    # Git Bash, MSYS2 and Cygwin all report their own uname; $OS is what
    # Windows itself sets, and it is there under every one of them.
    case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) echo windows; return ;;
    esac
    [ "${OS:-}" = "Windows_NT" ] && { echo windows; return; }
    id=$(sed -n 's/^ID=//p' /etc/os-release 2>/dev/null | tr -d '"')
    like=$(sed -n 's/^ID_LIKE=//p' /etc/os-release 2>/dev/null | tr -d '"')
    case " $id $like " in
    *" debian "* | *" ubuntu "*) echo debian ;;
    *" fedora "* | *" rhel "* | *" centos "*) echo fedora ;;
    *" arch "*) echo arch ;;
    *" suse "* | *" opensuse "*) echo suse ;;
    *) echo unknown ;;
    esac
}

# `PROGRAMFILES(X86)` has parentheses in its name, so no shell can expand it
# directly. env is how you read it.
PROGRAMFILES_X86="$(env | sed -n 's/^PROGRAMFILES(X86)=//p' | tr -d '\r')"
[ -n "$PROGRAMFILES_X86" ] || PROGRAMFILES_X86="/c/Program Files (x86)"

FAMILY=$(family)
case "$FAMILY" in
macos) TOOLS="$MACOS_TOOLS" ;;
windows) TOOLS="$WINDOWS_TOOLS" ;;
*) TOOLS="$LINUX_TOOLS" ;;
esac

# The package that provides each thing, where it is not the thing's own name.
# The keys are tool names, plus three capabilities the tool list cannot see:
# glib, static, perlmod.
package_for() {
    case "$1:$FAMILY" in
    # macOS installs three things; Xcode brings the rest, so they map to
    # nothing and drop out of the install line.
    cmake:macos | ninja:macos) echo "$1" ;;
    node:macos | npm:macos) echo "node" ;;
    *:macos) echo "" ;;
    # winget ids, which are what a fresh Windows has. cmake and ninja also come
    # with Visual Studio's C++ workload, so they are usually already there and
    # drop out of the install line before it is printed.
    cmake:windows) echo "Kitware.CMake" ;;
    ninja:windows) echo "Ninja-build.Ninja" ;;
    git:windows) echo "Git.Git" ;;
    curl:windows) echo "cURL.cURL" ;;
    python:windows) echo "Python.Python.3.12" ;;
    perl:windows) echo "StrawberryPerl.StrawberryPerl" ;;
    node:windows | npm:windows) echo "OpenJS.NodeJS.LTS" ;;
    nasm:windows) echo "NASM.NASM" ;;
    perlmod:windows) echo "StrawberryPerl.StrawberryPerl" ;;
    *:windows) echo "$1" ;;
    # Same name everywhere it is not listed below.
    gcc:debian | g++:debian | make:debian) echo "build-essential" ;;
    g++:fedora | g++:suse) echo "gcc-c++" ;;
    gcc:arch | g++:arch | make:arch) echo "base-devel" ;;
    ninja:debian | ninja:fedora) echo "ninja-build" ;;
    clang++:*) echo "clang" ;;
    ld.lld:*) echo "lld" ;;
    llvm-ar:*) echo "llvm" ;;
    python:debian) echo "python-is-python3" ;;
    python:fedora) echo "python-unversioned-command" ;;
    python:arch) echo "python" ;;
    perl:fedora) echo "perl-core" ;;
    pkg-config:fedora) echo "pkgconf-pkg-config" ;;
    pkg-config:arch) echo "pkgconf" ;;
    libtoolize:*) echo "libtool" ;;
    xz:debian) echo "xz-utils" ;;
    node:* | npm:*) echo "nodejs npm" ;;
    glib:debian) echo "libglib2.0-dev" ;;
    glib:fedora | glib:suse) echo "glib2-devel" ;;
    glib:arch) echo "glib2" ;;
    static:debian) echo "build-essential" ;;
    static:fedora) echo "libstdc++-static" ;;
    static:arch) echo "gcc" ;;
    perlmod:debian | perlmod:arch) echo "perl" ;;
    perlmod:fedora) echo "perl-core" ;;
    *) echo "$1" ;;
    esac
}

# Everything, whether or not it is installed. `list` prints this; `install`
# hands it to the package manager, which is cheaper than installing the subset
# that happens to be missing and leaves the machine in a state we have a name
# for.
all_packages() {
    for tool in $TOOLS; do package_for "$tool"; done
    # The three the tool list cannot see, and only where they are checked.
    case "$FAMILY" in macos | windows) return 0 ;; esac
    for cap in glib static perlmod; do package_for "$cap"; done
}

dedup() { printf '%s\n' "$@" | tr ' ' '\n' | sed '/^$/d' | sort -u | xargs; }

# $1 is "ask" or "yes": a line printed as advice lets the package manager
# prompt, and one this script is about to run has already been asked for by
# whoever typed `make toolchain-install`.
install_line() {
    consent=$1
    shift
    # No sudo as root, which is every container and some CI.
    sudo="sudo "
    [ "$(id -u)" = 0 ] && sudo=""
    case "$FAMILY:$consent" in
    debian:ask) echo "${sudo}apt install $*" ;;
    debian:yes) echo "${sudo}apt install -y $*" ;;
    fedora:ask) echo "${sudo}dnf install $*" ;;
    fedora:yes) echo "${sudo}dnf install -y $*" ;;
    arch:ask) echo "${sudo}pacman -S --needed $*" ;;
    arch:yes) echo "${sudo}pacman -S --needed --noconfirm $*" ;;
    suse:ask) echo "${sudo}zypper install $*" ;;
    suse:yes) echo "${sudo}zypper install -y $*" ;;
    macos:*) echo "brew install $*" ;;
    windows:ask) echo "winget install --exact $*" ;;
    windows:yes) echo "winget install --exact --silent --accept-package-agreements $*" ;;
    *) echo "install with your distribution's package manager: $*" ;;
    esac
}

# --- check -------------------------------------------------------------------

missing=""
packages=""

want() {
    # $1 is a key package_for knows, $2 the sentence saying what needs it.
    missing="$missing
  $2"
    packages="$packages $(package_for "$1")"
}

cmd_check() {
    for tool in $TOOLS; do
        command -v "$tool" >/dev/null 2>&1 || want "$tool" "$tool"
    done

    if command -v perl >/dev/null 2>&1; then
        if ! perl -MFindBin -MIPC::Cmd -e 'exit 0' 2>/dev/null; then
            if [ "$FAMILY" = windows ]; then
                # Measured on a GitHub runner: the perl that answers here is Git
                # for Windows' own, a trimmed MSYS2 build missing parts of core
                # that OpenSSL's Configure reaches for. Installing Strawberry
                # Perl is not enough on its own -- Git Bash puts /usr/bin ahead
                # of anything winget adds, so the trimmed one still wins. It has
                # to come first on PATH.
                want perlmod "perl at $(command -v perl), which has no FindBin or IPC::Cmd.
     That is Git for Windows' own perl. OpenSSL's Configure needs a full one,
     and it has to precede Git's on PATH:
       export PATH=/c/Strawberry/perl/bin:\$PATH"
            else
                want perlmod "perl without FindBin or IPC::Cmd, which OpenSSL's Configure needs"
            fi
        fi
    fi

    if [ "$FAMILY" = windows ]; then
        check_visual_studio || return 1
        check_cygwin || return 1
    fi

    # The three below are Linux's: the Mac builds ICU and V8 against what Xcode
    # ships, and has no static libstdc++ or glib to find.
    if [ "$FAMILY" != macos ] && [ "$FAMILY" != windows ]; then
        if command -v pkg-config >/dev/null 2>&1; then
            pkg-config --exists glib-2.0 gmodule-2.0 gobject-2.0 gthread-2.0 2>/dev/null ||
                want glib "the glib 2 .pc files, which V8's gn gen reads"
        fi

        if command -v g++ >/dev/null 2>&1; then
            probe=$(mktemp -d)
            printf 'namespace v { void f() {} }\nnamespace x = v;\nint main() { x::f(); return 0; }\n' \
                > "$probe/probe.cpp"
            g++ -static-libstdc++ -static-libgcc -std=c++11 -o "$probe/probe" \
                "$probe/probe.cpp" 2>/dev/null && "$probe/probe" ||
                want static "a static libstdc++, which ICU reports as a namespace error"
            rm -rf "$probe"
        fi
    fi

    # Listed by what to skip rather than by what to check, so adding a family
    # does not quietly opt it out of the V8 clang ceiling.
    case "$FAMILY" in
    macos | windows) ;;
    *)
        if command -v clang >/dev/null 2>&1; then
            check_clang_version || return 1
        fi
        ;;
    esac

    if [ -z "$missing" ]; then
        echo "    toolchain ok"
        return 0
    fi

    echo "FATAL: the toolchain is missing things the build needs:$missing" >&2
    echo >&2
    echo "  $(install_line ask "$(dedup "$packages")")" >&2
    [ "$FAMILY" = macos ] ||
        echo "  or: make toolchain-install" >&2
    return 1
}

# Visual Studio, not `cl`. The compiler is not on PATH until vcvarsall.bat has
# run, and V8's nc-build.py runs it itself -- it locates the installation, calls
# vcvarsall and captures the environment. So the thing that has to exist is the
# installation with the C++ workload in it, and vswhere is how Microsoft says to
# find one. It ships with any Visual Studio since 2017, at a fixed path.
#
# The Debugging Tools for Windows are checked with it because they are the
# Windows equivalent of the llvm-ar lesson: an optional feature of the Windows
# SDK, off by default, and gn fails on their absence long after the fetch.
check_visual_studio() {
    vswhere="$PROGRAMFILES_X86/Microsoft Visual Studio/Installer/vswhere.exe"
    [ -x "$vswhere" ] || {
        echo "FATAL: no Visual Studio found (vswhere.exe is not at the fixed path)." >&2
        echo "       Install Visual Studio 2022 with the 'Desktop development" >&2
        echo "       with C++' workload:" >&2
        echo "         winget install --exact Microsoft.VisualStudio.2022.Community" >&2
        return 1
    }
    vsdir="$("$vswhere" -latest -products '*' \
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 \
        -property installationPath 2>/dev/null | tr -d '\r')"
    [ -n "$vsdir" ] || {
        echo "FATAL: Visual Studio is installed without the C++ toolset." >&2
        echo "       Add 'Desktop development with C++' in the Visual Studio Installer." >&2
        return 1
    }
    echo "    Visual Studio: $vsdir"

    # cdb.exe is the one file gn looks for. Its absence is a Windows SDK
    # installed without its optional Debugging Tools, which is the default.
    if ! ls "$PROGRAMFILES_X86/Windows Kits/10/Debuggers/x64/cdb.exe" >/dev/null 2>&1; then
        echo "FATAL: the Windows SDK has no Debugging Tools for Windows." >&2
        echo "       gn needs them and says so only after V8 has been fetched." >&2
        echo "       Add them: Settings > Apps > Windows Software Development Kit" >&2
        echo "       > Modify > Change > tick 'Debugging Tools for Windows'." >&2
        return 1
    fi
    return 0
}

# ICU is built through Cygwin on Windows, and that is upstream's design rather
# than a workaround: icu/nc-build.bat hands icu/nc-build-cygwin.sh to Cygwin's
# bash, which runs `runConfigureICU Cygwin/MSVC` and then make. MSVC is still
# the compiler; Cygwin supplies the shell and the build system ICU's configure
# expects.
#
# Checked here because it fails five minutes in, after boost has built, and the
# message is about a path rather than about a thing to install.
#
# CYGWIN_ROOT moves it: nc-build.bat reads that before falling back to
# C:\cygwin64. `make` is checked separately because Cygwin's base install does
# not include it, and a Cygwin without make gets past the path test and fails
# in configure.
check_cygwin() {
    root="${CYGWIN_ROOT:-C:\\cygwin64}"
    root_u="$(cygpath -u "$root" 2>/dev/null || echo "$root")"

    if [ ! -x "$root_u/bin/bash.exe" ]; then
        echo "FATAL: no Cygwin at $root, which is where ICU is built." >&2
        echo "       Upstream builds ICU as Cygwin/MSVC: Cygwin supplies the" >&2
        echo "       shell and make, MSVC is still the compiler." >&2
        echo >&2
        echo "         winget install --exact Cygwin.Cygwin" >&2
        echo "       then add the 'make' package with Cygwin's setup, and if it" >&2
        echo "       is not at C:\\cygwin64 set CYGWIN_ROOT to where it is." >&2
        return 1
    fi
    if [ ! -x "$root_u/bin/make.exe" ]; then
        echo "FATAL: Cygwin at $root has no make." >&2
        echo "       ICU's configure runs it; a base Cygwin does not ship it." >&2
        echo "       Re-run Cygwin's setup and select the 'make' package." >&2
        return 1
    fi
    echo "    Cygwin: $root"
    return 0
}

# Its own function and its own message: no package name answers this, and the
# answer is usually "build it in the container" rather than "install a thing".
check_clang_version() {
    major=$(clang --version 2>/dev/null |
        sed -n 's/.*clang version \([0-9][0-9]*\).*/\1/p' | head -1)
    [ -n "$major" ] || return 0

    case "$(uname -m)" in
    aarch64 | arm64) wanted=$V8_CLANG_ARM64 ;;
    *) wanted="" ;;
    esac

    if [ -n "$wanted" ] && [ "$major" != "$wanted" ]; then
        echo "FATAL: clang $major, and V8 8.9 demands exactly $wanted on Linux arm64." >&2
        echo "       nc-build.py aborts on anything else, around its arm64 check." >&2
        echo >&2
        echo "  build it in the container instead:  make payload-container" >&2
        return 1
    fi

    if [ "$major" -gt "$V8_CLANG_MAX" ]; then
        echo "FATAL: clang $major is too new for V8 8.9, which does not compile" >&2
        echo "       under 16 or later: -Wenum-constexpr-conversion became an" >&2
        echo "       error, and src/base/bit-field.h:43 trips it in every" >&2
        echo "       torque-generated file -- a hundred of them, a hundred files" >&2
        echo "       into a thirty-minute build." >&2
        echo >&2
        echo "  the container pins clang 14 and is the supported path:" >&2
        echo "      make payload-container" >&2
        return 1
    fi
    return 0
}

cmd_list() { dedup "$(all_packages)"; }

cmd_install() {
    pkgs=$(cmd_list)
    line=$(install_line yes "$pkgs")
    case "$FAMILY" in
    unknown)
        echo "FATAL: this is not a distribution toolchain.sh has package names for." >&2
        echo "       It needs: $pkgs" >&2
        return 1
        ;;
    macos)
        echo "==> $line"
        echo "    and the Xcode command line tools: xcode-select --install"
        ;;
    *) echo "==> $line" ;;
    esac
    # sh -c so that the sudo and the shell quoting are the ones printed above,
    # rather than a second spelling of them that might differ.
    sh -c "$line"
}

case "${1:-check}" in
check) cmd_check ;;
install) cmd_install ;;
list) cmd_list ;;
*)
    echo "usage: toolchain.sh {check|install|list}" >&2
    exit 2
    ;;
esac
