#!/bin/sh
# Collect every platform's artifacts and put them on the payload origin.
#
#   build/origin.sh status    where this release is, and the next command
#   build/origin.sh collect   gather each builder's core here, restamp the manifest
#   build/origin.sh push      upload what the manifest names
#   build/origin.sh check     fetch it all back and verify, with no token
#
#   DRY=1      say what would happen and change nothing
#   QUICK=1    check: ask for sizes only, skipping the hashing
#   WHEEL=...  check: take the manifest from a wheel instead of from the tree.
#              A path, or `pypi` for the newest unyanked wheel published there.
#
# Three verbs, because they fail differently and cost differently. Collecting
# is a quarter of a gigabyte over ssh, pushing is the same again upward, and
# checking is a read. A failed upload is then retried on its own, without
# pulling everything across the network again first.
#
# **check is the verb a release has never had.** `curl -T` reports success for
# a truncated body, for a redirect to an HTML error page, and for an object
# written into the wrong prefix. The manifest the wheel ships is what decides:
# fetch each URL the way a stranger's machine will, with no token and no
# configuration, and hash it against what the application is going to demand.
#
# The origin and the version are read out of the application rather than
# repeated here. They are what the installed `libera` will ask for, so a script
# that spelt them itself could publish a perfect set of artifacts to a
# directory nothing looks in.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
. "$HERE/common.sh"

say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
die()  { printf 'FATAL: %s\n' "$*" >&2; exit 1; }

# --- where the payload lives, asked of the application ------------------------
#
# sed and not an import: this has to run on a build machine whose `python3` may
# be older than the tomllib that libera.payload.locate imports, and it is two
# constants.
ORIGIN="$(sed -n 's/^DEFAULT_ORIGIN = "\(.*\)"$/\1/p' "$REPO/src/libera/payload/installer.py")"
[ -n "$ORIGIN" ] || die "no DEFAULT_ORIGIN in src/libera/payload/installer.py"

VERSION="$(sed -n 's/^PAYLOAD_VERSION = "\(.*\)"$/\1/p' "$REPO/src/libera/payload/locate.py")"
[ -n "$VERSION" ] || die "no PAYLOAD_VERSION in src/libera/payload/locate.py"

# The build's copy of the same number. Two definitions of one version is a way
# to publish to a directory the application never reads, and the failure would
# not appear until somebody ran --payload-install.
BUILD_VERSION="$(sed -n 's/^version *= *//p' "$HERE/payload.version" | tr -d '"')"
[ "$BUILD_VERSION" = "$VERSION" ] || die \
    "build/payload.version says $BUILD_VERSION and locate.py says $VERSION.
       The artifacts would go to $VERSION/ and the build would name them
       $BUILD_VERSION. Fix one before publishing anything."

# The zone is the first path segment: that is how the CDN resolves one.
CDN_URL="${CDN_URL:-$(echo "$ORIGIN" | sed 's|\(https\{0,1\}://[^/]*\).*|\1|')}"
ZONE="${ZONE:-$(echo "$ORIGIN" | sed 's|https\{0,1\}://[^/]*/||')}"
[ -n "$ZONE" ] || die "no zone in $ORIGIN -- it should be https://host/<zone>"

DIST="$OUT/dist/$VERSION"
MANIFEST="$REPO/src/libera/manifest.json"

# --- who builds what ----------------------------------------------------------

BUILDERS="${BUILDERS:-$HERE/builders.conf}"

