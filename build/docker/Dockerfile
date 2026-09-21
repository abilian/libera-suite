# Build environment for Euro-Office core on Linux.
#
# Nothing is copied in: build/docker.sh bind-mounts this repository and the
# local upstream mirror, and keeps $BUILD_ROOT in a named volume. V8 alone takes
# half an hour, so the volume is what makes a second run cheap.
#
# Everything that can drift is pinned, for the same reason build/pins.toml pins
# the sources by SHA: a patch queue is only meaningful against a fixed base, and
# "it built last week" has to still be true next year.
#
#   the base image     by digest, because a tag is a branch with better marketing
#   every apt package  by archive snapshot date (APT_SNAPSHOT)
#   Node               by version and SHA-256, from nodejs.org
#
# Moving the toolchain means bumping one of those three ARGs deliberately.
# Nothing else in here decides what gets installed.
#
# **One release, two compilers, and the reason is V8 at both ends.**
#
# Common/3dParty/v8/nc-build.py checks the compiler only on Linux arm64, and
# checks it exactly:
#
#     if nc.is_linux() and targetarch == "arm64":
#         if not version.startswith( "13." ): abort
#
# Ubuntu dropped clang-13 after 22.04, so an arm64 build has to be on jammy.
# amd64 has no such gate, only a ceiling: V8 8.9 stops compiling at clang 16.
#
# amd64 used to build on noble anyway, because that is upstream's own CI base
# (docker-ci/ds-base), and the binaries it produced needed GLIBC 2.38 and
# GLIBCXX 3.4.32. Measured in a clean container of each release, the shipped
# x2t then refused to load on Ubuntu 22.04 and on Debian 12, while the
# jammy-built arm64 core ran on both. So both architectures build on jammy now
# and only CLANG_VERSION differs; build/docker.sh picks it.
#
# Everything that can drift is still pinned per release, and the checks further
# down run on both, so a toolchain that is wrong for one of them fails here
# rather than forty minutes into a build.
ARG UBUNTU_RELEASE=22.04
ARG UBUNTU_CODENAME=jammy
ARG BASE_DIGEST=sha256:829f6df217bcbae2b371026e81711d1a787c61b2967ad09d015063663ebafbf7
FROM ubuntu:${UBUNTU_RELEASE}@${BASE_DIGEST}

# Re-declared because an ARG from before FROM is out of scope after it.
ARG UBUNTU_RELEASE
ARG UBUNTU_CODENAME
ARG BASE_DIGEST
ARG APT_SNAPSHOT=20260901T000000Z
ARG CLANG_VERSION=14
ARG NODE_VERSION=20.20.2
ARG NODE_SHA256_AMD64=df770b2a6f130ed8627c9782c988fda9669fa23898329a61a871e32f965e007d
ARG NODE_SHA256_ARM64=73093db209e4e9e09dd7d15a47aeaab1b74833830df03efa5f942a1122c5fa71

ENV DEBIAN_FRONTEND=noninteractive

# ca-certificates first, and from the stock archive: snapshot.ubuntu.com is
# https-only (plain http 301s to it) and the base image carries no CA bundle, so
# this one package cannot itself come from the snapshot. It is reinstalled from
# the snapshot below, so the finished image has nothing unpinned in it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates

