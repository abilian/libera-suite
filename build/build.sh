#!/bin/sh
# Build Euro-Office core (x2t and friends) from pristine sources plus our patches.
# See README.md. Runs on the laptop; there is no CI.
set -eu

# The whole file is read before any of it runs -- see build/release.sh for
# why, and for the measurement. A brace group plus the exit at the end.
{

HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
# Defines msvc_env(), which is a no-op off Windows.
. "$HERE/msvc-env.sh"
# A local clone to copy objects from, so iterating does not refetch 1.5 GB.
MIRROR="${MIRROR:-$HOME/ghorg/euro-office}"

# What the machine can actually link in parallel. The laptop keeps its old
# hardcoded 4 because it is being used for other things while it builds; a
# Linux build box is not, so let it use what it has.
# How much memory this process may actually use, in GB.
#
v8_jobs() { build_jobs; }

pin() {
    sed -n "s/^$1 *= *\"\([0-9a-f]*\)\".*/\1/p" "$HERE/pins.toml" | head -1
}

# The repo names under [repos], so `fetch` and pins.toml cannot drift apart.
pinned_repos() {
    sed -n '/^\[repos\]/,/^\[[a-z]/p' "$HERE/pins.toml" |
        sed -n 's/^\([A-Za-z0-9_-]*\) *=.*/\1/p'
}

remote_base() {
    sed -n 's/^base *= *"\(.*\)".*/\1/p' "$HERE/pins.toml" | head -1
}

# depot_tools shells out to gsutil, which picks up ~/.boto and then fails on
# stale credentials even for public buckets -- and --no_auth no longer has any
# effect. Point it at an empty config so it uses the anonymous path. This is a
# local environment problem, not something to patch into V8.
setup_env() {
    # V8 defaults to one compile job per core, and linking v8_monolith takes
    # roughly 2 GB a job, so a machine with fewer gigabytes than twice its cores
    # gets the build OOM-killed.
    #
    # There is no prebuilt V8 for us on any platform: hashes.txt lists cache
    # keys for a Nextcloud store that wants NEXTCLOUD_USER/PASS, so ensure_dep
    # finds nothing and builds from source everywhere. Half an hour, on Linux
    # too.
    export V8_BUILD_JOBS="${V8_BUILD_JOBS:-$(v8_jobs)}"
    # Keep V8's object files between runs so an interrupted build resumes
    # rather than restarting from nothing.
    export V8_KEEP_BUILD_DIR="${V8_KEEP_BUILD_DIR:-1}"

    BOTO_CONFIG="$BUILD_ROOT/.boto-empty"
    # Unlink before creating. `: >` truncates, which needs write permission on
    # the *file*; unlink needs it on the directory. A build tree that docker
    # wrote leaves this one owned by root, so the first podman run into the
    # same tree could clone six repositories into a directory it owned and
    # then fail on a zero-byte file it did not -- "cannot create
    # /build/.boto-empty: Permission denied", forty lines further down.
    #
    # `|| true` because an unwritable *directory* is a different fault -- the
    # one the container's write probe reports -- and it should surface on the
    # create below, where the message names what the build was trying to do,
    # rather than here as a failure to remove something.
    rm -f "$BOTO_CONFIG" 2>/dev/null || true
    : > "$BOTO_CONFIG"
    export BOTO_CONFIG
}

require_case_sensitive() {
    # Not on Windows. This guard was measured on macOS, where APFS defaults to
    # case-insensitive and depot_tools minds; NTFS is case-insensitive too, and
    # Chromium's own Windows bots build on it, so the same test would refuse a
    # filesystem that is known to work. If a collision ever does appear there,
    # the answer is per-directory case sensitivity --
    # `fsutil file setCaseSensitiveInfo <dir> enable` -- rather than another
    # volume. Untested either way: no Windows build has been run yet.
    case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) return 0 ;;
    esac
    [ "${OS:-}" = "Windows_NT" ] && return 0

    d="$BUILD_ROOT/.casetest.$$"
    mkdir -p "$d" && : > "$d/CaseFile"
    if [ -e "$d/casefile" ]; then
        rm -rf "$d"
        echo "FATAL: $BUILD_ROOT is on a case-insensitive filesystem." >&2
        echo "       V8/depot_tools needs a case-sensitive one; pick another volume." >&2
        exit 1
    fi
    rm -rf "$d"
}

# git must never stop and ask, and `2>/dev/null || true` does not stop it:
# a credential prompt goes to /dev/tty, so the redirect cannot catch it and the
# `|| true` never runs. The build hangs instead, on a question nobody is
# watching, halfway through six clones.
#
# A public repository can still answer 401. GitHub throttles unauthenticated
# traffic and six clones of ~2 GB in a row is that pattern, at which point git
# asks who you are. With this it fails instead, which for the best-effort fetch
# below is the same thing as succeeding.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true