# Read as `platform target [dist-dir] [neutral]`, one per line. Kept out of git
# because it names machines, and a public repository is no place for an
# inventory of somebody's build hosts. builders.conf.example is the template.
read_builders() {
    [ -f "$BUILDERS" ] || die \
        "no builder list at $BUILDERS
       copy build/builders.conf.example to build/builders.conf and fill it in."
    stripped="$(mktemp)"
    sed 's/#.*//' "$BUILDERS" > "$stripped"
    # Read with a redirect rather than down a pipe, so a bad line can stop the
    # script instead of quietly shortening the list from inside a subshell.
    while read -r platform target dir flag extra; do
        [ -n "${platform:-}" ] || continue
        case "${dir:-}" in
        # Columns are positional, so an omitted directory silently makes
        # `neutral` the directory. Say so rather than fetch from a path called
        # neutral/ and report three missing files.
        neutral) die "in $BUILDERS, line for $platform: no directory column.
       Write - for the default:   $platform  ${target:-local}  -  neutral" ;;
        "" | "-") dir="$OUT/dist" ;;
        esac
        [ -z "${extra:-}" ] || die "in $BUILDERS, line for $platform: too many columns ($extra)"
        case "${flag:-}" in
        "" | neutral) ;;
        *) die "in $BUILDERS, line for $platform: unknown flag '$flag' (only 'neutral')" ;;
        esac
        printf '%s\t%s\t%s\t%s\n' "$platform" "${target:-local}" "$dir" "${flag:-}"
    done < "$stripped"
    rm -f "$stripped"
}

# --- collect ------------------------------------------------------------------

