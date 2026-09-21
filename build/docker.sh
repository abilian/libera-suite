#!/bin/sh
# Run the build for Linux, in a container -- the reproducible way to build a
# Linux payload, and the only way to build one from the Mac.
#
# On an Apple Silicon Mac, linux/amd64 runs under Rosetta rather than qemu, so
# an x86_64 build is slow-ish but perfectly usable -- and x86_64 is what Linux
# desktop users actually need. Override with ARCH=arm64 for a native build.
set -eu

# The whole file is read before any of it runs -- see build/release.sh for
# why, and for the measurement. A brace group plus the exit at the end.
{

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
# For $OUT: where exported artifacts land on *this* machine, by the same rule
# every other script in here uses. Nothing else from it is needed.
. "$HERE/common.sh"
MIRROR="${MIRROR:-$HOME/ghorg/euro-office}"

ARCH="${ARCH:-amd64}"
IMAGE="$(local_image "${IMAGE:-libera-build-linux-$ARCH}")"

# One base for both architectures, and a compiler that still differs.
#
# V8 is why the compiler differs: nc-build.py demands clang exactly 13 on Linux
# arm64, and Ubuntu has none after 22.04. See the head of
# build/docker/Dockerfile.
#
# The base stopped differing because of the other end of the same problem.
# amd64 built on noble, which put the shipped binaries at GLIBC 2.38 and
# GLIBCXX 3.4.32, and the x2t in core-linux-x86_64.tar.gz then refused to load
# on Ubuntu 22.04 and on Debian 12 -- measured in a clean container of each,
# and between them that is most of the Linux desktop. arm64 had been on jammy
# all along, for V8's sake, and the same test says it runs on both. So the
# constraint arm64 was stuck with is the portable choice, and taking it for
# amd64 costs a compiler version nobody was attached to.
UBUNTU_RELEASE=22.04
UBUNTU_CODENAME=jammy
# One digest for both: an OCI image index carrying linux/amd64 and
# linux/arm64/v8, checked with `docker buildx imagetools inspect`. The pin does
# not have to fork just because the compiler does.
BASE_DIGEST=sha256:829f6df217bcbae2b371026e81711d1a787c61b2967ad09d015063663ebafbf7
case "$ARCH" in
arm64) CLANG_VERSION=13 ;;
*)     CLANG_VERSION=14 ;;
esac
# The build tree goes on a real disk, beside the native one, and not in a named
# Docker volume. A volume lives on the VM's disk -- which on a Mac is the
# internal one -- and a full build is around 30 GB: the first attempt here died
# with "No space left on device" while $BUILD_ROOT had 295 GB free.
#
# $BUILD_ROOT is already chosen for this: an external case-sensitive volume on
# macOS, because V8's checkout needs case sensitivity and the internal disk has
# none. Each architecture gets its own subdirectory, so an amd64 and an arm64
# build can sit side by side without sharing an object tree.
#
# The old default was a volume, on the argument that thousands of small files
# are miserable across Docker Desktop's shared-folder layer. That is still true
# of Docker Desktop; it is much less true of OrbStack's virtiofs, and it is not
# a reason to run out of disk. `VOLUME=name` puts it back.
BUILD_DIR="${BUILD_DIR:-$BUILD_ROOT/linux-$ARCH}"
VOLUME="${VOLUME:-}"

# The payload version, read from the same file dist.sh writes it into, so the
# exported directory cannot be named something the installer will not look for.
payload_version() {
    sed -n 's/^version *= *//p' "$HERE/payload.version" | tr -d '"'
}

usage() {
    cat <<'USAGE'
build/docker.sh image [engine build args]   build (or rebuild) the build image
build/docker.sh versions                    what the image is pinned to
build/docker.sh build.sh fetch              any build/ script, with its arguments
build/docker.sh build.sh build
build/docker.sh payload.sh
build/docker.sh dist.sh --fonts core
build/docker.sh all                         fetch, build, payload, dist -- the lot
build/docker.sh export [DIR]                the built artifacts onto this machine
build/docker.sh shell                       poke around inside

  ARCH=arm64      build for arm64 instead of amd64
  V8_BUILD_JOBS=N how many compilers V8 runs at once (default: from memory)
  CORE_BUILD_JOBS=N the same for core itself (default: from the cgroup limit)
  DOCKER_MEMORY=8g ceiling for the container, so the host cannot be squeezed
  MIRROR=DIR      local clone to copy git objects from (optional, mounted ro)
  BUILD_DIR=DIR   where the build tree goes (default $BUILD_ROOT/linux-ARCH)
  VOLUME=NAME     a named Docker volume instead, on the VM's own disk
USAGE
}

