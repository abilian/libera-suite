#!/bin/sh
# Build the Flatpak, in a container.
#
# All of it runs here, Mac included: flatpak-builder is an ordinary Linux
# program, what it needs is user namespaces and /dev/fuse, and Docker grants
# both. The bundle is built, installed and run in here -- `check` asks the
# application whether it could open a window, `smoke` has it convert a document
# with the payload.
#
# The window itself is build/test-linux.sh's job: Xvfb, GTK and WebKitGTK are
# in that image and not this one, because they are a test dependency and
# nothing the Flatpak build needs.
#
#   build/flatpak.sh image      build (or rebuild) the builder image
#   build/flatpak.sh versions   what that image is pinned to
#   build/flatpak.sh wheels     just the offline wheel set
#   build/flatpak.sh build      wheels, then flatpak-builder, then the bundle
#   build/flatpak.sh check      install the built bundle and run --diagnose in it
#   build/flatpak.sh smoke      convert a document with the payload in the bundle
#   build/flatpak.sh shell      poke around inside, with flatpak on $PATH
#   build/flatpak.sh clean      drop the runtime cache (~4 GB per architecture)
#
#   ARCH=amd64   build for x86_64 instead of this machine's architecture
#
# On an Apple Silicon Mac ARCH=arm64 is native and ARCH=amd64 runs under
# Rosetta. Both work; only the first is quick.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
# common.sh for $OUT, which is where the release artifacts are: the bundle
# carries the payload now, so the build needs them staged beside the manifest
# before flatpak-builder runs. See cmd_payload_stage.
. "$HERE/common.sh"
OUT_DIST="$OUT/dist"

case "$(uname -m)" in
arm64 | aarch64) HOST_ARCH=arm64 ;;
*) HOST_ARCH=amd64 ;;
esac
ARCH="${ARCH:-$HOST_ARCH}"
# docker's spelling of the architecture, and the manifest's. They differ, and
# the artifacts are named in the manifest's.
[ "$ARCH" = "arm64" ] && PLATFORM=linux-arm64 || PLATFORM=linux-x86_64
IMAGE="$(local_image "${IMAGE:-libera-flatpak-$ARCH}")"
# The GNOME runtime and SDK together are several gigabytes. Re-downloading them
# per build would make this unusable, so /var/lib/flatpak lives in a volume.
#
# A named volume and not a directory on $BUILD_ROOT, which is where everything
# else large in this project now goes. flatpak's store is an ostree repo and
# ostree keeps its metadata in user xattrs -- and a macOS volume bind-mounted
# through virtiofs does not have them:
#
#     hardlink: ok
#     user xattr: NO
#
# So this one is stuck on the VM's disk. `build/flatpak.sh clean` drops it,
# which is worth doing after a release: about 4 GB per architecture.
VOLUME="${VOLUME:-libera-flatpak-$ARCH}"

APP_ID=eu.liberasuite.Libera
PAYLOAD_VERSION="$(sed -n 's/^version *= *//p' "$HERE/payload.version" | tr -d '"')"
DIST="${DIST:-$OUT_DIST/$PAYLOAD_VERSION}"
WORK="$HERE/flatpak"
VERSION="$(sed -n 's/^version *= *//p' "$REPO/pyproject.toml" | head -1 | tr -d '"')"
BUNDLE="libera-$VERSION-$ARCH.flatpak"
# Beside the .app, in build/out, and not in $OUT/dist: that directory is a
# *payload* version namespace -- 0.1 today, while the application is 0.1.0 --
# and two adjacent directories differing by a trailing .0 is a trap, not a
# layout. The Flatpak carries the application, so it goes where the .app goes.
DEST="$HERE/out"

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }

[ $# -gt 0 ] || { sed -n '3,19p' "$0" | sed 's/^#\{1,\} \{0,1\}//'; exit 2; }

build_image() { "$ENGINE" build --platform "linux/$ARCH" -t "$IMAGE" "$WORK"; }

case "$1" in
image) build_image; exit $? ;;
clean)
    "$ENGINE" volume rm "$VOLUME" >/dev/null 2>&1 \
        && say "removed $VOLUME" || say "$VOLUME was not there"
    exit 0
    ;;
esac

"$ENGINE" image inspect "$IMAGE" >/dev/null 2>&1 || {
    step "building the builder image first"
    build_image
}

# --privileged and /dev/fuse, because flatpak-builder runs each module inside a
# bubblewrap user namespace and flatpak's installer mounts revokefs. Docker
# Desktop's VM will not hand those to an unprivileged container. Nothing is
# trusted less for it: this container has the repository read-write already, so
# the confinement was not what was protecting anything -- the same argument
# build/docker.sh makes about disabling SELinux labels for it.
run() {
    set -- --rm --pull=never \
        --platform "linux/$ARCH" \
        --privileged --device /dev/fuse \
        -v "$VOLUME:/var/lib/flatpak" \
        -v "$REPO:/repo" \
        -w /repo \
        "$@"

    # Same reason as build/docker.sh: -t on a pipe makes docker fail outright,
    # and -i with no terminal leaves it waiting on a stdin nobody is attached to.
    if [ -t 0 ] && [ -t 1 ]; then
        set -- -it "$@"
    fi
    if [ -d /sys/fs/selinux ]; then
        set -- --security-opt label=disable "$@"
    fi

    "$ENGINE" run "$@"
}