# Only the core named for that builder's platform, and the neutral artifacts
# from exactly one of them.
#
# The neutral half -- editors.tar.gz and fonts-*.tar.gz -- is built from the
# same pinned sources everywhere, which makes it tempting to take whichever
# copy arrives last. It is not byte-identical: tar records modes and order,
# gzip records a timestamp, and two machines produce two different SHA-256 for
# the same content. The manifest names one hash, so a second rsync writing over
# a file the manifest already describes is a hash mismatch on a tester's
# machine -- reported there, hours later, as a corrupt download.
cmd_collect() {
    step "collecting into $DIST"
    mkdir -p "$DIST"

    # Into a file rather than down a pipe: a `while read` at the end of a
    # pipeline runs in a subshell, so everything it learned about what arrived
    # would be thrown away at the `done`.
    list="$(mktemp)"
    trap 'rm -f "$list"' EXIT INT TERM
    read_builders > "$list"
    [ -s "$list" ] || die "no builders listed in $BUILDERS"

    missing=""
    while IFS="$(printf '\t')" read -r platform target dir _; do
        core="core-$platform.tar.gz"
        fetch "$target" "$dir/$VERSION/$core" "$DIST/$core" \
            || missing="$missing $core"
    done < "$list"

    neutral="$(awk -F'\t' '$4 == "neutral" {print; exit}' "$list")"
    if [ -z "$neutral" ]; then
        neutral="$(head -1 "$list")"
        say "    no builder marked 'neutral'; taking the shared artifacts from the first"
    fi
    n_target="$(printf '%s\n' "$neutral" | cut -f2)"
    n_dir="$(printf '%s\n' "$neutral" | cut -f3)"
    say "    shared artifacts from $n_target"
    for name in editors.tar.gz fonts-core.tar.gz; do
        fetch "$n_target" "$n_dir/$VERSION/$name" "$DIST/$name" \
            || missing="$missing $name"
    done

    step "what is in $DIST"
    for f in "$DIST"/*; do
        [ -f "$f" ] && printf '    %6s  %s\n' "$(du -h "$f" | cut -f1)" "$(basename "$f")"
    done

    # A builder that was down is worth carrying on past -- the other three
    # transfers are not wasted by it. Stamping the manifest anyway is not:
    # a manifest with no arm64 core publishes cleanly and tells an arm64 user
    # "manifest has no core artifact for linux-arm64" days later.
    [ -z "$missing" ] || die "did not arrive:$missing
       The manifest is left as it was. Fix those and run collect again."

    step "manifest, over everything collected"
    if [ "${DRY:-}" = "1" ]; then
        say "    would run: INSTALL_MANIFEST=1 sh build/dist.sh --manifest-only"
        return 0
    fi
    INSTALL_MANIFEST=1 sh "$HERE/dist.sh" --manifest-only
}

# scp and not rsync: a build machine is whatever the platform gives you, and
# Windows ships OpenSSH without rsync. These are five whole files that either
# transfer or do not, so rsync's delta protocol buys nothing here.
#
# Returns non-zero rather than dying, so one unreachable builder does not throw
# away the transfers that worked.
fetch() {
    target=$1 remote=$2 local=$3
    name="$(basename "$local")"
    if [ "$target" = "local" ]; then
        [ "$remote" = "$local" ] && { say "    have  $name"; return 0; }
        [ -f "$remote" ] || { say "    MISSING $remote"; return 1; }
        [ "${DRY:-}" = "1" ] && { say "    would copy $remote"; return 0; }
        cp "$remote" "$local" && say "    local $name"
        return 0
    fi
    [ "${DRY:-}" = "1" ] && { say "    would scp $target:$remote"; return 0; }
    say "    scp   $target:$remote"
    scp -q "$target:$remote" "$local" && return 0
    say "          failed -- is dist.sh run for payload $VERSION there,"
    say "          and is the path in $BUILDERS right?"
    return 1
}

# --- push ---------------------------------------------------------------------

# What to upload, taken from the manifest rather than from a glob of $DIST.
# That directory also holds dist.sh's .stage and, after a version bump, the
# previous release -- and the manifest is the definition of a payload anyway.
#
# Smallest first, so a wrong token or a zone that does not exist costs the
# 3.8 MB of fonts rather than the 68 MB of a core. manifest.json goes last, in
# push(): a half-finished upload that already carries the manifest describes
# artifacts the origin does not have yet.
manifest_names() {
    python3 -c 'import json, sys
artifacts = json.load(open(sys.argv[1], encoding="utf-8"))["artifacts"]
print(" ".join(a["name"] for a in sorted(artifacts, key=lambda a: a["size"])))' \
        "$MANIFEST"
}

cmd_push() {
    [ -f "$MANIFEST" ] || die \
        "no $MANIFEST
       Run: build/origin.sh collect   (or INSTALL_MANIFEST=1 sh build/dist.sh --manifest-only)"

    # The dirty check before the token check, because it is the one that costs
    # something to fix: commit, collect again, and only then come back.
    #
    # The manifest records the tree it was stamped from, and 05-packaging.md
    # asks for a clean one. It is the provenance a user reads out of
    # `libera --payload-status` to find the source these binaries came from,
    # which under the AGPL is the point of recording it -- and a commit plus
    # "there were also some uncommitted changes" names nothing.
    if grep -q '"libera_dirty": true' "$MANIFEST" 2>/dev/null; then
        [ "${ALLOW_DIRTY:-}" = "1" ] || die \
            "the manifest was stamped from a dirty tree, so it names no source
       anyone could check. Commit, run collect again, then push.
       To publish anyway: ALLOW_DIRTY=1 make origin-push"
        say "    ALLOW_DIRTY=1: publishing artifacts with no reproducible provenance"
    fi

    [ -n "${CDN_TOKEN:-}" ] || [ "${DRY:-}" = "1" ] || die \
        "CDN_TOKEN is not set.
       Mint one on the CDN host, scoped to this zone:
         cdn create-token 'libera releases' --org <org> --zone $ZONE --scopes read,write"

    step "publishing payload $VERSION to $CDN_URL/$ZONE/$VERSION/"

    names="$(manifest_names) manifest.json"
    for name in $names; do
        src="$DIST/$name"
        [ "$name" = "manifest.json" ] && src="$MANIFEST"
        [ -f "$src" ] || die "the manifest names $name and $src is not there"
        put "$src" "$name"
    done

    if [ "${DRY:-}" = "1" ]; then
        step "nothing was uploaded (DRY=1)"
        return 0
    fi

    step "published"
    for name in $names; do say "    $CDN_URL/$ZONE/$VERSION/$name"; done
    say ""
    say "    check it:  make origin-check"
}

# One PUT per object, which is the whole of the CDN's upload API. No `cdn`
# binary: build/ has nothing but sh, curl and tar on any machine it runs on,
# and five named files need none of what `cdn sync` adds -- its skip-if-matching
# compares MD5, and the manifest beside them already carries SHA-256.
put() {
    src=$1 name=$2
    url="$CDN_URL/_/api/v1/zones/$ZONE/objects/$VERSION/$name"
    size=$(wc -c < "$src" | tr -d ' ')
    if [ "${DRY:-}" = "1" ]; then
        say "    would PUT $name ($((size / 1000000)) MB) -> $url"
        return 0
    fi
    printf '    %-28s %6s MB  ' "$name" "$((size / 1000000))"
    body="$(curl -sS -T "$src" \
        -H "Authorization: Bearer $CDN_TOKEN" \
        -H "Content-Type: $(content_type "$name")" \
        -w '\n%{http_code}' "$url")" || die "upload failed: $name"
    code="$(printf '%s' "$body" | tail -1)"
    json="$(printf '%s' "$body" | sed '$d')"

    case "$code" in
    200 | 201) ;;
    404)
        say "FAILED"
        die "the CDN has no zone called '$ZONE' ($json)
       It is created on the CDN host, where the database is:
         cdn create-zone $ZONE --org <org>" ;;
    401 | 403) say "FAILED"; die "the token was refused ($code): $json" ;;
    *) say "FAILED"; die "$code from $url: $json" ;;
    esac

    # Assert on what came back, not on curl's exit status. The response says
    # what was stored, and a size that disagrees with the file means the body
    # did not arrive whole -- which is the failure this would otherwise report
    # as a success.
    stored="$(printf '%s' "$json" | sed -n 's/.*"size":[[:space:]]*\([0-9]*\).*/\1/p')"
    [ "$stored" = "$size" ] || { say "FAILED"; die \
        "$name: sent $size bytes, the CDN stored ${stored:-nothing}"; }
    say "stored"
}