# Then point apt at the archive as it stood on APT_SNAPSHOT, and check that it
# landed. `apt-get update` exits 0 when every index fails to download -- it
# falls back to whatever is already in /var/lib/apt/lists and mentions it in a
# W: line -- so an unreachable snapshot would otherwise install today's packages
# and look exactly like success.
#
# Two spellings, because the sources file changed shape between the releases:
# noble ships deb822 in /etc/apt/sources.list.d/ubuntu.sources, jammy the
# one-line format in /etc/apt/sources.list. Rewriting the wrong one succeeds
# and changes nothing, which is exactly the silent failure the check below is
# for.
#
# Both land on .../ubuntu/, including on arm64, where the stock sources point
# at ports.ubuntu.com/ubuntu-ports instead. snapshot.ubuntu.com has no
# ubuntu-ports -- it answers 401 -- and does not need one: its /ubuntu/ Release
# lists amd64 arm64 armhf i386 ppc64el riscv64 s390x. Rewriting ports to a
# ubuntu-ports path on that host is how this failed the first time.
RUN set -eu; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        sed -i -E "s|^URIs: .*|URIs: https://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}|" \
            /etc/apt/sources.list.d/ubuntu.sources; \
    else \
        sed -i -E "s|https?://[^ ]+/(ubuntu\|ubuntu-ports)/?|https://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/|g" \
            /etc/apt/sources.list; \
    fi; \
    apt-get update; \
    apt-cache policy | grep -q "snapshot.ubuntu.com/ubuntu" || { \
        echo "FATAL: apt is not resolving against snapshot ${APT_SNAPSHOT}." >&2; \
        echo "       Check that the date exists: https://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/dists/${UBUNTU_CODENAME}/Release" >&2; \
        exit 1; \
    }

# Three groups: the C++ toolchain, what the 3dParty scripts need to build boost,
# ICU, OpenSSL and V8 from source, and the tools the payload half wants. Keep
# this list and docs/src/develop/build.md's Linux section saying the same thing
# -- together they are the only statement anywhere of what a bare Linux box
# needs.
#
# clang and lld are not optional on Linux even though everything else builds
# with gcc: nc-build.py's check_prequisites aborts with "Tool not found: clang"
# before it compiles anything, its gn args set is_clang=true and use_lld=true,
# and it runs ninja with CC=clang CXX=clang++. build-essential provides neither.
#
# llvm on top of those two, for one file: is_clang=true makes gcc_toolchain.gni
# set ar to llvm-ar, which Ubuntu ships in `llvm` and not in `clang`. It fails
# at the first AR step, a hundred compiles in, with "/usr/bin/llvm-ar: not
# found" -- a path in the message and no package name anywhere.
#
# CLANG_VERSION is 14 and not noble's default 18, because V8 8.9 does not
# compile under clang 16 or later: -Wenum-constexpr-conversion became an error,
# and src/base/bit-field.h line 43 trips it in every torque-generated file.
# Clang is used for V8 and nothing else -- core is a gcc build -- so this pins
# one dependency's compiler rather than the image's. The unversioned names are
# what nc-build.py and gn look for, hence update-alternatives.
#
# Changing this invalidates V8's object tree, and ninja will not notice: it
# keys on the command line, and /usr/bin/clang++ is the same string either way.
# Delete $BUILD_ROOT/out/core/third_party/work/v8/v8/v8/out.gn by hand.
#
# build-essential covers libstdc++.a, which ICU links against statically and
# Fedora splits into a package of its own -- see the assertion below.
#
# libglib2.0-dev because V8's Linux gn args set use_sysroot=false
# (Common/3dParty/v8/nc-build.py, get_gn_args_file_content), so it compiles
# against the host's glib rather than a downloaded sysroot: //build/config/linux
# pkg_configs glib-2.0, gmodule-2.0, gobject-2.0 and gthread-2.0 unconditionally
# and gn gen fails outright without them.
#
# python-is-python3 because boost's nc-build.py runs bare `python` to drive
# boostdep's depinst.py (Common/3dParty/boost/nc-build.py, around line 52).
# Ubuntu has had no /usr/bin/python since 20.04; Fedora ships one in
# python-unversioned-command. Without it boost fails with FileNotFoundError on
# 'python' and nothing in the message says which script wanted it.
RUN apt-get install -y --no-install-recommends --reinstall \
        ca-certificates \
        build-essential \
        cmake \
        ninja-build \
        clang-${CLANG_VERSION} \
        lld-${CLANG_VERSION} \
        llvm-${CLANG_VERSION} \
        git \
        curl \
        pkg-config \
        libglib2.0-dev \
        file \
        python3 \
        python3-venv \
        python-is-python3 \
        autoconf \
        automake \
        libtool \
        perl \
        xz-utils \
        zip \
        unzip \
        lsb-release \
        patch \
        patchelf \
    && update-alternatives \
        --install /usr/bin/clang clang /usr/bin/clang-${CLANG_VERSION} 100 \
        --slave /usr/bin/clang++ clang++ /usr/bin/clang++-${CLANG_VERSION} \
        --slave /usr/bin/ld.lld ld.lld /usr/bin/ld.lld-${CLANG_VERSION} \
        --slave /usr/bin/llvm-ar llvm-ar /usr/bin/llvm-ar-${CLANG_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# Node from nodejs.org rather than NodeSource. `curl | bash` of setup_20.x adds
# an apt repository carrying whatever 20.x is current that week, so the same
# Dockerfile built twice gets two different Nodes -- and the setup script itself
# is unpinned code fetched at build time. A tarball is one version and one hash.
RUN set -eu; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) node_arch=x64;   node_sha="${NODE_SHA256_AMD64}" ;; \
        arm64) node_arch=arm64; node_sha="${NODE_SHA256_ARM64}" ;; \
        *) echo "FATAL: no pinned Node checksum for $arch" >&2; exit 1 ;; \
    esac; \
    tarball="node-v${NODE_VERSION}-linux-${node_arch}.tar.xz"; \
    curl -fsSLO "https://nodejs.org/dist/v${NODE_VERSION}/${tarball}"; \
    echo "${node_sha}  ${tarball}" | sha256sum -c -; \
    tar -xJf "$tarball" -C /usr/local --strip-components=1 \
        --exclude CHANGELOG.md --exclude LICENSE --exclude README.md; \
    rm -f "$tarball"

