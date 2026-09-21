# Put the MSVC environment into this shell. Source it; Windows only.
#
# Two things go wrong without it, and the second is quieter than the first.
#
# build_3rdparty.py refuses outright: "MSVC environment is not set up: 'nmake'
# not found in PATH. Run 'vcvars64.bat' or use 'x64 Native Tools Command
# Prompt'." Fair enough, and easy to read.
#
# CMake does something worse. Under Git Bash with no MSVC on PATH it finds
# whatever else is there -- on a GitHub runner that is `C:/mingw64/bin/cc.exe`,
# GNU 15.2.0 -- and configures a GNU build with no complaint at all. It would
# have gone on failing later, somewhere that did not mention compilers.
#
# So the scripts arrange it rather than asking whoever runs them to remember an
# "x64 Native Tools Command Prompt". `nc-build.py` does the same thing for V8,
# in Python, which is where the recipe comes from: locate the installation with
# vswhere, run vcvarsall in cmd, and read back what it set.
#
# Only the variables the build needs are carried over. `set` also prints names
# no shell can export -- `PROGRAMFILES(X86)` has parentheses in it -- so
# re-exporting everything is not an option.

# Which MSVC to ask vcvarsall for, and why it is not simply "the newest".
#
# The third-party stack is 2021: boost 1.78, ICU 74, V8 8.9. boost's
# bootstrap.bat knows toolsets up to vc143 -- MSVC 14.3x, which is VS 2022 --
# and a runner's VS 18 gives cl 14.51, which it reports as "Unknown toolset:
# vcunk" and stops. V8 8.9 is from the same December and is no more likely to
# enjoy a compiler five years its junior: on Linux the same gap, clang 16
# against V8 8.9, does not compile at all.
#
# So pin it, the way build/toolchain.sh pins clang on Linux for exactly this
# reason. An installation usually carries several toolsets and vcvarsall will
# select one; MSVC_TOOLSET=14.4 or whatever else is there overrides.
MSVC_TOOLSET="${MSVC_TOOLSET:-14.3}"

msvc_env() {
    case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) ;;
    *) [ "${OS:-}" = "Windows_NT" ] || return 0 ;;
    esac

    # Already in a developer prompt, or already arranged by an earlier call.
    command -v cl.exe >/dev/null 2>&1 && return 0

    pf86="$(env | sed -n 's/^PROGRAMFILES(X86)=//p' | tr -d '\r')"
    [ -n "$pf86" ] || pf86="/c/Program Files (x86)"
    vswhere="$pf86/Microsoft Visual Studio/Installer/vswhere.exe"
    [ -x "$vswhere" ] || {
        echo "FATAL: no vswhere.exe, so no Visual Studio to set up." >&2
        echo "       build/toolchain.sh check says what to install." >&2
        exit 1
    }

    vsdir="$("$vswhere" -latest -products '*' \
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 \
        -property installationPath 2>/dev/null | tr -d '\r')"
    [ -n "$vsdir" ] || { echo "FATAL: Visual Studio has no C++ toolset." >&2; exit 1; }

    echo "==> MSVC environment ($vsdir, toolset $MSVC_TOOLSET)"

    # The VS 2017-2022 layout. A new major may have moved it, so look before
    # calling, and say what is there instead of guessing.
    vcvarsall="$vsdir\\VC\\Auxiliary\\Build\\vcvarsall.bat"
    vcvarsall_u="$(cygpath -u "$vcvarsall" 2>/dev/null || echo "$vcvarsall")"
    if [ ! -f "$vcvarsall_u" ]; then
        echo "FATAL: no vcvarsall.bat at" >&2
        echo "         $vcvarsall" >&2
        echo "       What that directory holds:" >&2
        ls -1 "$(dirname "$vcvarsall_u")" 2>/dev/null | sed 's/^/         /' >&2 ||
            echo "         nothing -- the directory is not there either" >&2
        exit 1
    fi

    # Through a .bat file rather than a quoted -c string. The path has spaces
    # and backslashes in it, and nesting quotes through bash into cmd is a
    # guessing game; a file has no quoting at all.
    work="$(mktemp -d)"
    {
        echo "@echo off"
        echo "call \"$vcvarsall\" x64 -vcvars_ver=$MSVC_TOOLSET"
        echo "if errorlevel 1 exit /b 1"
        echo "set"
    } > "$work/vcvars.bat"

    # `cmd //c`, with the doubled slash, or MSYS rewrites /c into a path.
    if ! cmd //c "$(cygpath -w "$work/vcvars.bat")" > "$work/out" 2> "$work/err"; then
        echo "FATAL: vcvarsall.bat x64 -vcvars_ver=$MSVC_TOOLSET failed. It said:" >&2
        cat "$work/out" "$work/err" 2>/dev/null | tail -30 | sed 's/^/    /' >&2
        echo "       Toolsets this installation has:" >&2
        ls -1 "$(cygpath -u "$vsdir")/VC/Tools/MSVC" 2>/dev/null |
            sed 's/^/         /' >&2 || echo "         none found" >&2
        echo "       MSVC_TOOLSET=<major.minor> picks another." >&2
        rm -rf "$work"
        exit 1
    fi
    dump="$work/out"

    # Case-insensitively, because Windows is about the case of these names and
    # the shell is not.
    for var in PATH INCLUDE LIB LIBPATH \
        VSINSTALLDIR VCINSTALLDIR VCToolsInstallDir \
        WindowsSdkDir WindowsSdkVerBinPath WindowsSDKVersion UCRTVersion \
        VSCMD_ARG_TGT_ARCH; do
        value="$(sed -n "s/^$var=//Ip" "$dump" | tr -d '\r' | head -1)"
        [ -n "$value" ] || continue
        if [ "$var" = PATH ]; then
            export PATH="$(cygpath -p -u "$value")"
        else
            export "$var=$value"
        fi
    done
    rm -rf "$work"

    command -v cl.exe >/dev/null 2>&1 || {
        echo "FATAL: vcvarsall ran and cl.exe is still not on PATH." >&2
        exit 1
    }

    # Named explicitly, because vcvarsall only *prepends*: mingw's cc.exe is
    # still on PATH behind it, and CMake asking for "a C compiler" is exactly
    # how this went wrong the first time.
    export CC=cl
    export CXX=cl
    echo "    cl: $(command -v cl.exe)"
}
