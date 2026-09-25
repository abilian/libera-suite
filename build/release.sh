#!/bin/sh
# Build a whole release, or refuse to build half of one.
#
#   make release-check     check everything and print the plan
#   make release           do it
#
# One command, every artifact. The pieces each worked already -- build.sh,
# payload.sh, dist.sh, docker.sh, macos-app.sh, flatpak.sh -- and what was
# missing is the order, the preconditions, and somebody noticing at the end
# that a platform is absent rather than at the moment a user cannot install it.
#
# What comes out, given a Mac with Docker:
#
#   $DIST/core-macos-arm64.tar.gz      native
#   $DIST/core-linux-x86_64.tar.gz     container, jammy + clang 14
#   $DIST/core-linux-arm64.tar.gz      container, jammy + clang 13
#   $DIST/editors.tar.gz               platform-neutral
#   $DIST/fonts-core.tar.gz            platform-neutral
#   $DIST/manifest.json                over every artifact present
#   dist/libera-*.whl                 the manifest stamped into it
#   build/out/Libera.app              ad-hoc signed
#   build/out/libera-*-amd64.flatpak  the Linux install channel
#   build/out/libera-*-arm64.flatpak
#
# Hours, so --dry-run first. Finding out at the .app step that the tree is
# dirty is a bad way to spend an evening.
#
# Knobs, all with working defaults:
#
#   ARCHES="amd64 arm64"   which Linux architectures to attempt
#   V8_BUILD_JOBS=N        compilers V8 runs at once
#   DOCKER_MEMORY=8g       ceiling for each build container
#   FONTS=core|full        which font pack ships
#   BUILD_DIR is not set here: build/docker.sh puts each container's tree in
#   $BUILD_ROOT/linux-ARCH, beside the native one and on the same disk.
set -eu

# --- read the whole file before running any of it ------------------------------
#
# A shell reads a script incrementally, keeping a byte offset. Edit the file
# while it is running -- which is what happens when this takes hours and
# somebody is working in the repository -- and the shell carries on reading at
# an offset that now points somewhere else in the new text. Measured, not
# feared: a three-second script rewritten underneath ran a fragment of a
# comment as a command, then re-ran a block it had already done.
#
# That is what killed a release after five hours of successful building, with
#
#     build/release.sh: line 267: syntax error near unexpected token `else'
#
# A brace group is one command, so the parser must find the matching `}` before
# executing anything -- and the `exit` inside it means the shell never goes
# back for another. `{` alone is not enough: without the exit it parses the
# group, runs it, and then reads on from the stale offset anyway. Both were
# tested.
{

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
. "$HERE/common.sh"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

VERSION="$(sed -n 's/^version *= *//p' "$HERE/payload.version" | tr -d '"')"
APP_VERSION="$(sed -n 's/^version *= *//p' "$REPO/pyproject.toml" | head -1 | tr -d '"')"
DIST="$OUT/dist/$VERSION"
HOST="$(uname -s)-$(uname -m)"
FONTS="${FONTS:-core}"

# What gets built on this machine rather than in a container, named the way the
# manifest names it.
#
# **macOS only, and that is the whole rule.** There is no macOS container, so a
# Mac has to build its own core here. Linux does not: build/docker.sh exists
# precisely so that a Linux payload never depends on what the host has
# installed, and on a Linux box the host's own architecture is just one more
# container target. Requiring a native toolchain there -- clang, cmake, ninja,
# node, the lot -- is asking for the thing the container was written to avoid.
case "$HOST" in
Darwin-arm64)  NATIVE=macos-arm64 ;;
Darwin-x86_64) NATIVE=macos-x86_64 ;;
*)             NATIVE="" ;;
esac

# Which Linux architectures to attempt.
#
# Both on a Mac: Docker Desktop and OrbStack ship the emulation, an arm64 Mac
# runs linux/amd64 under Rosetta rather than qemu, and this is the release
# machine.
#
# On Linux, only the host's own, because a plain Docker on a distribution does
# not register binfmt handlers for anything else and the failure is
#
#     exec /bin/sh: exec format error
#
# a minute into an image build. `ARCHES="amd64 arm64"` asks for the other one
# anyway, and the precondition below says whether this machine can actually
# run it.
case "$(uname -s)-$(uname -m)" in
Darwin-*)               DEFAULT_ARCHES="amd64 arm64" ;;
Linux-x86_64)           DEFAULT_ARCHES="amd64" ;;
Linux-aarch64 | Linux-arm64) DEFAULT_ARCHES="arm64" ;;
*)                      DEFAULT_ARCHES="amd64" ;;
esac
ARCHES="${ARCHES-$DEFAULT_ARCHES}"