# The wheel decides which payload the bundle will accept, and until this
# existed nothing made it agree with the payload being staged beside it.
#
# `installer._manifest_for` prefers the manifest *baked into the wheel* over
# the one in the directory it is installing from, deliberately: that is what
# makes the origin untrusted storage. src/libera/manifest.json is gitignored,
# so on a builder it is whatever some earlier run left there -- and the two
# machines had drifted in opposite directions. builder-arm64 carried one from
# 15 September naming payload 0.1, so the in-sandbox install refused with
# "manifest is for payload 0.1, this libera needs 0.2". fedora.zt had none at
# all, so the build passed by falling through to $DIST -- and shipped a wheel
# with no provenance in it, which is the shape of the 0.1.0 failure.
#
# Stamping it from $DIST makes the wheel and the payload one release, which is
# the rule notes/plans/release-0.2.md is built on.
stamp_bundled_manifest() {
    src="$DIST/manifest.json"
    [ -f "$src" ] || { say "FATAL: no manifest.json in $DIST" >&2; exit 1; }

    got="$(sed -n 's/.*"payload_version": *"\([^"]*\)".*/\1/p' "$src" | head -1)"
    [ "$got" = "$PAYLOAD_VERSION" ] || { say \
        "FATAL: $src is for payload $got and this tree wants $PAYLOAD_VERSION.
       The bundle would carry editors the application refuses to load." >&2; exit 1; }

    cp "$src" "$REPO/src/libera/manifest.json"
    say "    manifest  payload $got, from $DIST"
}

cmd_wheels() {
    step "wheels, for a build with no network"
    stamp_bundled_manifest
    # Assembled somewhere else and moved into place at the end. A wheel set that
    # is present but half-filled is worse than one that is absent -- cmd_build
    # would take it, and the failure would surface as pip resolving libera's
    # dependencies against an empty index four steps later.
    tmp="$WORK/wheels.tmp"
    rm -rf "$tmp" && mkdir -p "$tmp"

    # libera itself, built here: it is pure Python, so the wheel this machine
    # produces is the wheel that ships.
    #
    # Into $tmp with --out-dir, and emphatically not `rm -rf dist && uv build
    # --wheel` in the repository. That is what this used to do, and the
    # release runs the Flatpak step *after* the wheel step -- so it deleted
    # the sdist the release had just made and left dist/ holding a wheel
    # alone. Nothing failed; the sdist was simply gone.
    (cd "$REPO" && uv build --wheel --out-dir "$tmp" >/dev/null)

    # `pip wheel`, not `pip download`: proxy-tools (pywebview's, transitively)
    # publishes an sdist only, and installing an sdist under --no-index would
    # need its build backend at the moment flatpak-builder has taken the network
    # away. Aimed at the wheel itself so the dependency list comes from the
    # package rather than from a second copy of it kept here -- and resolved
    # inside Linux, which is why the pyobjc half of pywebview's dependencies
    # does not follow.
    #
    # --ignore-requires-python because this image is Debian bookworm and its
    # python3 is 3.11, while libera declares >=3.12 and the runtime that will
    # actually run it has 3.13. Nothing is being installed here, only a
    # dependency graph walked -- and the check below is what makes that safe:
    # every wheel has to come out pure-Python and platform-independent, so
    # resolving on the wrong interpreter cannot have picked something different
    # from what 3.13 would get.
    # --user only where it is needed: see engine_writes_as_you in common.sh.
    # Under rootless podman it names a container uid that maps to a subordinate
    # host one, and pip dies with "Permission denied" writing the first
    # dependency into a directory of ours it has just read from.
    set -- -e HOME=/tmp
    engine_writes_as_you || set -- "$@" --user "$(id -u):$(id -g)"
    run "$@" "$IMAGE" -c '
        set -eu
        pip3 wheel --no-cache-dir --ignore-requires-python \
            --wheel-dir build/flatpak/wheels.tmp build/flatpak/wheels.tmp/libera-*.whl
    '

    for whl in "$tmp"/*.whl; do
        case "$whl" in
        *-py3-none-any.whl | *-py2.py3-none-any.whl) ;;
        *)
            say "FATAL: $(basename "$whl") is not a pure-Python wheel." >&2
            say "       Resolving on this image's 3.11 no longer stands in for" >&2
            say "       the runtime's 3.13; resolve inside org.gnome.Sdk instead." >&2
            exit 1
            ;;
        esac
    done

    rm -rf "$WORK/wheels"
    mv "$tmp" "$WORK/wheels"
    ls -1 "$WORK/wheels" | sed 's/^/    /'
}

cmd_payload_stage() {
    # The payload goes inside the bundle, so the release artifacts have to be
    # beside the manifest before flatpak-builder runs: it gives the build no
    # network, which is the property that makes the result reproducible.
    #
    # Staged rather than mounted, because flatpak-builder resolves a source
    # against the manifest's own directory and $DIST is outside the repository.
    # ~120 MB of copy per build, against a bundle that then installs offline.
    step "payload, for $PLATFORM"
    core="core-$PLATFORM.tar.gz"
    [ -d "$DIST" ] && [ -f "$DIST/manifest.json" ] && [ -f "$DIST/$core" ] || {
        say "FATAL: no payload artifacts for $PLATFORM in $DIST" >&2
        say "       The bundle carries the editors now, so it needs them built." >&2
        say "       On this machine:  ARCH=$ARCH sh build/docker.sh all" >&2
        say "                         ARCH=$ARCH sh build/docker.sh export" >&2
        say "       Or point at a directory of artifacts with DIST=" >&2
        exit 1
    }

    tmp="$WORK/payload.tmp"
    rm -rf "$tmp" && mkdir -p "$tmp"
    # Only what this architecture needs. The other cores are 70 MB each of
    # something this bundle can never run, and install() would ignore them --
    # but they would still be copied, and then live in the build cache.
    cp "$DIST/manifest.json" "$DIST/$core" "$tmp/"
    for f in "$DIST"/editors.tar.gz "$DIST"/fonts-*.tar.gz; do
        [ -f "$f" ] || { say "FATAL: no $(basename "$f") in $DIST" >&2; exit 1; }
        cp "$f" "$tmp/"
    done
    rm -rf "$WORK/payload"
    mv "$tmp" "$WORK/payload"
    du -sh "$WORK/payload" | sed 's/^/    /'
}

cmd_build() {
    # Docker writes the bundle as root and it has to be handed back; rootless
    # podman wrote it as you already, and chowning to $(id -u) inside its user
    # namespace would hand it to a subordinate uid instead -- artifacts the
    # host can read and cannot delete. See engine_writes_as_you in common.sh.
    if engine_writes_as_you; then
        chown_back=":"
    else
        chown_back="chown -R $(id -u):$(id -g) /repo/build/flatpak 2>/dev/null || :"
    fi

    # Always, not "unless wheels/ is there". The wheel carries
    # src/libera/manifest.json -- which is what the application verifies its
    # payload downloads against -- so a wheel built before the manifest was
    # last written ships a bundle that refuses to install a payload:
    #
    #     libera: manifest has no core artifact for linux-arm64
    #
    # from inside the sandbox, with the right manifest sitting on disk outside
    # it. Twenty seconds against shipping a beta artifact that cannot install.
    cmd_wheels
    cmd_payload_stage

    # The icon and the desktop entry, from the one place each of them lives.
    # flatpak-builder resolves a source against the manifest's own directory,
    # so both have to be here by the time it runs -- copied rather than
    # committed here, because each has a second consumer. The drawing is also
    # the .icns on macOS and the Dock icon the host sets at runtime; the entry
    # is what `libera --launcher-install` writes on an ordinary Linux install,
    # and two committed copies of it would drift the moment one gained a
    # MimeType. Both gitignored.
    cp "$REPO/src/libera/icon.svg" "$WORK/$APP_ID.svg"
    cp "$REPO/src/libera/launcher.desktop" "$WORK/$APP_ID.desktop"

    step "flatpak-builder"
    # The runtime version is read out of the manifest rather than repeated here:
    # two places to bump it is one place to forget it.
    run "$IMAGE" -c "
        set -eu
        flatpak remote-add --if-not-exists flathub \
            https://dl.flathub.org/repo/flathub.flatpakrepo
        rt=\$(sed -n \"s/^runtime-version: *'\\(.*\\)'\$/\\1/p\" build/flatpak/$APP_ID.yml)
        [ -n \"\$rt\" ] || { echo 'FATAL: no runtime-version in the manifest' >&2; exit 1; }
        flatpak install -y --noninteractive flathub org.gnome.Platform//\$rt org.gnome.Sdk//\$rt
        cd build/flatpak
        rm -rf builddir repo
        flatpak-builder --force-clean --repo=repo builddir $APP_ID.yml
        flatpak build-bundle repo $BUNDLE $APP_ID
        # flatpak-builder runs as root and this directory is a bind mount of
        # the repository, so without this every artifact it writes -- the
        # bundle, builddir, repo, .flatpak-builder -- belongs to root on the
        # host. The first symptom is the *next* run stopping to ask
        #
        #     mv: replace '.../libera-0.1.0-amd64.flatpak', overriding mode 0644?
        #
        # in the middle of a release nobody is watching. macOS maps ownership
        # and never sees it; Linux does.
        $chown_back
    "

    # On content, not on an exit code. There is no single failure here that
    # exits non-zero and produces a plausible file, but the house rule is the
    # house rule, and a bundle that carries no /app/bin/libera is exactly the
    # kind of thing a green build has shipped before.
    step "what came out"
    [ -s "$WORK/$BUNDLE" ] || { say "FATAL: no bundle at $WORK/$BUNDLE" >&2; exit 1; }
    for f in files/bin/libera files/share/applications/$APP_ID.desktop \
             files/share/icons/hicolor/scalable/apps/$APP_ID.svg; do
        run "$IMAGE" -c "[ -e build/flatpak/builddir/$f ]" \
            || { say "FATAL: the build produced no $f" >&2; exit 1; }
        say "    $f"
    done

    mkdir -p "$DEST"
    # -f, because a prompt in a step that runs unattended is a hang, not a
    # question. The chown above should mean there is nothing to prompt about;
    # this is the belt to its braces.
    mv -f "$WORK/$BUNDLE" "$DEST/$BUNDLE"
    ls -lh "$DEST/$BUNDLE" | sed 's/^/    /'

    cmd_check

    say ""
    say "    install:  flatpak install --user $DEST/$BUNDLE"
    say "    run:      flatpak run $APP_ID"
}

# Install the bundle and run it, which is as far as a container goes: there is
# no display in here, so this cannot open a window -- but it can ask the
# application whether it could, which is the half that has ever been wrong.
#
# `libera --diagnose` is the check because it already answers exactly this:
# whether the wheels import under the runtime's python, whether gi finds GTK and
# WebKit, and what it thinks of the payload. A bundle that builds and cannot
# import pywebview is a thing that has shipped from other projects.
cmd_check() {
    step "run it, as far as a machine with no display can"
    [ -f "$DEST/$BUNDLE" ] || { say "FATAL: no bundle at $DEST/$BUNDLE" >&2; exit 1; }

    report=$(run -v "$DEST:/bundles:ro" "$IMAGE" -c "
        set -eu
        # The flatpak volume is kept between runs, so the previous build of
        # this same version is still installed in it. install --reinstall does
        # not cover a bundle: it fails with already-installed just the same.
        flatpak uninstall -y --noninteractive $APP_ID >/dev/null 2>&1 || :
        flatpak install -y --noninteractive /bundles/$BUNDLE >/dev/null
        flatpak run $APP_ID --diagnose 2>&1
    ") || { say "$report" >&2; exit 1; }

    say "$report" | sed 's/^/    /'

    # On content. --diagnose exits 0 whatever it finds, by design: it is a
    # report, not a test.
    echo "$report" | grep -q '^window *ok' || {
        say "FATAL: --diagnose says no window can be opened in the runtime." >&2
        say "       The GNOME runtime is what supplies GTK and WebKit here, so" >&2
        say "       this means the runtime-version in the manifest moved under us." >&2
        exit 1
    }

    # And the payload, which the bundle now carries. This used to read
    # `payload MISSING` and that was correct; it is a failure now, and the kind
    # that would otherwise reach a user as an application that starts and
    # cannot open anything.
    echo "$report" | grep -q '^payload .*(bundled)' || {
        say "FATAL: the bundle does not carry its payload." >&2
        say "       --diagnose should say 'payload 0.1 (bundled)'. Either the" >&2
        say "       install step in the manifest did not run, or resolve() no" >&2
        say "       longer looks beside the application: see" >&2
        say "       locate.bundled_dir()." >&2
        exit 1
    }
}

# The payload running under the runtime, which is a different userland from the
# one that compiled it. build/flatpak/runtime-smoke.py says what it checks.
cmd_smoke() {
    [ -f "$DEST/$BUNDLE" ] || { say "FATAL: no bundle at $DEST/$BUNDLE" >&2; exit 1; }

    # No $DIST and no --payload-install: the bundle carries its editors, so
    # this now exercises what a user actually gets rather than a payload put
    # there by the test.
    step "the payload, under the runtime"
    run -v "$DEST:/bundles:ro" "$IMAGE" -c "
        set -eu
        flatpak uninstall -y --noninteractive $APP_ID >/dev/null 2>&1 || :
        flatpak install -y --noninteractive /bundles/$BUNDLE >/dev/null
        python3 build/flatpak/runtime-smoke.py
    "
}

case "$1" in
versions) run "$IMAGE" -c "cat /etc/libera-flatpak-image.txt" ;;
wheels)   cmd_wheels ;;
build)    cmd_build ;;
check)    cmd_check ;;
smoke)    cmd_smoke ;;
shell)    run "$IMAGE" -c "exec /bin/bash" ;;
*)        say "unknown command: $1" >&2; exit 2 ;;
esac
