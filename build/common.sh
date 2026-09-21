# Shared by build.sh, payload.sh, dist.sh and smoke.sh. Not executable; source it.

# macOS: an external case-sensitive volume, because the internal disk is not
# one and V8's checkout needs it. Linux: anywhere, since every normal Linux
# filesystem is case-sensitive already. Override BUILD_ROOT on either.
case "$(uname -s)" in
Darwin) DEFAULT_BUILD_ROOT="/Volumes/T7-EXT-2T/euro-office-build" ;;
*)      DEFAULT_BUILD_ROOT="$HOME/euro-office-build" ;;
esac

BUILD_ROOT="${BUILD_ROOT:-$DEFAULT_BUILD_ROOT}"
SRC="$BUILD_ROOT/src"
OUT="$BUILD_ROOT/out"

# docker or podman, and on Linux the choice has a consequence beyond taste.
#
# A bind mount passes uids through unchanged there, so a container running as
# root writes a build tree you then cannot delete without sudo -- which is why
# $BUILD_ROOT/linux-amd64 comes out owned by root on Fedora and by you on a
# Mac, where the daemon lives in a VM that maps ownership across the share.
#
# Rootless podman maps container root to your own uid through a user
# namespace, so the same build writes files you own, with no --user and no
# HOME to arrange. Fedora ships it as the default engine anyway.
#
# Everything these scripts ask of an engine -- build, run, image inspect,
# volume rm -- is spelt the same in both, so the preference costs nothing and
# follows the consequence above: podman first on Linux, docker first on macOS.
#
# On Linux that is the difference between a build tree you own and one that
# wants sudo to delete, and the distributions shipping podman make it their
# default anyway. On macOS docker is what people have, its VM maps ownership
# across the share for you, and podman would want a VM of its own. ENGINE=
# overrides either way.
#
# Switching engines on a tree the other one built is the thing to know: its
# files carry uids this engine cannot write, and the build says so from inside
# the container rather than forty lines into a fetch. See notes/08-build.md.
if [ -z "${ENGINE:-}" ]; then
    case "$(uname -s)" in
    Darwin) engine_order="docker podman" ;;
    *)      engine_order="podman docker" ;;
    esac
    ENGINE=docker  # with neither installed, the failure names the common one
    for engine_try in $engine_order; do
        if command -v "$engine_try" >/dev/null 2>&1; then ENGINE="$engine_try"; break; fi
    done
fi

# Does this engine need arranging before a container writes files you own?
#
# Docker runs as real root and a bind mount passes uids through unchanged, so
# what it writes into the repository belongs to root unless it is told
# otherwise -- `--user` on the way in, or a chown on the way out.
#
# Rootless podman has already arranged it: container root *is* this uid. Saying
# it again is not merely redundant, it is the bug. `--user 1001` asks for
# *container* 1001, which maps to a subordinate host uid owning nothing, and
# pip then fails with EACCES writing into a directory it read a line earlier.
# A chown to 1001 hands the finished artifacts to that same uid, where the host
# can no longer delete them.
#
# Only podman answers yes: an engine nobody here has heard of gets docker's
# arrangement, which is the one that assumes nothing.
engine_writes_as_you() { [ "$ENGINE" = podman ]; }

