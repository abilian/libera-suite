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

    vcvarsall="$vsdir\\VC\\Auxiliary\\Build\\vcvarsall.bat"
    echo "==> MSVC environment ($vsdir)"

    # `cmd //c`, with the doubled slash, or MSYS rewrites /c into a path.
    dump="$(mktemp)"
    cmd //c "call \"$vcvarsall\" x64 >nul && set" > "$dump" 2>/dev/null || {
        rm -f "$dump"
        echo "FATAL: vcvarsall.bat x64 failed." >&2
        exit 1
    }

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
    rm -f "$dump"

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
