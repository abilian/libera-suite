# Cutting a release

A release is one set of artifacts that agree with each other. No single machine can produce all of them.

**`make ship` is how a release is cut now.** One command drives ten phases: the Linux and Windows cores, both Flatpak bundles and the Windows installer are built on their builders in parallel, the macOS core and the wheel here, then the origin and PyPI. `lb release plan` prints the plan and runs nothing. See [`make ship`](#make-ship) below.

Read [Build the payload](build.md) first if you have never built one. This page assumes you have.

## Start to finish

The whole of a release, in order. Each step says what to run and what has to be true before the next. The sections below are the detail behind them.

**1. Decide what ships.**

- The release plan (`notes/plans/release-X.Y.md`) has a *What X.Y needs before it ships* list. It is empty, or what is left is moved to the next plan, in writing.
- The two versions are settled. `pyproject.toml` is the application's (`0.5.0`). `src/libera/payload/payload.version` is the payload's (`0.5`), and it moves only when the payload changed. A payload version already published is never rebuilt: a new payload takes a new number.
- Every platform that shipped last time has a builder, and `build/builders.toml` lists it. A platform missing from a release is not just absent: once `bundles/latest` moves, `curl | sh` on that platform asks for a bundle that does not exist, and a pip install there finds no core in the manifest. If a builder is gone, build that platform elsewhere (an Apple Silicon Mac builds the arm64 Linux core and the arm64 Flatpak, see the table below), or decide in writing to drop it, and say so on the install page.

**2. Make the tree release-ready.**

```sh
git switch devel && git pull
make verify                         # lint, the whole suite, docs links, the patch queue, the converter
lb payload patches                  # the queue still applies to the pinned SHAs
```

- `CHANGES.md`: the section's `Unreleased` becomes the date.
- A news post in `docs/news/<lang>/YYYY-MM-DD-libera-suite-X-Y.md`, the same file name in the five languages.
- The user pages say what is true of this version: `main/status.md` and `develop/roadmap.md` above all, in every edition where they are translated.

**3. Test the real application on every platform, from artifacts.** The automated tiers cover a lot, not a person opening documents. Build the installers without publishing anything:

```sh
lb on linux-x86_64 --update payload container
lb on linux-x86_64 app flatpak --arch amd64                  # → ~/muchado/build/out/libera-X.Y.Z-amd64.flatpak
lb on windows-x86_64 --update payload all
lb on windows-x86_64 app windows                            # → C:\b\out\windows\Libera-Suite-Setup-X.Y.Z.exe
lb on linux-x86_64 linux gui-test                           # the gui tier, WebKitGTK
lb on windows-x86_64 app windows-gui-test                   # the gui tier, WebView2
make test-gui                                               # the gui tier, here
```

Then by hand, on each platform: open a `.docx`, a `.xlsx` and a `.pptx`; type, save, Save As in another format; close with unsaved changes; open a document LibreOffice has open; drop a file on a window; print; Help. Once with `ui_language` set to each translated language. On Linux the desktop is the VNC session described in `notes/15-builders.md`; on Windows, Windows App to the builder. For testers outside, a pre-release (below) does the same through the real channels without moving any of them.

**4. Tag, then ship.**

```sh
git tag -a X.Y.Z -m 'Libera Suite X.Y.Z' && git push sourcehut X.Y.Z    # no "v"
lb release plan                     # what will run
make ship                           # update … publish (asks on the terminal) … verify
lb release status                   # after any pause: where the release has got to
```

`publish` is the step with no undo. If a phase fails, fix it and run that phase again (`lb release ship collect push check`); the table in *The runbook, by hand* says what each one does.

**5. Check what users get.**

```sh
lb release released-gui             # the published Flatpak, screenshotted on each Linux builder
```

On a machine that has never had Libera Suite: `curl -fsSL https://cdn.abilian.com/libera/install.sh | sh` on Linux and macOS, `irm https://cdn.abilian.com/libera/install.ps1 | iex` on Windows, then open a document. `libera --payload-status` names the new payload.

**6. The channels `make ship` does not move.**

- Homebrew: `cd ~/projects/homebrew-tap && make update FORMULA=libera`, read the diff, then commit and push there. Brew's users see nothing until the push.
- The public mirror and the upstream mirrors, at the same moment as the binaries (see *Publish* below).
- The site: `make docs-publish`, which deploys `docs.liberasuite.eu` with the news post and the pages from step 2.

**7. Open the next cycle.** `pyproject.toml` goes to the next version on `devel`, `CHANGES.md` gets a new `Unreleased` section, and the release plan gets its outcome in a line, with what moved to the next one.

## make ship

```sh
lb release plan                                        # the plan, running nothing
make ship                                              # all ten phases
lb release ship collect push check                     # some of them
lb release ship --only linux-arm64                     # one builder: update, native, build, bundles
```

`make ship` is `lb release ship`; `lb release --help` lists the rest.

```
update  native  build  collect  push  check  bundles  wheel  publish  verify
```

The order is forced. `wheel` follows `collect`, because the wheel embeds the manifest `collect` stamps over every core; `verify` follows `publish`, because what it checks is the *published* wheel against the *published* payload. The phases run in that order whatever order they are typed in, so there is no way to get it wrong from the command line.

`publish` is the one phase with no undo, since PyPI refuses a version it has already seen even after a yank. It stops and asks on `/dev/tty` unless `--yes` is given. Asking on the terminal matters here: this is usually run under tmux with its output redirected, where a prompt on stdin is a prompt no one can answer.

Every phase checks what the machine printed, because over ssh an exit status describes the shell, including its logout scripts. Per-host logs land in `tmp/remote/`.

`build/builders.toml` lists the builders. It is gitignored because it is an inventory of machines, so copy `builders.toml.example` once. `lb` is its only reader (`libera_build.inventory`), so there is one list.

## A pre-release

A version that is not plain digits and dots, such as `0.4.0rc1`, ships as a pre-release with the same `make ship`. Everything is built, checked and uploaded, and nothing a user reaches without asking moves:

- PyPI takes the wheel, and pip leaves it alone unless asked: `pipx install --pip-args=--pre libera==0.4.0rc1`, or `uv tool install --prerelease allow libera==0.4.0rc1`.
- The origin takes the payload under its version, the Flatpak bundles and the Windows installer under their own names, at `bundles/libera-0.4.0rc1-amd64.flatpak` and `bundles/Libera-Suite-Setup-0.4.0rc1.exe`. `bundles/latest`, `bundles/latest-windows`, the unversioned installer name and both install scripts stay as they were. `install.sh` refuses a pointer that is not digits and dots, so a pre-release that moved one would stop every `curl | sh`.
- The Homebrew tap is not updated.
- `verify` reads this version's wheel from PyPI, not PyPI's newest, which is its newest *release*.

A tester on a pre-release is told when the release comes out: the update check sorts `0.4.0rc1` below `0.4.0`.

**The payload a pre-release pushes is the release's.** Its wheel names those files' hashes, and `push` overwrites what is there, so a rebuilt payload pushed under the same version would fail every later install of the pre-release (a tarball stores the time it was made, so a rebuild never hashes the same). The release that follows ships the same payload files, with `collect` and `check` and no `build` or `push`; a payload that has to change takes a new payload version.

## The runbook, by hand

What `make ship` does, phase by phase, for when part of a release has to be
redone or driven from somewhere else.

**One phase needs a Mac.** `native` builds `core-macos-arm64`, which nothing
else can. Everything below it runs wherever you are sitting, so long as that
machine has `build/builders.toml` and ssh to the builders. The Mac is one of
three builders.

**Settle the two versions first.** `pyproject.toml` moves every release.
`src/libera/payload/payload.version` moves only when the payload itself changed.
The host and the build both read it, so there is no second copy to keep in
step. Rebuilding a payload under a version that is already published overwrites artifacts a published wheel verifies against:
that is how 0.1.0 broke.

**`lb release status`** measures where a release has got to, against the
tree, the artifacts on this disk, the origin and PyPI, then prints the next
command. A release runs over days and several machines, so it measures which
step you are on and does not ask you to remember.

| phase | what it does | where it runs |
| :--- | :--- | :--- |
| | `git tag -a X.Y.Z && git push --tags` (no `v`: the tags are `0.3.0`, `0.3.3`), before building, so the manifest records a revision other people can fetch. `ship` does not do this. | anywhere |
| `update` | Send the commit you are at to each builder over ssh and check it out there, detached; refuse a dirty builder. Any branch, pushed or not: only `push` and `publish` want the commit on a remote, because the manifest names it. | the driving machine |
| `native` | The macOS core and its tarballs. | **a Mac, and only this** |
| `build` | The Linux and Windows cores, on their own machines, in parallel. Hours. | the Linux and Windows builders |
| `collect` | Fetch every core to the driving machine, then stamp `src/libera/manifest.json` over the whole set. | the driving machine |
| `push` | Upload the payload to the origin. Needs `CDN_TOKEN`. | anywhere |
| `check` | Fetch it all back with no token and verify every hash. | anywhere |
| `bundles` | The two `.flatpak` bundles (neither can be cross-built) and the Windows installer, each brought to the driving machine. | a machine of each platform |
| `wheel` | `make verify`, then the wheel. After `collect`, always. | anywhere |
| | A Windows build later than the rest, on its own: `lb release ship bundles --only windows-x86_64`, then `lb release windows`, which moves only its own pointer. | the driving machine |
| `publish` | The wheel to PyPI; the bundles, `install.sh` and `install.ps1` to the origin; then `bundles/latest`, which moves both install scripts to the new version. | anywhere with the credentials |
| `verify` | Read the *published* wheel back and check it against the origin. The check 0.1.0 needed. | anywhere |

Two things are left that no command covers. The mirrors go up, and somebody
runs `libera --payload-install` on a machine that has never built it.

Any one phase runs on its own, which is what makes a partial redo cheap. `--only` narrows the phases that run per builder, and refuses the rest: collect, push, check, wheel, publish and verify work on every builder at once. `publish` also wants `check` in the same run, and a manifest collected from this commit for this payload version:

```sh
lb release ship collect push check
lb release ship bundles --only linux-arm64
```

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

The tarballs go to `$BUILD_ROOT/out/dist/$PAYLOAD_VERSION`, which is `0.2` today and **not** the application version, `0.2.0`. The two reading 0.2 at the same time is a coincidence of counting. `src/libera/payload/payload.version` and `pyproject.toml` move independently on purpose: a host fix should not force everyone to re-download 120 MB; a payload rebuilt from new upstream pins should not need a host release.

## Which machine can make what, and why

Three constraints have each cost somebody a build:

**There is no macOS container.** A Mac builds its own core natively. Everything else about a Mac release follows from that one fact.

**A Linux core is built in a container, whatever the host is.** `lb payload container` exists so that a Linux payload never depends on what the host has installed. That holds on a Linux builder as much as on a Mac: the host's own architecture is one more container target, so do not build it natively there. An Apple Silicon Mac can stand in, building `linux/arm64` natively and `linux/amd64` under Rosetta, which is the fallback when a builder is unreachable.

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
Mac emulating amd64 and is the only way to get the amd64 bundle at all, and the
Windows core and installer to the Windows machine. The Mac
then does one thing nothing else can, `core-macos-arm64`, and the machine you
type the command on does the collecting and the publishing.

An arm64 Linux box has a second job: it is the only place the suite runs on
real arm64 hardware outside a container. Run it there before you ship.

`core-macos-x86_64` has no machine and is deferred: Intel Macs are not a target for this beta.

## Before you start

Tag before you build, so the provenance in the manifest is the tag and not a commit that only you have:

```sh
git tag -a 0.1.0 -m 'Libera Suite 0.1.0'
```

Then `lb release plan`, and `lb release status` after any pause: a release runs over days and several machines.

**The payload is never skippable.** A release once shipped an `editors.tar.gz` eighteen hours older than the licence text inside it, because the core tarball was present, the whole native half was skipped, and `dist.sh` (which repackages the theme, the branding and the attribution) never ran. `native` runs `lb payload dist` for that reason, every time.

## Any command, on a builder

```sh
lb on linux-x86_64 app flatpak-smoke          # the bundle, converting under the runtime
lb on linux-arm64 --update linux lint         # this commit sent first, then the checks
```

`lb on` runs an `lb` command in a builder's checkout, as `ship` runs its builds there: the output streams back; the status is read from what the builder printed. It runs the commit that checkout is at, says when that is not yours, and `--update` sends yours first. Nothing interactive works through it, since there is no terminal at the other end.

## On an arm64 Linux builder

No release depends on this. It is the only place the suite runs on real arm64 hardware:

```sh
lb payload container --arch arm64            # payload in the pinned container
lb payload install                           # installed the way a user does
lb linux test                                # the suite, on Linux
lb linux gui                                 # a real GTK/WebKitGTK window under Xvfb, screenshotted
lb app flatpak-check                         # install the bundle, run --diagnose in the sandbox
```

On a small machine the build is tight on memory before it is slow. `build/engine/payload.sh` and `build/engine/build.sh` size themselves from the cgroup limit; a 4 GB box needs swap to finish the core (see [Build the payload](build.md)). The symptom is `Killed signal terminated program cc1plus`. The answer is `fallocate`.

`lb app flatpak` ends by installing the bundle and running `libera --diagnose` inside the sandbox, which is as far as a container goes, since there is no display in one. It proves three things: the GNOME runtime supplies GTK and WebKit, the application imports, `--diagnose` says the payload is bundled. `lb app flatpak-smoke` goes one further and converts a document with it.

**Check what else is in `build/out` first.** Nothing cleans it. Every build writes a new filename, so bundles from earlier versions, including from before the product was renamed, sit there indefinitely. Delete them, so they are not in the way at upload time.

## After it is published: released-gui

Everything above tests what a machine built. Once the bundles are on the origin, one command asks the build machines whether **what a user downloads** opens a window:

```sh
lb release released-gui                           # every Linux builder in builders.toml
lb release released-gui --on fedora.zt            # one of them
```

It copies `build/install/released-gui.sh` to each machine over ssh, and the script installs nothing. It runs the published Flatpak under Xvfb against a blank taken out of the bundle's own payload, screenshots the result, then counts unique colours. Below two dozen the window opened empty, from a WebKit that never painted or an editor that failed to load. That is the failure which otherwise looks exactly like success. Its verdict is the line it prints, `__LIBERA__=ok` or the reason, never ssh's exit status. The screenshots come back to `build/out/released-gui-<platform>.png`, so the last check is a human looking at one.

On the builder it needs `xvfb-run`, `xwininfo` and ImageMagick. It also needs `flatpak` on the host itself, since the copy inside the build container is out of reach. A machine without them names which are missing, prints the line that installs them, and counts as a failure.

This is the one check that exercises the GNOME runtime's WebKit, which is a different library from the distribution's and is the one users get.

## Why the manifest comes last

The manifest describes a directory, so it is written **after** every artifact has arrived, and the wheel **after** the manifest, because the wheel embeds a copy and verifies every download against it. Across machines that order is what `lb release collect` is for: it fetches each builder's core over ssh and stamps the manifest over the result, and `ship` builds the wheel after it.

The Flatpak bundles are not in the manifest, because each has its own payload, so an amd64 bundle arriving late costs nothing.

If the wheel's manifest and the artifacts disagree, an install would reject its own payload: a hash mismatch on a tester's machine, which is a bad place to find out. `verify` reads the published wheel back to catch exactly that.

## Verify before publishing

```sh
make verify                    # lint, the whole suite, docs links, the patch queue, the converter
lb payload patches                            # the queue still applies to the pinned SHAs
```

Two things remain that no automated check covers:

- **Read the attribution out loud.** It is a licence obligation. It lives in `build/payload/theme/libera/meta/config.json` and shows in Help ▸ About.
- **Install the payload the way a user will**, from the artifacts, and open a document with it.

## Collect

A release is built on several machines: a Mac, a Linux box per architecture, and a Windows machine (see [Build](build.md#windows)). The origin is one directory that has to hold every platform's core at once, so the cores are gathered before anything is published.

List the machines once, in `build/builders.toml`, from the committed example:

```sh
cp build/builders.toml.example build/builders.toml
lb release collect --dry-run            # to see what it would fetch, then without
```

Each machine gives up the core named for its own platform. The shared pair, `editors.tar.gz` and `fonts-core.tar.gz`, comes from exactly one of them. There is a trap in that. Every builder produces the pair; no two machines produce it byte-for-byte, because tar records modes and order while gzip records a time. The manifest names one hash for each. A second copy arriving over the first is a hash mismatch on a tester's machine, hours later, reported there as a corrupt download.

`collect` ends by re-hashing everything it gathered and stamping `src/libera/manifest.json`. An unreachable builder leaves the other transfers alone. It does stop the manifest: one missing a core publishes cleanly and tells that platform's users `manifest has no core artifact` days later.

## Publish

Publish in this order, because the parts refer to each other:

1. **The payload** to `https://cdn.abilian.com/libera/`, under the payload version:

    ```sh
    export CDN_TOKEN=...          # cdn create-token, scoped to the zone
    lb release push
    lb release check                      # --quick for sizes only
    ```

    `push` refuses a manifest stamped from a dirty tree, because that manifest names no source anyone can check. `check` then reads the origin back over plain HTTPS with no token and no configuration, the way a stranger's machine will, and hashes every byte against the manifest the wheel ships. `curl -T` reports success for a truncated body and for a redirect to an error page; the read-back tells the two apart.

2. **The upstream mirrors**, at the same moment the binaries go out. The AGPL obligation is a commit plus a patch series that provably applies to it; `build/upstream/pins.toml` and `build/upstream/patches/` are that series.
3. **The wheel** to PyPI (`make publish`), and then `lb release check --wheel pypi`.

    That last command is the one that closes the loop: it fetches the wheel PyPI is actually serving, reads the manifest inside it, and verifies the origin against that copy. The wheel for `libera` 0.1.0 shipped naming a payload rebuilt two days later. Every check passed, because each one was looking at something correct.
4. **`Libera.app`, both `.flatpak` bundles and the Windows installer** wherever the release is downloaded from. The Windows installer goes up with `lb release extras` when `ship`'s `bundles` brought it, or later on its own with `lb release windows`: each moves its own pointer, `bundles/latest-windows` for `install.ps1` and `bundles/latest` for `install.sh`, and each moves it only once the files it names are up. A release whose Windows build is a week late ships its Flatpaks today; Windows users keep the previous version until the installer goes up.
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
| `FATAL: heap out of memory` in a webpack | V8 sizes its heap from the cgroup limit, ignoring the work: a *smaller* container aims lower and dies sooner. `build/engine/payload.sh` sets a floor below 6 GB; see [Build the payload](build.md). |
| A patch no longer applies | News, and something to investigate. `lb payload patches` names it; read the upstream change before rebasing. |
| The build ran the JS pipeline unpatched | The source tree was fetched before the patch existed. `git -C $BUILD_ROOT/src/<repo> log --oneline` answers it in one line. |
| `INCOMPLETE: no editors.tar.gz` | A Linux-only run whose architectures were all already built, so nothing produced the platform-neutral half. The command to fix it is printed with the message. |
| `FATAL: artwork in the payload that is not ours` | `dist.sh` found a logo-shaped file it does not recognise. Look at it before deciding: if it is upstream's it wants removing in `build/upstream/patches/web-apps/` or writing over in `payload.sh`; if it is ours, its name goes in `OURS` in `dist.sh`. |

[Build the payload](build.md) has the reasoning behind the rest: why the container is pinned the way it is, why arm64 needs clang 13 exactly, what each silent failure cost.