fetch_repo() {
    repo="$1"
    sha="$(pin "$repo")"
    [ -n "$sha" ] || { echo "FATAL: no pin for $repo in pins.toml" >&2; exit 1; }
    dst="$SRC/$repo"

    if [ ! -d "$dst/.git" ]; then
        src="$(remote_base)/$repo.git"
        [ -d "$MIRROR/$repo/.git" ] && src="$MIRROR/$repo"
        echo "==> clone $repo from $src"
        git clone --quiet --no-checkout "$src" "$dst" || {
            echo "FATAL: could not clone $repo from $src" >&2
            echo "       Every repository in pins.toml is public, so a request" >&2
            echo "       for a username here is usually GitHub throttling" >&2
            echo "       unauthenticated traffic -- six clones of ~2 GB in a row" >&2
            echo "       is the pattern it throttles." >&2
            echo "       Wait and run it again, or clone from local copies:" >&2
            echo "           MIRROR=/path/to/clones make payload-fetch" >&2
            exit 1
        }
    fi

    echo "==> $repo @ $sha"
    git -C "$dst" fetch --quiet --all 2>/dev/null ||
        echo "    (fetch skipped: upstream unreachable or throttled)"
    # Hard reset, so a re-run starts from pristine upstream rather than from
    # whatever the last patch attempt left behind.
    git -C "$dst" checkout --quiet --force --detach "$sha"
    git -C "$dst" clean -qfdx

    patches="$HERE/patches/$repo"
    if [ -d "$patches" ] && [ -n "$(ls -A "$patches" 2>/dev/null)" ]; then
        echo "==> applying $(ls "$patches" | wc -l | tr -d ' ') patch(es) to $repo"
        # No fuzz: a patch that stopped applying is news, not something to guess at.
        # --keep-cr because upstream keeps CRLF files (every .desktop HTML, for
        # one): git am parses a patch as mail, and mailinfo strips the trailing
        # CR from every line, after which no context matches and the patch is
        # rejected with nothing to suggest line endings were involved.
        git -C "$dst" am --keep-non-patch --keep-cr "$patches"/*.patch
    else
        echo "==> no patches for $repo yet"
    fi
}

# git am makes a commit per patch. Without an identity it applies the series,
# fails at the first commit, and leaves the tree mid-am -- which reads as a
# rejected patch rather than an unconfigured machine.
require_git_identity() {
    git config --get user.email >/dev/null && git config --get user.name >/dev/null && return 0
    echo "FATAL: git has no user.email/user.name, and the patch queue is applied" >&2
    echo "       with git am, which makes commits. Set them and re-run:" >&2
    echo "         git config --global user.email you@example.com" >&2
    echo "         git config --global user.name 'Your Name'" >&2
    exit 1
}

cmd_fetch() {
    require_case_sensitive
    require_git_identity
    mkdir -p "$SRC" "$OUT"
    # No argument means every pinned repo. Only core is built here; the rest are
    # the payload (sdkjs, web-apps) and the fonts x2t needs.
    for repo in ${*:-$(pinned_repos)}; do
        fetch_repo "$repo"
    done
}

cmd_configure() {
    setup_env
    # Before the toolchain check, so `cl` is on PATH by the time anything looks
    # for a compiler. On Windows without this, CMake picks up mingw's gcc and
    # configures a GNU build in silence.
    msvc_env
    # Before cmake, because everything this catches fails deep inside a
    # third-party build and in somebody else's words. V8's gn gen wants the
    # host's glib and fails *after* depot_tools has fetched V8 -- 991 seconds,
    # measured on Fedora 43 -- and ICU reports a missing libstdc++.a as
    # "Namespace support is required to build ICU". A second here, either way.
    echo "==> toolchain"
    sh "$HERE/toolchain.sh" check
    mkdir -p "$OUT/core"
    echo "==> cmake configure (no vcpkg toolchain: surface the plain-CMake gaps first)"
    cd "$OUT/core"
    # Teed rather than redirected: a configure that prints nothing for minutes
    # reads as hung, and build_3rdparty.py is minutes. The status goes through
    # a file because a pipeline's exit status is the last command's, and POSIX
    # sh has no pipefail.
    cmake_log="$OUT/core/cmake-configure.log"
    {
        cmake -G Ninja \
            -DCMAKE_BUILD_TYPE=Release \
            -DEO_CORE_OUTPUT_DIR="$OUT/core/bin" \
            -DEO_CORE_TOOLS_DIR="$OUT/core/tools" \
            "$SRC/core" 2>&1
        echo "$?" > "$OUT/core/.cmake-status"
    } | tee "$cmake_log"
    [ "$(cat "$OUT/core/.cmake-status")" = 0 ] || {
        failed_tree "$cmake_log"
        named_logs "$cmake_log"
        exit 1
    }
}

# What the failing component's source tree actually contains.
#
# build_3rdparty.py names the one that stopped -- "❌ openssl failed" -- and a
# build tool complaining it cannot make a source file is either a tool that
# cannot read the tree or a tree that is not there. Those want opposite fixes
# and the logs distinguish them badly, so list it.
failed_tree() {
    name="$(sed -n 's/.*[^a-z]\([a-z0-9_-]*\) failed with code.*/\1/p' "$1" | tail -1)"
    [ -n "$name" ] || return 0
    dir="$OUT/core/third_party/work/$name"
    echo >&2
    echo "--- $name's work tree: $dir ---" >&2
    if [ -d "$dir" ]; then
        ls -1 "$dir" 2>/dev/null | head -25 | sed 's/^/    /' >&2
        echo "    ($(find "$dir" -type f 2>/dev/null | wc -l | tr -d " ") files in all)" >&2
    else
        echo "    the directory does not exist" >&2
    fi
}