# This machine's own architecture in docker's spelling, for the things that
# cannot be cross-built.
case "$(uname -m)" in
arm64 | aarch64) HOST_ARCH=arm64 ;;
*) HOST_ARCH=amd64 ;;
esac

# A full core build peaks around 12 GB of RSS across its compiles, and the host
# is what runs out -- on a 16 GB Mac this project has had three builds killed
# from outside with nothing in any log. Conservative by default; override when
# the machine is bigger or idle.
V8_BUILD_JOBS="${V8_BUILD_JOBS:-2}"

# A ceiling below what the machine has, because one above it grants nothing:
# `docker run -m 8g` on a 4 GB box still has 4 GB, and the only thing the
# larger number changes is which process the kernel kills when it runs out --
# the host's, rather than the container's. A gigabyte is left for the system.
host_gb() {
    case "$(uname -s)" in
    Darwin) echo $(( $(sysctl -n hw.memsize) / 1073741824 )) ;;
    *) awk '/MemTotal/ {print int($2 / 1048576)}' /proc/meminfo ;;
    esac
}
if [ -z "${DOCKER_MEMORY:-}" ]; then
    gb="$(host_gb 2>/dev/null || echo 8)"
    gb=$(( gb - 1 ))
    [ "$gb" -gt 8 ] && gb=8
    [ "$gb" -lt 2 ] && gb=2
    DOCKER_MEMORY="${gb}g"
fi
export V8_BUILD_JOBS DOCKER_MEMORY

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
skip() { printf '    skipped: %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }

# Everything that has to be true, checked before anything is built. Each one
# has cost somebody a wasted build.
problems=0
complain() { printf '    MISSING: %s\n' "$*" >&2; problems=$((problems + 1)); }

# What this run failed to produce, collected rather than fatal: one platform
# refusing to build is not a reason to throw away the other five artifacts, and
# the report at the end is what says so.
missing=""
# Logs of steps that failed, replayed at the very end.
#
# A failing container step scrolls thousands of lines past the failure, and
# what anyone reads -- or pastes into a bug report -- is the tail. Three times
# running, the tail said "linux arm64 did not build" and the reason was twenty
# thousand lines above it. Put it where it will be looked at.
fail_logs=""
lost() { missing="$missing $1"; printf '    FAILED: %s\n' "$*" >&2; }
lost_with_log() { lost "$1"; fail_logs="$fail_logs $2"; }

linux_platform() { [ "$1" = "amd64" ] && echo linux-x86_64 || echo linux-arm64; }

step "preconditions"
note "version        $VERSION  (payload), $APP_VERSION (application)"
note "host           $HOST  -> ${NATIVE:-everything in containers}"
note "build root     $BUILD_ROOT"
note "dist           $DIST"
note "linux          $ARCHES"
note "fonts          $FONTS"
note "limits         V8_BUILD_JOBS=$V8_BUILD_JOBS  DOCKER_MEMORY=$DOCKER_MEMORY"

# --- skipping work whose inputs have not changed --------------------------------
#
# A release that rebuilds bytes it already has is not safer for it, only
# slower: dist.sh records a sha256 per artifact either way, so a stale one is
# detectable rather than invisible. Measured on a second run with nothing
# changed: 314 seconds, of which 125 were flatpak-builder pruning a cache it
# had just written -- the same 125 with the cache deleted first, so it buys
# nothing -- and 106 were webpack emitting the bundles it emitted before.
#
# So each expensive step carries a stamp, a hash of the things that decide its
# output, and is skipped when the stamp matches and the output is still there.
#
# Content, never timestamps. A checkout rewrites mtimes and would miss every
# stamp; `touch` would rebuild something that had not changed; and a file
# restored to an old mtime would be skipped when it had.
#
# FORCE_PAYLOAD=1 and FORCE_FLATPAK=1 rebuild anyway. So does deleting the
# stamp file, which is how to check that a skip was telling the truth.
# The one file a hashed directory must not include: the release writes it
# itself, at the very end, and it carries the same `built` timestamp that keeps
# manifest.json out of the artifact list below. Hashing it makes every stamp
# that covers src/ miss on every run -- which is exactly what it did, and the
# rebuild it caused looked for all the world like a real change.
GENERATED_MANIFEST="$REPO/src/libera/manifest.json"

stamp_of() {
    for item in "$@"; do
        case "$item" in
        *=*) printf '%s\n' "$item" ;;
        *)
            if [ -d "$item" ]; then
                # Sorted: find's order is the filesystem's, and a stamp that
                # changes when nothing did is worse than no stamp at all.
                find "$item" -type f ! -path "$GENERATED_MANIFEST" \
                    -exec sha256sum {} + 2>/dev/null | sort
            elif [ -f "$item" ]; then
                sha256sum "$item"
            else
                # Named, so that a deleted theme is a different stamp from
                # never having had one.
                printf 'absent %s\n' "$item"
            fi
            ;;
        esac
    done | sha256sum | cut -d' ' -f1
}