[ $# -gt 0 ] || { usage; exit 2; }

build_image() {
    shift
    "$ENGINE" build --platform "linux/$ARCH" -t "$IMAGE" \
        --build-arg "UBUNTU_RELEASE=$UBUNTU_RELEASE" \
        --build-arg "UBUNTU_CODENAME=$UBUNTU_CODENAME" \
        --build-arg "BASE_DIGEST=$BASE_DIGEST" \
        --build-arg "CLANG_VERSION=$CLANG_VERSION" \
        -f "$HERE/docker/Dockerfile" "$@" "$HERE"
}

case "$1" in
image) build_image "$@"; exit $? ;;
esac

# An image already called libera-build-linux-amd64 is not necessarily the image
# this script now describes. The name carries the architecture and nothing else,
# so moving the base -- which is what happened when amd64 left noble for jammy --
# leaves a stale image under the right name. A build against it succeeds, takes
# its hours, and produces binaries with the old glibc floor; nothing downstream
# says a word, because every check that exists is about whether the build
# worked.
#
# The image records the base it was built on, so ask it.
if ! "$ENGINE" image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "==> building the image first ($UBUNTU_CODENAME, clang $CLANG_VERSION)"
    build_image image
else
    had="$("$ENGINE" run --rm --pull=never --platform "linux/$ARCH" "$IMAGE" \
        -c "sed -n 's/^base: *//p' /etc/libera-build-image.txt" 2>/dev/null || true)"
    if [ "$had" != "ubuntu:$UBUNTU_RELEASE@$BASE_DIGEST" ]; then
        echo "==> the $ARCH image was built on a different base; rebuilding it"
        echo "    it has: ${had:-an image too old to say}"
        echo "    wanted: ubuntu:$UBUNTU_RELEASE@$BASE_DIGEST"
        build_image image
    fi
fi