content_type() {
    case "$1" in
    *.tar.gz) echo "application/gzip" ;;
    *.json)   echo "application/json" ;;
    *)        echo "application/octet-stream" ;;
    esac
}

# --- check --------------------------------------------------------------------

# The manifest as a *published wheel* carries it, which is the copy that
# decides what somebody else's install accepts.
#
# `libera` 0.1.0 went to PyPI naming a payload that was rebuilt two days later.
# Its five hashes all describe bytes the origin no longer held, and no command
# anywhere compared the two: `check` read the manifest in this tree, which was
# correct, about a wheel that was not. WHEEL=pypi asks the question that was
# never asked.
wheel_manifest() {
    source=$1 dest=$2
    python3 - "$source" "$dest" <<'PY' || die "could not read a manifest from $source"
import io
import json
import sys
import urllib.request
import zipfile

source, dest = sys.argv[1], sys.argv[2]
if source == "pypi":
    with urllib.request.urlopen("https://pypi.org/pypi/libera/json", timeout=60) as r:
        data = json.load(r)
    wheels = [f for f in data["urls"] if f["filename"].endswith(".whl") and not f["yanked"]]
    if not wheels:
        sys.exit(f"libera {data['info']['version']} has no unyanked wheel on PyPI")
    print(f"    {wheels[0]['filename']}, as PyPI serves it")
    with urllib.request.urlopen(wheels[0]["url"], timeout=120) as r:
        source = io.BytesIO(r.read())

with zipfile.ZipFile(source) as z:
    found = [n for n in z.namelist() if n.endswith("libera/manifest.json")]
    if not found:
        # The other half of the same failure: a wheel with no manifest verifies
        # nothing and refuses every download.
        sys.exit("that wheel ships no libera/manifest.json, so it can verify nothing")
    open(dest, "wb").write(z.read(found[0]))
PY
}