# The log the failure named, and only that one.
#
# The first version of this tailed the two newest *.log under third_party,
# which is a proxy and a bad one: a recipe that fails without writing a log --
# OpenSSL hands its output back through run_command instead -- leaves the
# newest files belonging to whatever succeeded before it. It printed forty
# lines of a component that had worked, labelled as the failure.
#
# So read the path out of what cmake actually said. A recipe that names a log
# gets it tailed; one that does not has already printed everything it has.
named_logs() {
    for f in $(sed -n 's/.*(see \([^)]*\.log\)).*/\1/p' "$1" | sort -u); do
        # /cygdrive/d/... is how the Cygwin side of the ICU build spells it.
        case "$f" in /cygdrive/?/*) f="$(echo "$f" | sed 's|^/cygdrive/\(.\)|\1:|')" ;; esac
        [ -f "$f" ] || continue
        echo >&2
        echo "--- the last 40 lines of $f ---" >&2
        tail -40 "$f" >&2
    done
}

# stat's spelling differs between GNU and BSD, and this runs on both.
mtime() {
    stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

cmd_build() {
    msvc_env
    setup_env
    cd "$OUT/core"

    # Ninja defaults to one job per CPU and knows nothing about memory. Inside
    # a container that is the *host's* CPU count against the container's
    # memory limit, and core's heaviest translation units want over a gigabyte
    # each -- so the build dies with cc1plus killed, twenty thousand lines
    # after the last thing anyone read.
    jobs="${CORE_BUILD_JOBS:-$(build_jobs)}"
    echo "==> cmake --build (jobs: $jobs, from $(usable_gb) GB usable)"
    if [ "$jobs" = "1" ]; then
        echo "    one at a time: this machine has little memory, so this is slow." >&2
        echo "    Swap matters more than the job count here. Measured on arm64:" >&2
        echo "    odf_writer.cpp alone peaks at 2.8 GB in one cc1plus, so a 4 GB" >&2
        echo "    box with no swap cannot build core however few jobs it runs." >&2
    fi

    # Tee'd, because a pipeline's status is tee's: the status is carried out of
    # the subshell in a file instead.
    log="$OUT/core-build.log"
    status_file="$OUT/.core-build-status"
    rm -f "$status_file"
    { cmake --build . --parallel "$jobs" 2>&1; echo $? > "$status_file"; } | tee "$log"
    status="$(cat "$status_file" 2>/dev/null || echo 1)"
    rm -f "$status_file"

    if [ "$status" != "0" ]; then
        echo "" >&2
        echo "FATAL: the core build failed. What actually broke, out of $(wc -l < "$log" | tr -d ' ') lines:" >&2
        grep -n '^FAILED: ' "$log" | head -5 | sed 's/^/    /' >&2 || :
        grep -nE 'error:|Killed signal|virtual memory exhausted|cannot allocate|No space left' \
            "$log" | head -25 | sed 's/^/    /' >&2 || :
        echo "" >&2
        echo "    full log: $log" >&2
        if grep -q 'Killed signal' "$log"; then
            # Not "use fewer jobs" when there is only one left to drop to. The
            # heaviest translation unit is 2.8 GB on its own (measured, arm64,
            # gcc 11): odf_writer.cpp #includes other .cpp files, so it is one
            # enormous unit by construction and no job count divides it.
            # Dropping the PCH saves 187 MB of that, which is not enough to
            # matter and costs the rest of the library its speed.
            echo "    cc1plus was killed: this is the OOM killer, not a code error." >&2
            if [ "$jobs" = "1" ]; then
                echo "    Already at one job, so the fix is swap, not fewer:" >&2
                echo "      sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile" >&2
                echo "      sudo mkswap /swapfile && sudo swapon /swapfile" >&2
                echo "    Only a handful of files are this big; the rest stay in RAM." >&2
            else
                echo "      CORE_BUILD_JOBS=1 make release   (now $jobs), or add swap" >&2
            fi
        fi
        exit 1
    fi
    # The installer runs allfontsgen out of the payload, so it has to sit with
    # the libraries it links and be relocated along with them.
    mkdir -p "$OUT/core/bin/tools"
    cp "$OUT/core/tools/allfontsgen" "$OUT/core/bin/tools/"
    echo "==> relocatable check"
    relocate "$OUT/core/bin"
}

case "${1:-}" in
    fetch)     shift; cmd_fetch "$@" ;;
    configure) cmd_configure ;;
    build)     cmd_build ;;
    *) echo "usage: build.sh {fetch [repo...]|configure|build}" >&2; exit 2 ;;
esac

exit 0
}   # end of the read-it-all-first guard