# An image these scripts built themselves, named the way the engine wants.
#
# Docker takes a bare name and silently reads it as docker.io/library/<name>.
# Podman refuses to guess: an unqualified name sends it to the
# unqualified-search-registries list and, interactively, to a menu --
#
#     ? Please select an image:
#       > registry.fedoraproject.org/libera-build-linux-amd64:latest
#         registry.access.redhat.com/libera-build-linux-amd64:latest
#         docker.io/library/libera-build-linux-amd64:latest
#
# -- none of which can be right for an image built on this machine a moment
# ago. Podman stores those under localhost/, so that is the qualification.
# Docker would read the same prefix as a registry host called localhost, so it
# is podman's alone. A name that already carries a registry is left as it is.
local_image() {
    case "$ENGINE:$1" in
    podman:*/*) echo "$1" ;;
    podman:*) echo "localhost/$1" ;;
    *) echo "$1" ;;
    esac
}

# /proc/meminfo reports the *host's* memory inside a container -- the cgroup
# limit is invisible to it -- so a 64 GB builder running `docker run -m 8g`
# reads 64 and starts thirty compilers in an 8 GB box. Ask the cgroup first
# and fall back to meminfo, which is right when there is no limit.
usable_gb() {
    # Darwin has no /proc: without this the awk below fails and the caller
    # prints "from  GB usable" with an awk error beside it, which is what the
    # native core build has been doing.
    if [ "$(uname -s)" = "Darwin" ]; then
        sysctl -n hw.memsize | awk '{print int($1 / 1073741824)}'
        return
    fi
    physical="$(awk '/MemTotal/ {print int($2 / 1048576)}' /proc/meminfo)"
    limit=""
    for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory/memory.limit_in_bytes; do
        if [ -r "$f" ]; then
            v="$(cat "$f")"
            # "max" (v2) and a 64-bit sentinel (v1) both mean unlimited.
            case "$v" in
            max | 9223372036854771712 | 18446744073709551615) continue ;;
            esac
            limit=$(( v / 1073741824 ))
            break
        fi
    done

    # The *lesser* of the two, which is the only one that is a fact. A cgroup
    # limit above physical memory grants nothing -- `docker run -m 8g` on a
    # 4 GB machine still has 4 GB -- and believing it is how a build starts
    # four compilers on a box that fits one and dies with
    #
    #     c++: fatal error: Killed signal terminated program cc1plus
    #
    # which is what happened on a 4 GB arm64 builder.
    if [ -n "$limit" ] && [ "$limit" -lt "$physical" ]; then
        echo "$limit"
    else
        echo "$physical"
    fi
}

# One compiler per 2 GB, capped at the core count. The divisor is not folklore:
# the OOXML and OdfFile translation units instantiate enough templates to pass
# 1.5 GB each, which is why this is the number that decides whether a build
# ends in "Killed signal terminated program cc1plus".
build_jobs() {
    [ "$(uname -s)" = "Darwin" ] && { echo 4; return; }
    gb="$(usable_gb)"
    cpus=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)
    # A gigabyte off the top for the kernel, the shell and everything else on
    # the machine, then one compiler per two. Without the reservation a 4 GB
    # box computes two jobs and has room for one.
    jobs=$(( (gb - 1) / 2 ))
    [ "$jobs" -gt "$cpus" ] && jobs="$cpus"
    [ "$jobs" -lt 1 ] && jobs=1
    echo "$jobs"
}

# Run one of the built binaries. They link ~30 libraries that sit beside them,
# and on Linux nothing in the binary says where those are: DT_NEEDED records a
# soname, never a path. The host sets the same variable before running x2t --
# see convert.py -- so this is the build-side half of the same arrangement.
# APPLICATION_NAME is what core stamps into the <Application> field of every
# document it writes. It defaults to ONLYOFFICE, so anything that runs x2t has
# to set it -- the host does the same in convert.py.
built() {
    exe="$1"
    shift
    APPLICATION_NAME="${APPLICATION_NAME:-Libera Suite}" \
    DYLD_LIBRARY_PATH="$OUT/core/bin" LD_LIBRARY_PATH="$OUT/core/bin" \
        "$OUT/core/bin/$exe" "$@"
}

# core-fonts is a pinned repo, but fetching it costs 248 MB and a clone is
# usually already lying around. Prefer whichever exists.
resolve_core_fonts() {
    for d in "${CORE_FONTS:-}" "$SRC/core-fonts" "$HOME/ghorg/euro-office/core-fonts"; do
        if [ -n "$d" ] && [ -d "$d" ]; then
            CORE_FONTS="$d"
            return 0
        fi
    done
    echo "FATAL: no core-fonts checkout (set CORE_FONTS)" >&2
    exit 1
}

# allfontsgen writes two different AllFonts.js and they are not interchangeable:
#
#   --allfonts-web  lists numeric ids ("000", "001") that the browser fetches
#                   over HTTP from the web font directory
#   --allfonts      lists absolute filesystem paths, which is what doctrenderer
#                   needs -- point DoctRenderer.config's <allfonts> at this one
#                   or font loading fails inside V8
#
# It also treats an existing AllFonts.js as an up-to-date cache and exits 0
# without writing anything, so callers must clear the outputs first.
generate_fonts() {
    payload="$1"
    resolve_core_fonts
    rm -rf "$payload/fonts" "$payload/AllFonts.js" \
           "$payload/sdkjs/common/AllFonts.js" "$payload/sdkjs/common/font_selection.bin"
    mkdir -p "$payload/fonts" "$payload/sdkjs/common/Images"

    echo "==> allfontsgen ($CORE_FONTS)"
    built tools/allfontsgen \
        --input="$CORE_FONTS" \
        --allfonts-web="$payload/sdkjs/common/AllFonts.js" \
        --allfonts="$payload/AllFonts.js" \
        --images="$payload/sdkjs/common/Images" \
        --selection="$payload/sdkjs/common/font_selection.bin" \
        --output-web="$payload/fonts"

    # The count, not the exit code. allfontsgen exits 0 having found nothing
    # when its directory walk has no live branch for the platform, and writes a
    # well-formed AllFonts.js holding zero fonts -- an editor built on that
    # renders every glyph as a box, and nothing else anywhere says so.
    n="$(ls "$payload/fonts" | wc -l | tr -d ' ')"
    [ "$n" -gt 100 ] || { echo "FATAL: allfontsgen produced $n web fonts" >&2; exit 1; }
    echo "    $n web fonts"
}

# Make the built binaries relocatable, and prove it.
#
# Dispatch by platform: the two linkers get this wrong in different ways, and
# only one of them is fatal.
relocate() {
    case "$(uname -s)" in
    Darwin) relocate_macos "$1" ;;
    Linux)  relocate_linux "$1" ;;
    esac
}

# Linux does not have the macOS problem: DT_NEEDED records a soname, never a
# path, so a moved payload still finds its libraries through LD_LIBRARY_PATH --
# which both the build (see `built`) and the host (convert.py) set.
#
# A recorded RPATH/RUNPATH is still worth knowing about, because it is searched
# ahead of LD_LIBRARY_PATH: on a machine that happens to have the build
# directory, the payload would silently load libraries from it. Report rather
# than fail, and strip them when patchelf is there to do it.
relocate_linux() {
    dir="$1"
    command -v readelf >/dev/null 2>&1 || {
        echo "    relocatable: no readelf, not checked"
        return 0
    }
    # An `if` with no else, so the loop ends with status 0 even when the last
    # file is clean -- the same trap relocate_macos documents below: a `&&
    # echo` as the last command makes the substitution exit non-zero, which
    # set -e then treats as a failed build.
    bad="$(find "$dir" -type f | while read -r f; do
        n="$(readelf -d "$f" 2>/dev/null | grep -cE "R(UN)?PATH.*$BUILD_ROOT" || true)"
        if [ "$n" -gt 0 ]; then
            echo "$f"
        fi
    done)"
    if [ -z "$bad" ]; then
        echo "    relocatable: no build-tree RPATHs"
        return 0
    fi
    n="$(echo "$bad" | wc -l | tr -d " ")"
    if command -v patchelf >/dev/null 2>&1; then
        echo "$bad" | while read -r f; do patchelf --set-rpath '$ORIGIN' "$f"; done
        echo "    relocatable: rewrote $n RPATH(s) to \$ORIGIN"
    else
        echo "    WARNING: $n binaries record a build-tree RPATH." >&2
        echo "             Harmless here; install patchelf to strip them." >&2
    fi
}

#
# Our own libraries link each other through @rpath, but ICU is built by its own
# configure, which stamps an absolute -install_name of $libdir/libicuuc.74.dylib.
# Every consumer records that path, so the payload runs where it was built and
# nowhere else: moving it gives "dyld: Library not loaded". Copies of the ICU
# dylibs are already shipped alongside the binaries -- only the recorded paths
# are wrong.
#
# This rewrites them the way macdeployqt and delocate do, and then asserts that
# nothing anywhere still points into the build tree. The assertion is the point:
# it catches the next third-party library that does the same thing.
# Every Mach-O under dir, subdirectories included. Listing binaries by name
# missed tools/allfontsgen, which the installer runs -- so the artifact shipped
# with absolute ICU paths and would have died on any machine but this one.
macho_files() {
    find "$1" -type f -perm -u+r 2>/dev/null | while read -r f; do
        case "$(file -b "$f" 2>/dev/null)" in
        *Mach-O*) echo "$f" ;;
        esac
    done
}

relocate_macos() {
    dir="$1"
    [ "$(uname -s)" = "Darwin" ] || return 0

    macho_files "$dir" | while read -r f; do

        # A library's own id, when it names a build path rather than @rpath.
        case "$(otool -D "$f" 2>/dev/null | tail -1)" in
        "$BUILD_ROOT"/*) install_name_tool -id "@rpath/$(basename "$f")" "$f" 2>/dev/null || true ;;
        esac

        # Then each dependency recorded as an absolute build path.
        otool -L "$f" 2>/dev/null | sed -n '2,$p' | awk '{print $1}' |
        while read -r dep; do
            case "$dep" in
            "$BUILD_ROOT"/*)
                base="$(basename "$dep")"
                # Only if we actually ship that library beside the binary.
                if [ -f "$dir/$base" ]; then
                    install_name_tool -change "$dep" "@rpath/$base" "$f" 2>/dev/null || true
                fi
                ;;
            esac
        done
    done

    # `[ ... ] && echo` as the loop's last command makes the substitution exit
    # non-zero when the final file is clean, which set -e then treats as failure.
    bad="$(macho_files "$dir" | while read -r f; do
        n="$(otool -L "$f" 2>/dev/null | sed -n '2,$p' | grep -c "$BUILD_ROOT" || true)"
        if [ "$n" -gt 0 ]; then
            echo "$f ($n)"
        fi
    done)"
    if [ -n "$bad" ]; then
        echo "FATAL: build-tree references remain:" >&2
        echo "$bad" | sed 's/^/  /' >&2
        exit 1
    fi
    echo "    relocatable: no build-tree paths in $(macho_files "$dir" | wc -l | tr -d ' ') binaries"
}