# As a stranger sees it: no token, no config, the public URL the wheel will
# build. Hashing is streamed rather than downloaded, so this verifies a quarter
# of a gigabyte and writes nothing to disk.
cmd_check() {
    manifest="$MANIFEST"
    if [ -n "${WHEEL:-}" ]; then
        step "manifest from $WHEEL"
        manifest="$(mktemp -d)/manifest.json"
        wheel_manifest "$WHEEL" "$manifest"
    fi
    [ -f "$manifest" ] || die "no $manifest to check against"
    step "reading $CDN_URL/$ZONE/$VERSION/ as a stranger"
    # The directory comes out of the manifest being checked rather than out of
    # the tree: a wheel naming payload 0.1 has to be checked against 0.1/, even
    # when this checkout has moved on.
    want="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["payload_version"])' "$manifest")"
    QUICK="${QUICK:-}" BASE="$CDN_URL/$ZONE/$want" \
        python3 - "$manifest" <<'PY'
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

manifest = json.loads(open(sys.argv[1], encoding="utf-8").read())
base, quick = os.environ["BASE"], os.environ.get("QUICK") == "1"

wanted = [
    {"name": a["name"], "size": a["size"], "sha256": a["sha256"]}
    for a in manifest["artifacts"]
]
# The manifest itself is not one of its own artifacts, and only --trust-manifest
# reads it from here -- but a mirror needs it, so its absence is worth knowing.
wanted.append({"name": "manifest.json", "size": None, "sha256": None})

bad = 0
for art in wanted:
    url = f"{base}/{art['name']}"
    try:
        request = urllib.request.Request(url, method="HEAD" if quick else "GET")
        with urllib.request.urlopen(request, timeout=120) as r:
            length = int(r.headers.get("Content-Length") or 0)
            if quick:
                got = None
            else:
                h = hashlib.sha256()
                read = 0
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    h.update(chunk)
                    read += len(chunk)
                got, length = h.hexdigest(), read
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"    MISSING  {art['name']:28} {getattr(e, 'reason', e)}")
        bad += 1
        continue

    problems = []
    if art["size"] is not None and length != art["size"]:
        problems.append(f"{length} bytes, the manifest says {art['size']}")
    if got is not None and art["sha256"] is not None and got != art["sha256"]:
        problems.append(f"sha256 {got[:12]}…, the manifest says {art['sha256'][:12]}…")
    if problems:
        print(f"    WRONG    {art['name']:28} {'; '.join(problems)}")
        bad += 1
    else:
        note = "size ok" if quick else "size and sha256 ok"
        print(f"    ok       {art['name']:28} {note}")

if bad:
    print(f"\nFATAL: {bad} of {len(wanted)} are not what the wheel will ask for.")
    sys.exit(1)
print(f"\n    all {len(wanted)} match the manifest the wheel ships.")
if quick:
    print("    sizes only -- drop QUICK=1 to hash the bytes.")
PY
    [ "${QUICK:-}" = "1" ] || say "
    The last word belongs to the application: on a machine with no payload,
        libera --payload-install"
}

# --- status -------------------------------------------------------------------