# True when the stamp matches *and* every named output is still there. The
# outputs are half the question: a matching stamp with the tarball deleted is
# not "current", it is a stamp describing something that is gone.
step_is_current() {
    _stamp="$1"; _want="$2"; shift 2
    [ -f "$_stamp" ] || return 1
    [ "$(cat "$_stamp")" = "$_want" ] || return 1
    for _out in "$@"; do
        [ -e "$_out" ] || return 1
    done
    return 0
}

# Everything that decides what the payload and its tarballs contain: the pinned
# revisions, our patches and theme, the lists of what ships, the scripts that
# assemble it, the image they run in, the core they pack, and the branding that
# is passed through the environment rather than written down.
payload_stamp() {
    stamp_of \
        "$HERE/pins.toml" "$HERE/patches" "$HERE/theme" \
        "$HERE/payload.version" "$HERE/dictionaries.txt" "$HERE/fonts-core.txt" \
        "$HERE/build.sh" "$HERE/payload.sh" "$HERE/dist.sh" \
        "$HERE/common.sh" "$HERE/docker.sh" "$HERE/docker" \
        "$BUILD_ROOT/linux-$1/out/core/bin" \
        "arch=$1" "fonts=$FONTS" "eo=${EO_VERSION:-}" "theme=${THEME:-}" \
        "company=${COMPANY_NAME:-}" "blank=${BLANK_LOCALE:-}"
}

