# Cutting a release

A release is one set of artifacts that agree with each other. No single machine can produce all of them.

**`make ship` is how a release is cut now.** One command drives ten phases: the Linux cores and both Flatpak bundles are built on the Linux builders in parallel, the macOS core and the wheel here, then the origin and PyPI. `make ship-plan` prints the plan and runs nothing. See [`make ship`](#make-ship) below.

Read [Build the payload](build.md) first if you have never built one. This page assumes you have.

## make ship

```sh
make ship-plan                        # the plan, running nothing
make ship                             # all ten phases
make ship ARGS="collect push check"   # some of them
make ship ARGS="--only linux-arm64"   # one builder
```

```
update  native  build  collect  push  check  bundles  wheel  publish  verify
```

The order is forced. `wheel` follows `collect`, because the wheel embeds the manifest `collect` stamps over every core; `verify` follows `publish`, because what it checks is the *published* wheel against the *published* payload. The phases run in that order whatever order they are typed in, so there is no way to get it wrong from the command line.

`publish` is the one phase with no undo, since PyPI refuses a version it has already seen even after a yank. It stops and asks on `/dev/tty` unless `--yes` is given. Asking on the terminal matters here: this is usually run under tmux with its output redirected, where a prompt on stdin is a prompt no one can answer.

Every phase checks what the machine printed, because over ssh an exit status describes the shell, including its logout scripts. Per-host logs land in `tmp/remote/`.

The builders are listed in `build/builders.toml`, which is gitignored because it is an inventory of machines; copy `builders.toml.example` once. `build/origin.sh` reads the same file through the same parser, so there is one list.

## The runbook, by hand

What `make ship` does, phase by phase, for when part of a release has to be
redone or driven from somewhere else.

**One phase needs a Mac.** `native` builds `core-macos-arm64`, which nothing
else can. Everything below it runs wherever you are sitting, so long as that
machine has `build/builders.toml` and ssh to the builders. The Mac is one of
three builders.

**Settle the two versions first.** `pyproject.toml` moves every release.
`build/payload.version` and `src/libera/payload/locate.py` move together, and
only when the payload itself changed. Rebuilding a payload under a version that
is already published overwrites artifacts a published wheel verifies against:
that is how 0.1.0 broke.

**`make release-status`** measures where a release has got to, against the
tree, the artifacts on this disk, the origin and PyPI, then prints the next
command. A release runs over days and several machines, so it measures which
step you are on and does not ask you to remember.

| phase | what it does | where it runs |
| :--- | :--- | :--- |
| | `git tag -a vX.Y.Z && git push --tags`, before building, so the manifest records a revision other people can fetch. `ship` does not do this. | anywhere |
| `update` | `git pull` each builder onto its branch, and refuse a dirty one. | the driving machine |
| `native` | The macOS core and its tarballs. | **a Mac, and only this** |
| `build` | The Linux cores, on their own machines, in parallel. Hours. | the Linux builders |
| `collect` | Fetch every core to the driving machine, then stamp `src/libera/manifest.json` over the whole set. | the driving machine |
| `push` | Upload the payload to the origin. Needs `CDN_TOKEN`. | anywhere |
| `check` | Fetch it all back with no token and verify every hash. | anywhere |
| `bundles` | The two `.flatpak` bundles. Neither can be cross-built. | a machine of each architecture |
| `wheel` | `make verify`, then the wheel. After `collect`, always. | anywhere |
| | The Windows installer, `sh build/origin.sh windows`, before `publish`. `ship` does not build Windows. | the Windows machine |
| `publish` | The wheel to PyPI; the bundles, `install.sh` and `install.ps1` to the origin; then `bundles/latest`, which moves both install scripts to the new version. | anywhere with the credentials |
| `verify` | Read the *published* wheel back and check it against the origin. The check 0.1.0 needed. | anywhere |

Two things are left that no command covers. The mirrors go up, and somebody
runs `libera --payload-install` on a machine that has never built it.

Any one phase runs on its own, which is what makes a partial redo cheap:

```sh
make ship ARGS="collect push check"
make ship ARGS="--only linux-arm64 bundles"
```

`make release` is the older path. It builds every Linux core in containers on
one machine, with no builders involved. It needs Docker locally and
cannot produce the bundles at all. Prefer `ship`.

## What a release is

| Artifact | Where it goes | Built by |
| :--- | :--- | :--- |
| `core-linux-x86_64.tar.gz` | the origin | a container |
| `core-linux-arm64.tar.gz` | the origin | a container |
| `core-macos-arm64.tar.gz` | the origin | a Mac, natively |
| `editors.tar.gz` | the origin | any payload build: **exactly one** |
| `fonts-core.tar.gz` | the origin | the same one |
| `manifest.json` | the origin | last, over the directory |
| `libera-X.Y.Z-py3-none-any.whl` | PyPI | after the manifest, with a copy of it inside |
| `Libera.app` | a download | a Mac |
| `libera-X.Y.Z-amd64.flatpak` | a download | an x86_64 Linux machine, **payload included** |
| `libera-X.Y.Z-arm64.flatpak` | a download | an arm64 machine, **payload included** |

The tarballs go to `$BUILD_ROOT/out/dist/$PAYLOAD_VERSION`, which is `0.2` today and **not** the application version, `0.2.0`. The two reading 0.2 at the same time is a coincidence of counting. `build/payload.version` and `pyproject.toml` move independently on purpose: a host fix should not force everyone to re-download 120 MB; a payload rebuilt from new upstream pins should not need a host release.

## Which machine can make what, and why

Three constraints have each cost somebody a build:

**There is no macOS container.** A Mac builds its own core natively. Everything else about a Mac release follows from that one fact.

**A Linux core is built in a container, whatever the host is.** `build/docker.sh` exists so that a Linux payload never depends on what the host has installed, and that holds on a Linux builder as much as on a Mac: the host's own architecture is one more container target, so do not build it natively there. An Apple Silicon Mac can stand in, building `linux/arm64` natively and `linux/amd64` under Rosetta, which is the fallback when a builder is unreachable.

**Flatpak bundles cannot be cross-built.** `flatpak-builder` runs every build command inside bubblewrap, which installs a seccomp filter compiled for the target architecture. Under emulation the kernel is still the host's, so it is rejected:

```
bwrap: Unable to set up system call filtering as requested:
prctl(PR_SET_SECCOMP) reported EINVAL.
```

Rosetta translates instructions; it leaves the kernel's idea of what architecture a BPF program is for alone. So each bundle is built on a machine of its own architecture, then collected.

Which leaves the division of labour:

| | Mac (Apple Silicon) | x86_64 Linux | arm64 Linux |
| :--- | :--- | :--- | :--- |
| `core-macos-arm64` | **only here** | no | no |
| `core-linux-x86_64` | yes (Rosetta) | yes | no |
| `core-linux-arm64` | yes (native) | no | yes |
| editors, fonts, manifest, wheel | yes | yes | yes |
| `Libera.app` | **only here** | no | no |
| `*-arm64.flatpak` | yes | no | yes |
| `*-amd64.flatpak` | no | **only here** | no |

That table is what each machine *can* do. It is not how a release is built.
`make ship` sends the Linux cores to the Linux builders, which is faster than a
Mac emulating amd64 and is the only way to get the amd64 bundle at all. The Mac
then does one thing nothing else can, `core-macos-arm64`, and the machine you
type the command on does the collecting and the publishing.

An arm64 Linux box has a second job: it is the only place the suite runs on
real arm64 hardware outside a container. Run it there before you ship.

`core-macos-x86_64` has no machine and is deferred: Intel Macs are not a target for this beta.

## Before you start

The build takes hours, so run the dry run first. It builds nothing and prints what it would do:

```sh
make release-check
```

It checks the things that have each wasted a build before: a dirty tree (a release records its commit as provenance), Docker actually running, binfmt handlers for any foreign architecture, `uv`, `iconutil`, and enough disk. Disk means about 20 GB per architecture that is not already built, and 5 GB for one that is.

Fix everything it names, then read the plan it prints. It will tell you which steps are a rebuild and which are a repackage. Those are different: the core is skippable, **the payload is not**. A release once shipped an `editors.tar.gz` eighteen hours older than the licence text inside it, because the core tarball was present, the whole native half was skipped, and `dist.sh` (which repackages the theme, the branding and the attribution) never ran.

Tag before you build, so the provenance in the manifest is the tag and not a commit that only you have:

```sh
git tag -a v0.1.0 -m 'Libera Suite 0.1.0'
```

## 1. The Mac

```sh
make release
```

Which does, in order:

1. the native core if `x2t` is missing (hours, since V8 alone is ~30 minutes), then the payload, `smoke.sh` and `dist.sh`;
2. each Linux architecture in its container, exported into `$DIST`;
3. the manifest, over everything present;
4. the wheel, with the manifest stamped into it;
5. `Libera.app`;
6. the arm64 Flatpak.

A failure in one architecture is recorded, leaving the run to continue: one platform refusing to build is no reason to throw away the other five artifacts. The run ends with a list of what it failed to produce and the relevant lines from each failing log. Read that list: it is the report.

Expect it to end saying:

```
    still missing: core-macos-x86_64
    still missing: libera-0.1.0-amd64.flatpak (build it on a amd64 machine)
```

Both are correct. The first is deferred; the second is step 2.

## 2. The x86_64 Linux machine

**The bundle includes the payload**, so this box needs one built before it can make a bundle. That is a change: it used to need only the repository, Docker and `uv`.

```sh
git clone https://github.com/abilian/libera-suite && cd libera-suite
git checkout v0.1.0            # the same tag, or the artifacts do not match
make payload-linux             # core and payload in the pinned container (hours, once)
make flatpak                   # stages them into the bundle, then --diagnose inside it
```

Or, if the Mac has already built the amd64 artifacts, copy them over and skip the hours: `make flatpak` takes them from `$DIST`; `DIST=/path/to/artifacts make flatpak` points it somewhere else.

**Use `make flatpak` here.** A release run works and wastes an afternoon: it repackages a `$DIST` that is not the release. Expect this box to report `still missing: core-macos-arm64` and the rest, which is correct: it is describing its own directory.

That leaves `build/out/libera-X.Y.Z-amd64.flatpak`. `make ship ARGS=bundles` fetches it to wherever you are driving from; by hand it is one `scp`.

**Check what else is in `build/out` first.** Nothing cleans it. Every build writes a new filename, so bundles from earlier versions, including from before the product was renamed, sit there indefinitely. `make release` now lists those separately, under "NOT part of this release". Delete them, so they are not in the way at upload time.

`make flatpak` ends by installing the bundle and running `libera --diagnose` inside the sandbox, which is as far as a container goes, since there is no display in one. It proves three things: the GNOME runtime supplies GTK and WebKit, the application imports, `--diagnose` says the payload is bundled. `make flatpak-smoke` goes one further and converts a document with it.

### After it is published: `make released-gui`

Everything above tests what this machine built. Once the bundles are on the origin, one command asks the build machines whether **what a user downloads** opens a window:

```sh
make released-gui                          # every Linux builder in builders.toml
make released-gui ARGS="--on fedora.zt"    # one of them
```

`build/released-gui.sh` copies itself to each machine over ssh and installs nothing. It runs the published Flatpak under Xvfb against a blank taken out of the bundle's own payload, screenshots the result, then counts unique colours. Below two dozen the window opened empty, from a WebKit that never painted or an editor that failed to load. That is the failure which otherwise looks exactly like success. The screenshots come back to `build/out/released-gui-<platform>.png`, so the last check is a human looking at one.

On the builder it needs `xvfb-run`, `xwininfo` and ImageMagick. It also needs `flatpak` on the host itself, since the copy inside the build container is out of reach. A machine without them names which are missing, prints the line that installs them, and counts as a failure.

This is the one check that exercises the GNOME runtime's WebKit, which is a different library from the distribution's and is the one users get.

## 3. An arm64 Linux machine, if you have one

No release depends on this step. It is the only place the suite runs on real arm64 hardware:

```sh
make payload-linux             # payload in the pinned container
make test-linux                # the suite, on Linux
make gui-linux                 # a real GTK/WebKitGTK window under Xvfb, screenshotted
make released-gui              # the same, from the published bundle
make flatpak-check             # install the bundle, run --diagnose in the sandbox
```

On a small machine the build is tight on memory before it is slow. `build/payload.sh` and `build/build.sh` size themselves from the cgroup limit; a 4 GB box needs swap to finish the core (see [Build the payload](build.md)). The symptom is `Killed signal terminated program cc1plus`. The answer is `fallocate`.

## 4. Bringing it together

The manifest describes a directory, so it is written **after** every artifact has arrived, and the wheel **after** the manifest, because the wheel embeds a copy and verifies every download against it.

Within one `make release` those are already in order. Across machines they are not, which is what `make origin-collect` is for: it fetches each builder's core over ssh and stamps the manifest over the result. The wheel comes after that, which is why the runbook puts it at step 6.

The Flatpak bundles are not in the manifest, because each has its own payload, so an amd64 bundle arriving late costs nothing.

`make release` checks the agreement at the end and says so:

```
    the wheel's manifest matches the artifacts
```

If it does not, an install would reject its own payload: a hash mismatch on a tester's machine, which is a bad place to find out.

## 5. Verify before publishing

```sh
make verify                    # lint, the whole suite, docs links, the patch queue, the converter
make patches                   # the queue still applies to the pinned SHAs
```

Two things remain that no automated check covers:

- **Read the attribution out loud.** It is a licence obligation. It lives in `build/theme/libera/meta/config.json` and shows in Help ▸ About.
- **Install the payload the way a user will**, from the artifacts, and open a document with it.

## 6. Collect

A release is built on several machines: a Mac, a Linux box per architecture, and later a second Mac and a Windows box. The origin is one directory that has to hold every platform's core at once, so the cores are gathered before anything is published.

List the machines once, in `build/builders.toml`, from the committed example:

```sh
cp build/builders.toml.example build/builders.toml
make origin-collect          # DRY=1 first, to see what it would fetch
```

Each machine gives up the core named for its own platform. The shared pair, `editors.tar.gz` and `fonts-core.tar.gz`, comes from exactly one of them. There is a trap in that. Every builder produces the pair; no two machines produce it byte-for-byte, because tar records modes and order while gzip records a time. The manifest names one hash for each. A second copy arriving over the first is a hash mismatch on a tester's machine, hours later, reported there as a corrupt download.

`origin-collect` ends by re-hashing everything it gathered and stamping `src/libera/manifest.json`. An unreachable builder leaves the other transfers alone. It does stop the manifest: one missing a core publishes cleanly and tells that platform's users `manifest has no core artifact` days later.

## 7. Publish

Publish in this order, because the parts refer to each other:

1. **The payload** to `https://cdn.abilian.com/libera/`, under the payload version:

    ```sh
    export CDN_TOKEN=...          # cdn create-token, scoped to the zone
    make origin-push
    make origin-check             # QUICK=1 for sizes only
    ```

    `origin-push` refuses a manifest stamped from a dirty tree, because that manifest names no source anyone can check. `origin-check` then reads the origin back over plain HTTPS with no token and no configuration, the way a stranger's machine will, and hashes every byte against the manifest the wheel ships. `curl -T` reports success for a truncated body and for a redirect to an error page; the read-back tells the two apart.

2. **The upstream mirrors**, at the same moment the binaries go out. The AGPL obligation is a commit plus a patch series that provably applies to it; `build/pins.toml` and `build/patches/` are that series.
3. **The wheel** to PyPI (`make publish`), and then `WHEEL=pypi make origin-check`.

    That last command is the one that closes the loop: it fetches the wheel PyPI is actually serving, reads the manifest inside it, and verifies the origin against that copy. The wheel for `libera` 0.1.0 shipped naming a payload rebuilt two days later. Every check passed, because each one was looking at something correct.
4. **`Libera.app`, both `.flatpak` bundles and the Windows installer** wherever the release is downloaded from. The Windows installer goes first, from the Windows machine (`sh build/origin.sh windows`), because `make origin-extras` then publishes `install.ps1` and moves `bundles/latest`, and from that moment `install.ps1` fetches the new version's installer.
5. **This documentation**, which deploys on its own and is not part of `make ship`:

    ```sh
    cd docs && make check       # a broken link fails the build
    cd docs && make publish     # clean, build, then hop3 deploy
    ```

    `make publish` runs `hop3 deploy --context prod -y` against the app named in `docs/hop3.toml`: `libera-docs`, a static site serving `docs/site/` at `docs.liberasuite.eu`. It depends on `clean build`, so the deployed tree is never a stale one. `make deploy` is an alias. `hop3check` validates the config without touching the server.

6. **Push the tag.**

The last word belongs to the application, on a machine with no payload: `libera --payload-install`.

## When a step fails

| | |
| :--- | :--- |
| `exec format error` a minute into an image build | No binfmt handler for a foreign architecture. `docker run --privileged --rm tonistiigi/binfmt --install all`, or build that architecture on a machine that is one. |
| `Killed signal terminated program cc1plus` | The OOM killer. Add swap; the build prints the `fallocate`/`mkswap`/`swapon` lines when it detects a small machine. |
| `FATAL: heap out of memory` in a webpack | V8 sizes its heap from the cgroup limit, ignoring the work: a *smaller* container aims lower and dies sooner. `build/payload.sh` sets a floor below 6 GB; see [Build the payload](build.md). |
| A patch no longer applies | News, and something to investigate. `make patches` names it; read the upstream change before rebasing. |
| The build ran the JS pipeline unpatched | The source tree was fetched before the patch existed. `git -C $BUILD_ROOT/src/<repo> log --oneline` answers it in one line. |
| `INCOMPLETE: no editors.tar.gz` | A Linux-only run whose architectures were all already built, so nothing produced the platform-neutral half. The command to fix it is printed with the message. |
| `FATAL: artwork in the payload that is not ours` | `dist.sh` found a logo-shaped file it does not recognise. Look at it before deciding: if it is upstream's it wants removing in `build/patches/web-apps/` or writing over in `payload.sh`; if it is ours, its name goes in `OURS` in `dist.sh`. |

[Build the payload](build.md) has the reasoning behind the rest: why the container is pinned the way it is, why arm64 needs clang 13 exactly, what each silent failure cost.