# The runbook in docs/src/develop/release.md, answered instead of read.
#
# A release spans days, two machines and hours of unattended building, so the
# question that actually gets asked is "where was I". Remembering is how 0.1.0
# shipped against a payload that had been rebuilt underneath it. This measures
# instead: the tree, the artifacts on this disk, the origin, and PyPI. Then it
# names the next command.
#
# Read-only. No token, nothing written, safe to run at any point.
cmd_status() {
    step "versions"
    app="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$REPO/pyproject.toml" | head -1)"
    printf '    %-13s %-8s %s\n' application "$app" "(pyproject.toml)"
    printf '    %-13s %-8s %s\n' payload "$VERSION" "(payload.version and locate.py, agreed)"

    step "this tree"
    commit="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    dirty="$(git -C "$REPO" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    tag="$(git -C "$REPO" tag --points-at HEAD 2>/dev/null | head -1)"
    say "    commit       $commit  ($dirty file(s) modified)"
    say "    tag          ${tag:-none on HEAD}"

    step "artifacts here, for payload $VERSION"
    missing=""
    for name in core-macos-arm64 core-linux-x86_64 core-linux-arm64 editors fonts-core; do
        f="$DIST/$name.tar.gz"
        if [ -f "$f" ]; then
            printf '    %-26s %6s\n' "$name.tar.gz" "$(du -h "$f" | cut -f1)"
        else
            printf '    %-26s %s\n' "$name.tar.gz" "MISSING"
            missing="$missing $name"
        fi
    done

    step "the manifest in this tree"
    if [ -f "$MANIFEST" ]; then
        python3 - "$MANIFEST" "$VERSION" <<'PY'
import json
import subprocess
import sys

m = json.loads(open(sys.argv[1], encoding="utf-8").read())
src = m.get("source", {})
sha = src.get("libera_commit", "")
known = subprocess.run(["git", "cat-file", "-t", sha], capture_output=True).returncode == 0
print(f"    stamped for payload {m['payload_version']}, built {m['built']}")
print(f"    names commit {sha[:9]}" + ("" if known else "  -- WHICH THIS REPOSITORY DOES NOT HAVE"))
if src.get("libera_dirty"):
    print("    stamped from a dirty tree, so it names no source anyone can check")
if m["payload_version"] != sys.argv[2]:
    print(f"    DISAGREES with this tree, which wants payload {sys.argv[2]}")
PY
    else
        say "    none stamped"
    fi

    step "the origin, and PyPI"
    BASE="$CDN_URL/$ZONE/$VERSION" python3 <<'PY'
import json
import os
import urllib.error
import urllib.request


def reachable(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


base = os.environ["BASE"]
print(f"    origin       {base}/  {'serving' if reachable(base + '/manifest.json') else 'NOT THERE'}")
try:
    with urllib.request.urlopen("https://pypi.org/pypi/libera/json", timeout=30) as r:
        d = json.load(r)
    yanked = sorted(v for v, fs in d["releases"].items() if all(f["yanked"] for f in fs))
    live = sorted(v for v in d["releases"] if v not in yanked)
    line = f"    PyPI         latest {d['info']['version']}; published {', '.join(live)}"
    print(line + (f"; yanked {', '.join(yanked)}" if yanked else ""))
except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
    print(f"    PyPI         could not ask: {e}")
PY

    step "next"
    if [ -n "$missing" ]; then
        # One line per command rather than per artifact: the Mac core and the
        # shared pair all come out of the same `payload-dist`.
        mac="" amd64="" arm64=""
        for name in $missing; do
            case "$name" in
            core-linux-x86_64) amd64=1 ;;
            core-linux-arm64) arm64=1 ;;
            *) mac=1 ;;
            esac
        done
        say "    not here yet:$missing"
        [ -z "$mac" ] || say "      here:              make payload-dist"
        [ -z "$amd64" ] || say "      on the x86_64 box: make payload-container"
        [ -z "$arm64" ] || say "      here:              ARCH=arm64 sh build/docker.sh build/dist.sh --fonts core"
        say "    then:                make origin-collect"
        return 0
    fi
    say "    every core is here. The rest, in order:"
    say "      make origin-collect                       # restamps the manifest over all five"
    say "      make build                                # the wheel, after the manifest"
    say "      make verify"
    say "      CDN_TOKEN=... make origin-push && make origin-check"
    say "      make publish && WHEEL=pypi make origin-check"
}

case "${1:-}" in
status)  cmd_status ;;
collect) cmd_collect ;;
push)    cmd_push ;;
check)   cmd_check ;;
*)
    sed -n '2,10p' "$0" | sed 's/^#\{1,\} \{0,1\}//'
    exit 2
    ;;
esac