# And what goes into the bundle: the artifacts it wraps, the host that runs
# them, and the recipe. src/ is in here because the wheels are built from it
# inside flatpak.sh, so a host change has to rebuild the bundle.
#
# The tarballs, not $DIST itself. manifest.json lives there and carries the
# time of the run that wrote it -- `built` -- so hashing the directory makes
# this stamp miss every time and the bundle rebuild for a clock tick. What
# decides the bundle's contents is the artifacts; if those change, the
# manifest's recorded hashes change with them, and this notices either way.
flatpak_stamp() {
    stamp_of \
        "$DIST"/*.tar.gz "$REPO/src" "$REPO/pyproject.toml" "$REPO/uv.lock" \
        "$HERE/flatpak.sh" "$HERE/payload.version" \
        "$HERE"/flatpak/*.yml \
        "arch=$1"
}

# A dirty tree is a fact about what came out, not a reason to refuse to make
# it. dist.sh already records the commit as provenance, warns when it cannot,
# and stamps that warning into the manifest -- so the artifacts tell the truth
# either way, and this check refusing to build adds nothing but an obstacle in
# front of the one person it is aimed at: whoever has the tree open.
#
# So it asks the same question the tag does, and gives the same answer.
# Untagged is a test build, where modified files are the normal state of
# working on something. Tagged is a release, where the commit stops being a
# description and becomes a promise -- and a promise about a tree that is not
# what was built is the thing worth stopping for.
#
# Named, not just counted, either way. "the tree is dirty" tells you there is
# something and not what, and every generated path this build writes is already
# in .gitignore -- so whatever shows here is real and probably surprising.
# `??` is untracked; ` M` is modified.
dirty="$(git -C "$REPO" status --porcelain)"
tag="$(git -C "$REPO" describe --tags --exact-match 2>/dev/null || :)"
if [ -n "$dirty" ]; then
    n="$(printf '%s\n' "$dirty" | wc -l | tr -d " ")"
    if [ -n "$tag" ]; then
        complain "the tree is dirty, and $tag makes its commit a promise"
    else
        note "tree           dirty, $n file(s); the manifest will say so"
    fi
    printf '%s\n' "$dirty" | head -10 | sed 's/^/                 /' >&2
    if [ "$n" -gt 10 ]; then
        say "                 ... and $((n - 10)) more" >&2
    fi
    if [ -n "$tag" ]; then
        say "                 (git stash, or commit, or move the tag)" >&2
    fi
fi
if [ -n "$tag" ]; then
    note "tag            $tag"
else
    note "tag            none (fine for a test build, not for a release)"
fi

# Only the native half reads $SRC. A container fetches its own sources into its
# own tree, so on a Linux box -- where every core comes out of a container --
# an empty $SRC is not a problem and telling someone to run a fetch they do not
# need is worse than saying nothing. And even on a Mac this is a note rather
# than a complaint: step 1 is `build.sh fetch`.
if [ -n "$NATIVE" ]; then
    [ -d "$SRC/core" ] || note "sources        not fetched yet (this run will)"
    [ -x "$OUT/core/bin/x2t" ] || note "core           not built yet (this run will)"
fi
if ! command -v "$ENGINE" >/dev/null 2>&1; then
    # $ENGINE, not docker: common.sh picks one per platform and ENGINE= moves
    # it, so gating on the name docker refused a release on a machine that had
    # podman and could have built every artifact.
    complain "$ENGINE, for the Linux artifacts (ENGINE=docker or ENGINE=podman selects it)"
else
    # Two different questions, asked separately, because one answer used to
    # stand for both.
    #
    # First: does the engine work at all, for this machine's own architecture?
    # A daemon that is not running, a user not in the docker group, no network
    # to pull with -- each of those failed the old check and were reported as
    # "cannot run linux/arm64 containers" on an arm64 box, which is nonsense:
    # its own architecture needs no emulation and never did.
    # The advice has to match the engine: rootless podman has neither a daemon
    # nor a group, so docker's two questions are noise in front of its errors.
    case "$ENGINE" in
    docker) engine_hint="(is the daemon running, and are you in the docker group?)" ;;
    podman) engine_hint="(rootless podman needs no daemon -- try: podman info)" ;;
    *)      engine_hint="(try running it by hand to see why)" ;;
    esac
    if ! probe="$("$ENGINE" run --rm --platform "linux/$HOST_ARCH" alpine:3 true 2>&1)"; then
        complain "$ENGINE would not run a container:
                 ${probe}
                 ${engine_hint}"
    else
        # Second: the foreign ones, which do need binfmt handlers registered.
        # Without them the first sign is `exec format error` inside an image
        # build that has already spent a minute pulling.
        for arch in $ARCHES; do
            if [ "$arch" = "$HOST_ARCH" ]; then
                note "emulation      linux/$arch is native here"
            elif "$ENGINE" run --rm --platform "linux/$arch" alpine:3 true >/dev/null 2>&1; then
                note "emulation      linux/$arch runs under emulation"
            else
                # tonistiigi/binfmt first: it is the one spelling that works
                # wherever docker does. Rootless podman needs the handlers
                # from the distribution instead, since it cannot run a
                # --privileged container to register them. The package names move -- Ubuntu 26.04
                # has no qemu-user-static, only the virtual name over
                # qemu-user-binfmt -- and a wrong package name is worse than
                # no package name.
                complain "this machine cannot run linux/$arch containers, and it is not native.
                 Register the handlers:
                     $ENGINE run --privileged --rm tonistiigi/binfmt --install all
                 or install them from the distribution -- the package is
                 qemu-user-binfmt on recent Ubuntu, qemu-user-static on Debian
                 and Fedora.
                 Or build that architecture on a machine that is one."
            fi
        done
    fi
fi
command -v uv >/dev/null 2>&1 || complain "uv, for the wheel"
# An `if` rather than `[ ... ] && { ... }`, which reads the same and cannot
# quietly become somebody's exit status. The version of that which does bite
# is in common.sh's relocate_macos: an && list as the last command inside a
# command substitution makes the *assignment* fail, and set -e acts on that.
if [ "$(uname -s)" = "Darwin" ]; then
    command -v iconutil >/dev/null 2>&1 || complain "iconutil, for the .app icon"
fi

# Disk, in the one place it is spent. Three builds' worth of core plus their
# 3rdparty trees is most of 100 GB, and running out arrives as a page of
# compiler errors rather than as a disk message.
mkdir -p "$BUILD_ROOT"
free_gb="$(df -g "$BUILD_ROOT" 2>/dev/null | awk 'NR==2 {print $4+0}')"
[ -n "$free_gb" ] || free_gb="$(df -BG "$BUILD_ROOT" 2>/dev/null | awk 'NR==2 {print $4+0}')"
if [ -n "$free_gb" ]; then
    note "free           ${free_gb} GB on $BUILD_ROOT"
    # Measured, not guessed: a finished Linux tree is 15 GB -- 6.5 of sources
    # and 8.9 of output -- and V8 peaks above that before it prunes. 20 leaves
    # room without refusing a build that would have fitted.
    #
    # A target whose tree is already on disk needs a fraction of that: it is
    # being reused, not rebuilt, and the space it occupies is already spent.
    # Asking for the full amount again is how a re-run was refused on a
    # machine holding an 18 GB tree and 16 GB free -- which is to say, the
    # check was counting the thing it was standing on.
    want=0
    for arch in $ARCHES; do
        if [ -d "$BUILD_ROOT/linux-$arch/out/core" ]; then
            want=$((want + 5))
        else
            want=$((want + 20))
        fi
    done
    if [ -n "$NATIVE" ]; then
        if [ -x "$OUT/core/bin/x2t" ]; then
            want=$((want + 5))
        else
            want=$((want + 20))
        fi
    fi
    if [ "$free_gb" -lt "$want" ]; then
        complain "about ${want} GB wanted on $BUILD_ROOT, ${free_gb} GB free"
    fi
fi

# A real run stops here. A dry run carries on and prints the plan anyway --
# telling you what is wrong *and* what would happen is the whole job, and
# refusing to describe the plan because the tree is dirty helps nobody.
if [ "$problems" -gt 0 ] && [ "$DRY" = "0" ]; then
    say ""
    say "$problems thing(s) to fix first."
    exit 1
fi

# --- what this run can and cannot produce ------------------------------------
#
# A release needs one core artifact per platform in one directory, because the
# manifest covers whatever it finds there. Artifacts from earlier runs on other
# machines count: that is how a Mac and a Linux box make one release between
# them.
step "platforms"
for platform in macos-arm64 macos-x86_64 linux-x86_64 linux-arm64; do
    if [ -f "$DIST/core-$platform.tar.gz" ]; then
        note "$platform: already in $DIST"
        continue
    fi
    case "$platform-$HOST" in
    macos-arm64-Darwin-arm64 | macos-x86_64-Darwin-x86_64)
        note "$platform: build natively here" ;;
    linux-x86_64-*)
        case " $ARCHES " in
        *" amd64 "*) note "$platform: build in the container (jammy, clang 14)" ;;
        *) note "$platform: not in ARCHES" ;;
        esac ;;
    linux-arm64-*)
        case " $ARCHES " in
        *" arm64 "*) note "$platform: build in the container (jammy, clang 13)" ;;
        *) note "$platform: not in ARCHES" ;;
        esac ;;
    *)
        note "$platform: NOT AVAILABLE -- build it on that machine and copy"
        note "           core-$platform.tar.gz into $DIST" ;;
    esac
done

if [ "$DRY" = "1" ]; then
    step "plan"
    n=0
    plan() { n=$((n + 1)); printf '    %2d. %-16s %s\n' "$n" "$1" "$2"; }
    # The plan has to agree with the skips, or it reports five hours of work
    # for a run that will take four minutes.
    # These have to ask the same questions the real run asks, of the same
    # things. They did not: the plan looked for a tarball in $DIST and the run
    # looks for a built x2t, and the plan printed one "SKIP: native" line for
    # what the run splits into a skippable core and an unconditional
    # payload-and-dist. So a dry run said nothing would be rebuilt while the
    # run was about to spend four minutes rebuilding the payload -- which is
    # the right thing to do, for the reason written where it happens, and
    # exactly the sort of surprise this flag exists to prevent.
    if [ -n "$NATIVE" ]; then
        if [ -x "$OUT/core/bin/x2t" ] && [ "${FORCE_NATIVE:-0}" = "0" ]; then
            plan "native core" "SKIP: $OUT/core/bin/x2t is there (FORCE_NATIVE=1 rebuilds)"
        else
            plan "native core" "build.sh fetch/configure/build  (hours; V8 alone is ~30 min)"
        fi
        plan "native payload" "payload.sh, smoke.sh  (always -- it carries the theme)"
        plan "native dist"    "dist.sh --fonts $FONTS  ->  core-$NATIVE, editors, fonts"
    fi
    for arch in $ARCHES; do
        if [ ! -x "$BUILD_ROOT/linux-$arch/out/core/bin/x2t" ]; then
            plan "linux $arch" "docker.sh all  (hours)"
        elif [ "${FORCE_PAYLOAD:-0}" = "0" ] && step_is_current \
                "$BUILD_ROOT/linux-$arch/out/.release-payload-stamp" \
                "$(payload_stamp "$arch")" \
                "$BUILD_ROOT/linux-$arch/out/dist/$VERSION/manifest.json"; then
            plan "linux $arch" "SKIP: unchanged since the last run (FORCE_PAYLOAD=1 rebuilds)"
        else
            plan "linux $arch" "repackage: docker.sh build.sh fetch, payload.sh, dist.sh"
            # The flatpak wraps what this step produces, so its own stamp is
            # being compared against artifacts that are about to be replaced.
            # Whether they come out different is not knowable from here -- a
            # change to a README under theme/ leaves the payload byte for byte
            # the same -- so the plan says so rather than guessing either way.
            payload_rebuilds=1
        fi
        plan "linux $arch" "export into $DIST"
    done
    plan "manifest"       "dist.sh --manifest-only, over everything in $DIST"
    plan "wheel"          "uv build, with the manifest stamped in"
    if [ "$(uname -s)" = "Darwin" ]; then
        plan "app"        "macos-app.sh, ad-hoc signed"
    fi
    for arch in $ARCHES; do
        if [ "$arch" = "$HOST_ARCH" ]; then
            if [ "${FORCE_FLATPAK:-0}" = "0" ] && step_is_current \
                    "$HERE/out/.release-flatpak-stamp-$arch" \
                    "$(flatpak_stamp "$arch")" \
                    "$HERE/out/libera-$APP_VERSION-$arch.flatpak"; then
                if [ "${payload_rebuilds:-0}" = "1" ]; then
                    plan "flatpak $arch" "rebuild only if the repackage changes the artifacts"
                else
                    plan "flatpak $arch" "SKIP: unchanged since the last run (FORCE_FLATPAK=1 rebuilds)"
                fi
            else
                plan "flatpak $arch" "flatpak.sh build, then run it in the sandbox"
            fi
        else
            plan "flatpak $arch" "SKIP: no cross-build; make it on a $arch machine"
        fi
    done
    say ""
    if [ "$problems" -gt 0 ]; then
        say "    --dry-run: nothing was built, and $problems thing(s) would stop it."
        exit 1
    fi
    say "    --dry-run: nothing was built. It would run."
    exit 0
fi

# Only the *core* is skippable, and only the core. It is the part measured in
# hours; payload.sh and dist.sh are minutes and they are what carries the
# branding, the theme and the attribution into editors.tar.gz.
#
# Skipping both together is how a release shipped an editors.tar.gz eighteen
# hours older than the licence text in it: the core tarball was present, the
# whole native half was skipped, and dist.sh -- which would have repackaged
# the theme -- never ran. The artifact was stale and nothing said so.
if [ -n "$NATIVE" ]; then
    if [ -x "$OUT/core/bin/x2t" ] && [ "${FORCE_NATIVE:-0}" = "0" ]; then
        step "native core: already built"
        note "$OUT/core/bin/x2t is there; FORCE_NATIVE=1 rebuilds it"
    else
        step "native core"
        sh "$HERE/build.sh" fetch
        sh "$HERE/build.sh" configure
        sh "$HERE/build.sh" build
    fi

    step "native payload and dist"
    sh "$HERE/payload.sh"
    sh "$HERE/smoke.sh"
    sh "$HERE/dist.sh" --fonts "$FONTS"
fi

# Each architecture separately, and a failure in one is recorded rather than
# fatal. Linux arm64 in particular has never been built end to end: V8 8.9
# demands clang exactly 13 there, which is the older of the two reasons both
# containers are jammy; the other is the glibc floor build/docker.sh explains.
for arch in $ARCHES; do
    platform="$(linux_platform "$arch")"
    step "linux $arch"
    # Same split as the native half: reuse a built core, repackage every time.
    # On a Linux host this is also where editors.tar.gz comes from, so it
    # cannot be skipped there without shipping whatever the last run made.
    arch_log="$OUT/release-linux-$arch.log"
    arch_status="$OUT/.release-linux-status"
    rm -f "$arch_status"
    mkdir -p "$OUT"

    payload_stampfile="$BUILD_ROOT/linux-$arch/out/.release-payload-stamp"
    payload_want="$(payload_stamp "$arch")"
    if [ "${FORCE_PAYLOAD:-0}" = "0" ] && step_is_current "$payload_stampfile" \
            "$payload_want" "$BUILD_ROOT/linux-$arch/out/dist/$VERSION/manifest.json"; then
        note "unchanged since the last run; reusing it (FORCE_PAYLOAD=1 rebuilds)"
        echo 0 > "$arch_status"
    else
    # Tee'd for the same reason cmd_build is: the status has to come out of the
    # subshell in a file, because a pipeline's status belongs to tee.
    {
        if [ -x "$BUILD_ROOT/linux-$arch/out/core/bin/x2t" ]; then
            note "core already built; fetching sources, then repackaging"
            # Fetch even here. "Already built" justifies skipping the *core
            # build*, not the source fetch: fetch_repo is what resets each
            # pinned tree and applies build/patches/, so skipping it means a
            # patch added since the tree was checked out never lands -- which
            # is silent, and cost a build that ran the JS pipeline unpatched
            # and died exactly as it had before. The core build tree is under
            # out/, untouched by the clean, so this stays a repackage.
            ARCH="$arch" sh "$HERE/docker.sh" build.sh fetch \
                && ARCH="$arch" sh "$HERE/docker.sh" payload.sh \
                && ARCH="$arch" sh "$HERE/docker.sh" dist.sh --fonts "$FONTS"
        else
            ARCH="$arch" sh "$HERE/docker.sh" all
        fi
        echo $? > "$arch_status"
    } 2>&1 | tee "$arch_log"
    fi
    built_ok=0
    [ "$(cat "$arch_status" 2>/dev/null || echo 1)" = "0" ] && built_ok=1
    rm -f "$arch_status"
    # After the build, never before: a stamp written up front describes a tree
    # that may not exist, and the next run would skip on the strength of it.
    if [ "$built_ok" = "1" ]; then
        printf '%s\n' "$payload_want" > "$payload_stampfile"
    fi
    if [ "$built_ok" = "1" ]; then
        from="$(ARCH="$arch" sh "$HERE/docker.sh" export)"
        # An unmatched glob leaves the pattern itself in $f, so the test has to
        # be there whatever shape it takes.
        mkdir -p "$DIST"
        for f in "$from"/core-linux-*.tar.gz; do
            if [ -f "$f" ]; then
                cp "$f" "$DIST/"
            fi
        done
        # editors and the fonts are platform-neutral, so exactly one machine
        # should decide what is in them.
        #
        # With a native half -- a Mac -- that is the native dist, which has
        # just run, so a container must not overwrite it: copy only what is
        # missing. Without one -- a Linux box -- the container *is* the only
        # source, and "only if absent" would keep whatever an earlier run left
        # there, which is the staleness this whole step exists to avoid.
        for f in "$from"/editors.tar.gz "$from"/fonts-*.tar.gz; do
            [ -f "$f" ] || continue
            if [ -z "$NATIVE" ] || [ ! -f "$DIST/$(basename "$f")" ]; then
                cp "$f" "$DIST/"
            fi
        done
    else
        lost_with_log "linux $arch did not build" "$arch_log"
    fi
done

# The manifest is written last and covers every artifact in the directory, so
# it has to run after everything is collected -- and INSTALL_MANIFEST puts it
# in the wheel, which is what makes the origin untrusted storage.
# --manifest-only: the tarballs are already there, built here and in the
# containers, and rebuilding them needs a native payload this machine may not
# have. A manifest is a description of a directory.
step "manifest, over everything in $DIST"
INSTALL_MANIFEST=1 sh "$HERE/dist.sh" --manifest-only

step "wheel"
(cd "$REPO" && rm -rf dist && uv build)

step "apps"
if [ "$(uname -s)" = "Darwin" ]; then
    sh "$HERE/macos-app.sh"
else
    skip "the .app is macOS only"
fi

# The Flatpak carries the host and fetches the payload, so it depends on
# nothing above it -- but unlike the payload it cannot be cross-built.
#
# flatpak-builder runs every build command inside bubblewrap, and bubblewrap
# installs a seccomp filter compiled for the target architecture. Under
# emulation the kernel is still the host's, so that filter is rejected:
#
#     bwrap: Unable to set up system call filtering as requested:
#     prctl(PR_SET_SECCOMP) reported EINVAL.
#
# on an arm64 Mac asked for linux/amd64. Rosetta translates instructions, not
# the kernel's idea of what architecture a BPF program is for. So each bundle
# is built on its own architecture and collected, the same way the macOS cores
# are -- this Mac makes the arm64 one, an x86_64 box makes the amd64 one.
for arch in $ARCHES; do
    if [ "$arch" != "$HOST_ARCH" ]; then
        step "flatpak $arch"
        note "NOT AVAILABLE here: flatpak-builder cannot cross-build."
        note "Build it on a $arch machine and copy the .flatpak next to this one."
        continue
    fi
    step "flatpak $arch"
    flatpak_stampfile="$HERE/out/.release-flatpak-stamp-$arch"
    flatpak_want="$(flatpak_stamp "$arch")"
    flatpak_bundle="$HERE/out/libera-$APP_VERSION-$arch.flatpak"
    mkdir -p "$HERE/out"
    if [ "${FORCE_FLATPAK:-0}" = "0" ] && step_is_current "$flatpak_stampfile" \
            "$flatpak_want" "$flatpak_bundle"; then
        note "unchanged since the last run; reusing $(basename "$flatpak_bundle")"
        note "(FORCE_FLATPAK=1 rebuilds it)"
    elif ARCH="$arch" sh "$HERE/flatpak.sh" build; then
        printf '%s\n' "$flatpak_want" > "$flatpak_stampfile"
    else
        lost "flatpak $arch did not build"
    fi
done

step "what came out"
ls -1 "$DIST" 2>/dev/null | sed "s|^|    $DIST/|"
# build/out is a directory nothing cleans, and it collects two kinds of thing
# that are not this release.
#
# Things that were never artifacts: gui-linux.png is a test screenshot.
#
# And artifacts of *other* releases. Every build writes a new filename --
# libera-$APP_VERSION-$arch.flatpak -- so the one from the version before stays
# put, and so does the one from before the product was renamed. A Fedora box
# that had built this project in March still had muchado-0.1.0-amd64.flatpak
# sitting beside the bundle that had just been built correctly, and the release
# listed both without comment.
#
# A listing of "what came out" that includes either invites somebody to upload
# one. So: name this release's, and name the rest as strays rather than
# quietly dropping them, because a stale bundle in the output directory is
# something to go and delete.
strays=""
for f in "$HERE"/out/*.app "$HERE"/out/*.flatpak "$HERE"/out/*.dmg; do
    [ -e "$f" ] || continue
    name="$(basename "$f")"
    case "$name" in
    Libera.app | libera-"$APP_VERSION"-*) say "    build/out/$name" ;;
    *) strays="$strays $name" ;;
    esac
done
ls -1 "$REPO/dist" 2>/dev/null | sed 's|^|    dist/|'
if [ -n "$strays" ]; then
    say ""
    say "    NOT part of this release, left in build/out by an earlier one:"
    for s in $strays; do say "        $s"; done
    say "    Delete them, or they get uploaded by mistake."
fi

say ""
for platform in macos-arm64 macos-x86_64 linux-x86_64 linux-arm64; do
    [ -f "$DIST/core-$platform.tar.gz" ] || say "    still missing: core-$platform"
done
# The bundles, which cannot be cross-built and so arrive one machine at a time.
for arch in amd64 arm64; do
    [ -f "$HERE/out/libera-$APP_VERSION-$arch.flatpak" ] \
        || say "    still missing: libera-$APP_VERSION-$arch.flatpak (build it on a $arch machine)"
done

# editors and the fonts are not optional and not per-platform: every install
# unpacks them whatever it is running on. They come out of the native dist on a
# Mac and out of a container export on Linux -- so a Linux run whose every
# architecture was already in $DIST builds no container, exports nothing, and
# would otherwise write a manifest describing a release that cannot be
# installed.
incomplete=""
[ -f "$DIST/editors.tar.gz" ] || incomplete="$incomplete editors.tar.gz"
set -- "$DIST"/fonts-*.tar.gz
[ -f "$1" ] || incomplete="$incomplete fonts-$FONTS.tar.gz"
if [ -n "$incomplete" ]; then
    say ""
    say "    INCOMPLETE: no$incomplete in $DIST."
    say "    Every install needs these, whatever platform it is on. They come"
    say "    out of any payload build, so either build one here or take them"
    say "    from a container that has one:"
    say ""
    # $HOST_ARCH, not a hardcoded amd64: this told an arm64 box to go and
    # ask a container it had never been asked to build.
    say "        ARCH=$HOST_ARCH sh build/docker.sh dist.sh --fonts $FONTS"
    say "        from=\"\$(ARCH=$HOST_ARCH sh build/docker.sh export)\""
    say "        cp \"\$from\"/editors.tar.gz \"\$from\"/fonts-*.tar.gz $DIST/"
    say "        sh build/dist.sh --manifest-only"
    missing="$missing editors/fonts"
fi

# The wheel carries a copy of the manifest and verifies every download against
# it, so the two have to agree exactly. Within one run they do -- the manifest
# step precedes the wheel step -- but a dist.sh run afterwards silently
# invalidates the wheel, and the symptom is a hash mismatch on a tester's
# machine rather than anything here. Three artifacts drifted this way once.
if [ -f "$REPO/src/libera/manifest.json" ] && [ -f "$DIST/manifest.json" ]; then
    if python3 - "$REPO/src/libera/manifest.json" "$DIST/manifest.json" <<'PY'
import json, sys
wheel, dist = (json.load(open(p)) for p in sys.argv[1:3])
same = {a["name"]: a["sha256"] for a in wheel["artifacts"]} == {
    a["name"]: a["sha256"] for a in dist["artifacts"]
}
if not same:
    print("    the wheel's manifest does not match the artifacts in this")
    print("    directory. An install would reject its own payload. Re-run:")
    print("        INSTALL_MANIFEST=1 sh build/dist.sh --manifest-only")
    print("        (cd . && rm -rf dist && uv build)")
raise SystemExit(0 if same else 1)
PY
    then
        say "    the wheel's manifest matches the artifacts"
    else
        missing="$missing manifest/wheel-agreement"
    fi
fi

if [ -n "$missing" ]; then
    say ""
    say "    this run failed to produce:$missing"
    for l in $fail_logs; do
        [ -f "$l" ] || continue
        say ""
        say "    --- the failure in $l ---"
        grep -nE '^FAILED: |error:|Killed signal|virtual memory exhausted|cannot allocate|No space left|FATAL' \
            "$l" | tail -20 | sed 's/^/    /' || say "    (nothing matched; read the log)"
    done
    exit 1
fi

exit 0
}   # end of the read-it-all-first guard