run() {
    cmd="$1"

    set -- --rm --pull=never \
        --platform "linux/$ARCH" \
        -v "$REPO:/repo" \
        -e BUILD_ROOT=/build \
        -w /repo

    # -t on a pipe makes docker fail outright, and -i without a terminal leaves
    # the build waiting on a stdin nobody is attached to; either one turns
    # `build/docker.sh all | tee log` into a puzzle.
    if [ -t 0 ] && [ -t 1 ]; then
        set -- "$@" -it
    fi

    # Fedora and RHEL: SELinux denies the container every file on a bind mount
    # out of $HOME. build.sh is 0755 on the host and "Permission denied" inside,
    # and not only to exec -- reading it fails too, which is what made this
    # script unusable on an SELinux box in the first place.
    #
    # The documented fix is a :z suffix on each mount, but that relabels the
    # host tree to container_file_t, and one of those trees is the upstream
    # mirror, mounted read-only precisely so that nothing in here writes to it.
    # Dropping the label check for one local build container leaves every host
    # label alone, and the container already has this repository mounted
    # read-write, so the confinement was not what was protecting anything.
    if [ -d /sys/fs/selinux ]; then
        set -- "$@" --security-opt label=disable
    fi

    if [ -n "$VOLUME" ]; then
        set -- "$@" -v "$VOLUME:/build"
    else
        mkdir -p "$BUILD_DIR"
        # A tree docker left behind is owned by real root on Linux, and
        # rootless podman writes as you -- so switching engines turns the build
        # into "Permission denied" forty lines in, after the whole fetch.
        # Docker itself does not care, because it is root either way.
        if [ ! -w "$BUILD_DIR" ]; then
            echo "FATAL: $BUILD_DIR is not writable by $(id -un)." >&2
            echo "       $(ls -ld "$BUILD_DIR" 2>/dev/null)" >&2
            echo >&2
            echo "       A build tree docker wrote is owned by root, and" >&2
            echo "       rootless podman writes as you. Remove it and let this" >&2
            echo "       run make it again:" >&2
            echo "           sudo rm -rf $BUILD_DIR" >&2
            exit 1
        fi
        set -- "$@" -v "$BUILD_DIR:/build"
    fi

    # Temporaries onto the same filesystem as the build tree. Without this they
    # go to the container's own /tmp, which on Docker Desktop and OrbStack is
    # the VM's disk -- and boost's bootstrap alone writes enough there to fill
    # it. When that happens the build dies ten minutes in with a page of
    # compiler errors whose first line is "fatal error: error writing to
    # /tmp/ccYezS3O.s: No space left on device", and nothing says the build tree
    # had room all along.
    set -- "$@" -e TMPDIR=/build/tmp

    # And tar must not restore ownership. Chromium's sysroot tarballs record
    # the uid and gid of whoever rolled them in 2019 -- 376730 and 89939,
    # "thomasanderson/primarygroup" -- and V8's install-sysroot.py untars one
    # as root from gclient's hooks. Real root may chown to any uid, so docker
    # never noticed. Rootless podman maps this user to container root plus
    # 65536 subordinate uids; 376730 is outside that range, chown fails with
    # EINVAL on every entry, and tar exits 2 with a page of "Cannot change
    # ownership" and a Python traceback under it that names neither uids nor
    # engines. GNU tar reads TAR_OPTIONS, so this costs no patch to V8, and
    # extracting as the build user is what a bind mount wanted anyway.
    set -- "$@" -e TAR_OPTIONS=--no-same-owner

    # build/README.md documents V8_BUILD_JOBS, and until now there was no way
    # to reach it from in here: build.sh computes a default from the memory it
    # can see, which is the container's view, and the machine running the
    # container is the one that runs out. Six clang processes under Rosetta on
    # a 16 GB Mac is enough to have the whole build killed from outside, with
    # nothing in the log to say why.
    if [ -n "${V8_BUILD_JOBS:-}" ]; then
        set -- "$@" -e "V8_BUILD_JOBS=$V8_BUILD_JOBS"
    fi
    if [ -n "${CORE_BUILD_JOBS:-}" ]; then
        set -- "$@" -e "CORE_BUILD_JOBS=$CORE_BUILD_JOBS"
    fi

    # A ceiling on the container, because without one the VM takes what the
    # build asks for and the *host* is what runs out. On a 16 GB Mac that shows
    # up as the build being killed from outside with nothing in the log -- and
    # a cgroup limit turns the same event into an OOM inside the container,
    # which says which compile died and can be answered with fewer jobs.
    if [ -n "${DOCKER_MEMORY:-}" ]; then
        set -- "$@" -m "$DOCKER_MEMORY"
    fi

    # The mirror is optional, and read-only when it is there: it exists so a
    # re-fetch copies objects from a local clone instead of pulling 1.5 GB, and
    # a container must never be able to rewrite the host's copy of upstream.
    #
    # Docker creates a missing bind-mount source as an empty root-owned
    # directory on the host rather than complaining, so an absent mirror would
    # otherwise mean a silent clone from GitHub, a stray ~/ghorg you did not
    # make, and -- because CORE_FONTS would point into it -- a font directory
    # that exists and is empty.
    if [ -d "$MIRROR" ]; then
        set -- "$@" -v "$MIRROR:/mirror:ro" -e MIRROR=/mirror
        if [ -d "$MIRROR/core-fonts" ]; then
            set -- "$@" -e CORE_FONTS=/mirror/core-fonts
        fi
    elif [ -z "${NO_MIRROR_WARNING:-}" ]; then
        # Only worth saying when something is about to fetch. `export` copies
        # what is already built and sets this.
        echo "==> no mirror at $MIRROR: cloning from upstream, and fonts come" >&2
        echo "    from the fetched core-fonts. Set MIRROR=DIR to use a clone." >&2
    fi

    # Ahead of the command, because every script in here assumes it exists and
    # `mktemp -d` fails with a path, not an explanation.
    #
    # And the write probe ahead of that, because the host-side check cannot see
    # this: on Linux the answer depends on how the engine maps uids into the
    # mount, and `mkdir -p` on a directory that already exists says nothing --
    # which is how a tree left by another engine gets through the outer check
    # and fails at the first real write, forty lines into a fetch.
    "$ENGINE" run "$@" "$IMAGE" -c "
        touch /build/.writable 2>/dev/null || {
            echo \"FATAL: /build is not writable from inside the container.\" >&2
            echo \"       as \$(id -un) (uid \$(id -u)):\" >&2
            ls -ld /build >&2
            echo >&2
            echo \"       A build tree another engine wrote is owned by a uid this\" >&2
            echo \"       one does not map to. Remove it and let the next run make it:\" >&2
            echo \"           sudo rm -rf $BUILD_DIR\" >&2
            exit 1
        }
        rm -f /build/.writable
        mkdir -p /build/tmp && { $cmd
}"
}