# git am makes a commit per patch, and applying the queue is the first thing the
# build does; without an identity it fails at the first commit and leaves the
# tree mid-am, which reads as a rejected patch rather than an unconfigured box.
# safe.directory because the repository arrives as a bind mount owned by the
# host user, which git otherwise refuses to touch.
RUN git config --system user.email "build@libera.invalid" \
    && git config --system user.name "Libera build" \
    && git config --system --add safe.directory '*'

# Prove the toolchain here, where it costs a second, instead of finding out
# twenty minutes into a build. What each check is for is in the script, which
# `build.sh configure` also runs on a native Linux build -- the image and the
# host need the same things, and two copies of that list is a list that drifts.
#
# The two assertions that stay here are the ones about *this image* rather than
# about a toolchain: node and clang are pinned by ARG, so they are checked
# against the ARG.
COPY toolchain.sh /usr/local/bin/toolchain.sh
RUN set -eu; \
    sh /usr/local/bin/toolchain.sh check; \
    [ "v${NODE_VERSION}" = "$(node --version)" ] || { \
        echo "FATAL: wanted node v${NODE_VERSION}, got $(node --version)" >&2; exit 1; }; \
    clang --version | grep -q "clang version ${CLANG_VERSION}\." || { \
        echo "FATAL: wanted clang ${CLANG_VERSION}, got $(clang --version | head -1)" >&2; exit 1; }

# What this image is, for the record. `build/docker.sh versions` prints the
# first; the second is every package and version, for when that is the question.
RUN set -eu; \
    { \
        echo "base:         ubuntu:${UBUNTU_RELEASE}@${BASE_DIGEST}"; \
        echo "arch:         $(dpkg --print-architecture)"; \
        echo "apt-snapshot: ${APT_SNAPSHOT}"; \
        echo "clang:        ${CLANG_VERSION} (V8 only; core builds with gcc)"; \
        echo "built:        $(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
        echo; \
        gcc --version | head -1; \
        g++ --version | head -1; \
        clang --version | head -1; \
        ld.lld --version | head -1; \
        cmake --version | head -1; \
        echo "ninja $(ninja --version)"; \
        python3 --version; \
        perl -e 'print "perl $^V\n"'; \
        echo "node $(node --version)"; \
        echo "npm $(npm --version)"; \
        echo "git $(git --version | awk '{print $3}')"; \
    } > /etc/libera-build-image.txt; \
    dpkg-query -W -f '${Package}=${Version}\n' | sort > /etc/libera-build-packages.txt; \
    cat /etc/libera-build-image.txt

WORKDIR /repo
ENTRYPOINT ["/bin/sh"]
