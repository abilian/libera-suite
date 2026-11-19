# Build environment for Euro-Office core on Linux.
#
# Nothing is copied in: build/src/libera_build/buildbox.py bind-mounts this repository and the
# local upstream mirror, and keeps $BUILD_ROOT in a named volume. V8 alone takes
# half an hour, so the volume is what makes a second run cheap.
#
# Everything that can drift is pinned, for the same reason build/upstream/pins.toml pins
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
# **One base for both architectures: jammy, for the glibc it ships against.**
#
# amd64 used to build on noble, because that is upstream's own CI base
# (docker-ci/ds-base), and the binaries it produced needed GLIBC 2.38 and
# GLIBCXX 3.4.32. Measured in a clean container of each release, the shipped
# x2t then refused to load on Ubuntu 22.04 and on Debian 12. So both
# architectures build on jammy.
#
# **V8's compiler comes from LLVM, not from Ubuntu.** V8 14.6, which
# Euro-Office's main builds since 2026-11, is compiled with clang 21 upstream,
# and jammy's archive stops at clang 15. apt.llvm.org has it but keeps only its
# latest build, which cannot be pinned; LLVM's release tarballs can, by version
# and SHA-256, as Node is below. build/src/libera_build/buildbox.py holds both
# and passes them in, since it also needs the version to tell a stale image.
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
ARG LLVM_VERSION
ARG LLVM_SHA256_AMD64
ARG LLVM_SHA256_ARM64
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
# clang, lld and llvm-ar for V8 come from the LLVM tarball below; lld links
# against libxml2, which jammy has, hence libxml2 here.
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
        libxml2 \
    && rm -rf /var/lib/apt/lists/*

# clang, lld and llvm-ar for V8, and nothing else: core is a gcc build. They
# are not optional even so: nc-build.py aborts with "Tool not found: clang"
# before it compiles anything, its gn args set is_clang=true and use_lld=true,
# and is_clang makes gcc_toolchain.gni set ar to llvm-ar. It also looks for
# compiler-rt's builtins (clang -print-libgcc-file-name --rtlib=compiler-rt)
# before building. The tarball is 1.8 GB and 2.6 GB unpacked, most of it tools
# V8 never runs, so only these are taken out of it; the unversioned names are
# what nc-build.py and gn look for.
#
# Changing LLVM_VERSION invalidates V8's object tree, and ninja will not notice:
# it keys on the command line, and /usr/local/bin/clang++ is the same string
# either way. Delete $BUILD_ROOT/out/core/third_party/work/v8/v8/v8/out.gn.
RUN set -eu; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) llvm_arch=X64;   llvm_sha="${LLVM_SHA256_AMD64}" ;; \
        arm64) llvm_arch=ARM64; llvm_sha="${LLVM_SHA256_ARM64}" ;; \
        *) echo "FATAL: no pinned LLVM checksum for $arch" >&2; exit 1 ;; \
    esac; \
    tarball="LLVM-${LLVM_VERSION}-Linux-${llvm_arch}.tar.xz"; \
    curl -fsSLO "https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VERSION}/${tarball}"; \
    echo "${llvm_sha}  ${tarball}" | sha256sum -c -; \
    major="${LLVM_VERSION%%.*}"; \
    mkdir -p /opt/llvm; \
    tar -xJf "$tarball" -C /opt/llvm --strip-components=1 --wildcards \
        "*/bin/clang" "*/bin/clang++" "*/bin/clang-${major}" \
        "*/bin/lld" "*/bin/ld.lld" "*/bin/llvm-ar" "*/bin/llvm-ranlib" "*/bin/llvm-nm" \
        "*/lib/clang/${major}/include" "*/lib/clang/${major}/lib/*/libclang_rt.builtins.a"; \
    rm -f "$tarball"; \
    for tool in clang clang++ ld.lld lld llvm-ar llvm-ranlib llvm-nm; do \
        ln -s "/opt/llvm/bin/$tool" "/usr/local/bin/$tool"; \
    done

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
# common.sh beside it, because toolchain.sh sources it from its own directory.
COPY engine/toolchain.sh engine/common.sh /usr/local/bin/
RUN set -eu; \
    sh /usr/local/bin/toolchain.sh check; \
    [ "v${NODE_VERSION}" = "$(node --version)" ] || { \
        echo "FATAL: wanted node v${NODE_VERSION}, got $(node --version)" >&2; exit 1; }; \
    clang --version | grep -q "clang version ${LLVM_VERSION} " || { \
        echo "FATAL: wanted clang ${LLVM_VERSION}, got $(clang --version | head -1)" >&2; exit 1; }; \
    ld.lld --version > /dev/null

# What this image is, for the record. `lb container versions payload` prints the
# first; the second is every package and version, for when that is the question.
RUN set -eu; \
    { \
        echo "base:         ubuntu:${UBUNTU_RELEASE}@${BASE_DIGEST}"; \
        echo "arch:         $(dpkg --print-architecture)"; \
        echo "apt-snapshot: ${APT_SNAPSHOT}"; \
        echo "identity:     ubuntu:${UBUNTU_RELEASE}@${BASE_DIGEST} llvm ${LLVM_VERSION}"; \
        echo "llvm:         ${LLVM_VERSION}, LLVM's release tarball (V8 only; core builds with gcc)"; \
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