# How much room the build tree has, from inside, where the answer counts. V8,
# boost and ICU together want tens of gigabytes and the failure mode is a wall
# of compiler errors, so this is worth one container start.
#
# Not a hard stop: "enough" depends on what is already built, and a rebuild of
# the last stage needs almost nothing. Saying the number is the useful part.
check_space() {
    free=$(NO_MIRROR_WARNING=1 run "df -BG /build | awk 'NR==2 {print \$4+0}'" 2>/dev/null | tr -dc '0-9')
    [ -n "$free" ] || return 0
    echo "==> ${free} GB free on the build filesystem" >&2
    if [ "$free" -lt 30 ]; then
        echo "    A full build wants ~30 GB. BUILD_DIR=/path/on/a/big/disk moves" >&2
        echo "    the tree; it defaults to \$BUILD_ROOT/linux-ARCH, a real" >&2
        echo "    directory rather than the named volume it used to be." >&2
        echo "    Before moving anything, look at what is already dead:" >&2
        echo "      $ENGINE system df          volumes from before that default" >&2
        echo "                                changed are 100% reclaimable" >&2
        echo "      $ENGINE volume prune -f    the dead build trees" >&2
        echo "      $ENGINE builder prune -f   layer cache" >&2
        echo "    Keep \$BUILD_ROOT/src (re-cloning core alone is 1.5 GB) and" >&2
        echo "    the tree you are building into; its third_party is V8." >&2
    fi
}

case "$1" in
# Reads one file out of the image: no mounts, so no mirror warning either.
versions) "$ENGINE" run --rm --pull=never "$IMAGE" -c "cat /etc/libera-build-image.txt"; exit $? ;;
esac

# The built artifacts out of the volume and onto this machine, so the payload
# can be installed and the suite run against it. A tar pipe rather than
# `docker cp`/`podman cp`, because extraction runs as you: nothing lands owned
# by root.
#
# Diagnostics go to stderr and the destination to stdout, so a caller can read
# the path -- `make payload-install` does exactly that.
cmd_export() {
    dest="${1:-$OUT/dist}"
    ver="$(payload_version)"
    [ -n "$ver" ] || { echo "FATAL: no version in build/payload.version" >&2; exit 1; }

    if [ -z "$VOLUME" ]; then
        # Already on this machine: a bind-mounted build root needs no copy.
        out="$BUILD_DIR/out/dist/$ver"
    else
        # Ask first. Streaming a directory that is not there gives four lines
        # of tar complaint, and the pipeline's non-zero status kills this
        # script under set -e before the check below can say anything useful.
        NO_MIRROR_WARNING=1 run "[ -d /build/out/dist ]" >/dev/null 2>&1 || {
            echo "FATAL: nothing built in $VOLUME (no /build/out/dist)" >&2
            echo "       build it first: make payload-container" >&2
            exit 1
        }
        mkdir -p "$dest"
        echo "==> export $VOLUME:/build/out/dist -> $dest" >&2
        # `|| :` so a partial copy is reported by the content check below,
        # which knows what was supposed to arrive, rather than by tar.
        NO_MIRROR_WARNING=1 run "tar -C /build/out/dist -cf - ." | tar -C "$dest" -xf - || :
        out="$dest/$ver"
    fi

    # On content, not on the exit code of a pipeline whose status is tar's.
    [ -f "$out/manifest.json" ] || {
        echo "FATAL: no manifest.json in $out" >&2
        echo "       build the artifacts first: build/docker.sh dist.sh --fonts core" >&2
        exit 1
    }
    n="$(find "$out" -name '*.tar.gz' | wc -l | tr -d ' ')"
    [ "$n" -gt 0 ] || { echo "FATAL: no tarballs in $out" >&2; exit 1; }
    echo "    $n artifact(s) in $out" >&2

    echo "$out"
}

case "$1" in
export)   shift; cmd_export "${1:-}" ;;
shell)    run "exec /bin/bash" ;;
all)
    check_space
    run "set -e
        build/build.sh fetch
        build/build.sh configure
        build/build.sh build
        build/payload.sh
        build/dist.sh --fonts core
        build/smoke.sh"
    ;;
*.sh)
    script="$1"
    shift
    run "build/$script $*"
    ;;
*)
    echo "unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac

exit 0
}   # end of the read-it-all-first guard
