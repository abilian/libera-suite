# Cutting a release

A release is one set of artifacts that agree with each other. No single machine can produce all of them.

**A release is two commands, and `make ship` runs both.** `lb release check` builds it and installs it as users will, publishing nothing; `lb release publish` is the part with no undo. `check` has six phases: the Linux and Windows components, both Flatpak bundles and the Windows installer are built on their builders in parallel, the macOS components and the wheel here; then every file of the release is staged and installed on every platform, and the Linux converter and `install.sh`'s pip path tried in a clean container of each distribution. `publish` has five: the upload to PyPI and the CDN, two that read back what users get, then the Homebrew tap and the documentation site. `lb release check --dry-run` prints the plan and runs nothing. See [`make ship`](#make-ship) below.

Read [Build the payload](build.md) first if you have never built one. This page assumes you have.

## Start to finish

The whole of a release, in order. Each step says what to run and what has to be true before the next. The sections below are the detail behind them.

**1. Decide what ships.**

- The release plan (`notes/plans/release-X.Y.md`) has a *What X.Y needs before it ships* list. It is empty, or what is left is moved to the next plan, in writing.
- The version is set: `lb release bump X.Y.Z` writes it for `libera`, `libera-core` and `libera-web` alike, in the six places it lives, and runs `uv lock`. A version already on PyPI is never used again, since PyPI refuses it even after a yank.
- Every platform that shipped last time has a builder, and `build/builders.toml` lists it. A platform missing from a release is not just absent: once `bundles/latest` moves, `curl | sh` on that platform asks for a bundle that does not exist, and a pip install there finds no `libera-core` wheel for it. If a builder is gone, build that platform elsewhere (an Apple Silicon Mac builds the arm64 Linux core and the arm64 Flatpak, see the table below), or decide in writing to drop it, and say so on the install page.

**2. Make the tree release-ready.**

```sh
git switch main && git pull
make verify                         # lint, the whole suite, docs links, the patch queue, the converter
lb payload check                  # the queue still applies to the pinned SHAs
```

- `CHANGES.md`: the section's `Unreleased` becomes the date.
- A news post in `docs/news/<lang>/YYYY-MM-DD-libera-suite-X-Y.md`, the same file name in the five languages.
- The user pages say what is true of this version: `main/status.md` and `develop/roadmap.md` above all, in every edition where they are translated.

**3. Check it: build and stage it, publishing nothing.**

```sh
lb release check
lb on linux-x86_64 linux test --gui                           # the gui tier, WebKitGTK
lb on windows-x86_64 app test windows                   # the gui tier, WebView2
make test-gui                                               # the gui tier, here
```

`stage` gathers every file the release publishes into `build/out/release/<commit>/staged/` and installs it on every platform, as users will, then opens, types into, saves and reopens a document in each editor there (see [Stage](#stage)); the pictures are in `build/out/five-minutes/`. Nothing leaves the machines. A whole check at a commit whose builds are cached took 63 minutes on 2026-11-14, half of it `make verify`. The staged files are the ones to test by hand, for what `stage` does not do: on each platform: Save As in another format; close with unsaved changes; open a document LibreOffice has open; drop a file on a window; print; Help. Once with `ui_language` set to each translated language. On Linux the desktop is the VNC session described in `notes/15-builders.md`; on Windows, Windows App to the builder. For testers outside, a pre-release (below) does the same through the real channels without moving any of them.

**4. Tag, then publish what was staged.**

```sh
git tag -a X.Y.Z -m 'Libera Suite X.Y.Z' && git push sourcehut X.Y.Z    # no "v"
lb release publish                  # the staged files, as they are (asks on the terminal), then read back
lb release status                   # after any pause: where the release has got to
```

`publish` is the step with no undo, and it uploads the staged directory and nothing else: it refuses a stage from another commit, or one a file was added to, removed from or changed in since. Tag before checking if the tag is to be the commit the stage names. `make ship` runs `check` then `publish` in one go; the table in *The runbook, by hand* says what each phase does.

**5. Check what users get.** `publish` ends by installing the published Flatpak and Windows installer on the builders and screenshotting a window from each (its `downloads` phase; see [released-gui](#after-it-is-published-released-gui)). On a machine that has never had Libera Suite: `curl -fsSL https://cdn.abilian.com/libera/install.sh | sh` on Linux and macOS, `irm https://cdn.abilian.com/libera/install.ps1 | iex` on Windows, then open a document. `libera --payload-status` names the new payload.

**6. The channels that follow.** `publish`'s last two phases move the Homebrew tap (`tap`: the tap's generator, `make update FORMULA=libera` in its clone, then a commit and a push to the branch brew reads) and deploy the site with the news post and the pages from step 2 (`docs`: `make -C docs publish`, then the site's `build.json` read back until it names this checkout's `docs/`). Both are refused before anything is published when they could not run: a tap clone with uncommitted changes or no upstream, no `hop3`. Neither runs for a pre-release. The tap's clone is `~/projects/homebrew-tap` unless `--tap DIR` (`TAP`) says otherwise. What `make ship` does not move is the public mirror and the upstream mirrors, at the same moment as the binaries (see *Publish* below).

**7. Open the next cycle.** `pyproject.toml` goes to the next version on `main`, `CHANGES.md` gets a new `Unreleased` section, and the release plan gets its outcome in a line, with what moved to the next one.

## make ship

```sh
lb release bump X.Y.Z                                  # the version, for the three packages
lb release check --dry-run                             # the plan, running nothing
lb release check                                       # build and install everything, publish nothing
lb release check stage                                 # one phase
lb release check --only linux-arm64                    # one builder: update, components, bundles
lb release publish                                     # asks, publishes, reads back
make ship                                              # check, then publish
```

`lb release --help` lists the rest.

```
check:    update  components  bundles  wheel  stage  distros
publish:  publish  verify  downloads  tap  docs
```

The order is forced. `stage` follows everything that makes a file; `publish` uploads what `stage` stamped; `verify` and `downloads` follow `publish`, because what they check is what users get; `tap` and `docs` come last, because the tap's generator reads the release from PyPI and the site announces it. The phases run in that order whatever order they are typed in, so there is no way to get it wrong from the command line.

`publish` is the one phase with no undo, since PyPI refuses a version it has already seen even after a yank. It stops and asks on `/dev/tty` unless `--yes` is given. Asking on the terminal matters here: this is usually run under tmux with its output redirected, where a prompt on stdin is a prompt no one can answer.

Every phase checks what the machine printed, because over ssh an exit status describes the shell, including its logout scripts. Per-host logs land in `tmp/remote/`.

**A builder's job outlives the connection.** `components` and `bundles` start their job detached on the builder, in `~/.lb/runs/<platform> <command>/` there, which holds its script, its log, its pid and, once it has ended, its exit status, and poll it every 15 seconds with a connection of their own. A builder that does not answer is a poll that missed: the watch says how long it has been silent, and gives up after 45 minutes, saying the job may still be running. The same phase, run again, finds the job still running and watches it rather than starting a second build on the same tree. On Windows the job is started through PowerShell's `Start-Process`: one put in the background from Git Bash holds the ssh session open until it ends. The precheck asks each builder four times, a poll apart, before calling it unreachable. All of it measured on 2026-11-01, when builder-windows dropped off the network four times in an afternoon.

`build/builders.toml` lists the builders. `lb` is its only reader (`libera_build.inventory`), so there is one list.

## A pre-release

A version that is not plain digits and dots, such as `0.4.0rc1`, ships as a pre-release with the same `make ship`. Everything is built, checked and uploaded, and nothing a user reaches without asking moves:

- PyPI takes the wheel, and pip leaves it alone unless asked: `pipx install --pip-args=--pre libera==0.4.0rc1`, or `uv tool install --prerelease allow libera==0.4.0rc1`.
- The CDN takes the Flatpak bundles and the Windows installer under their own names, at `bundles/libera-0.4.0rc1-amd64.flatpak` and `bundles/Libera-Suite-Setup-0.4.0rc1.exe`. `bundles/latest`, `bundles/latest-windows`, the unversioned installer name and both install scripts stay as they were. `install.sh` refuses a pointer that is not digits and dots, so a pre-release that moved one would stop every `curl | sh`.
- The Homebrew tap is not updated.
- `verify` reads this version's wheel from PyPI, not PyPI's newest, which is its newest *release*.

A tester on a pre-release is told when the release comes out: the update check sorts `0.4.0rc1` below `0.4.0`.

## The runbook, by hand

What `make ship` does, phase by phase, for when part of a release has to be redone or driven from somewhere else.

**One phase needs a Mac.** `components` builds `libera-core`'s macOS wheel, which nothing else can. Everything else runs wherever you are sitting, so long as that machine has `build/builders.toml` and ssh to the builders. The Mac is one of three builders.

**Set the version first**, with `lb release bump X.Y.Z`. The three packages share it, and every release rebuilds and uploads the components, even unchanged: one number is worth that. Two numbers that moved apart are how 0.7.0 went out pinning components 0.7.1. A deliberate exception is made by hand, and `test_the_release_has_one_version_and_libera_pins_it` then says where the numbers differ.

**`lb release status`** measures where a release has got to, against the tree, the release's files on this disk and PyPI. A release runs over days and several machines, so it measures which step you are on and does not ask you to remember.

| phase | what it does | where it runs |
| :--- | :--- | :--- |
| | `git tag -a X.Y.Z && git push --tags` (no `v`: the tags are `0.3.0`, `0.3.3`), before building, so the manifest records a revision other people can fetch. Neither command does this. | anywhere |
| `update` | Send the commit you are at to each builder over ssh and check it out there, detached; refuse a dirty builder. Any branch, pushed or not: only `publish` wants the commit on a remote, because the manifest names it. | the driving machine |
| `components` | `lb components build` on each builder: its platform's `libera-core` wheel, built from the core's sdist at the pins, in parallel; hours the first time, when its build tree, a compile cache, is empty. And here, the macOS wheel, that sdist and `libera-web`'s wheel, in a build root of their own (below). All of them land in `pypi/` in the run directory (below). | each builder, and **the Mac** |
| `bundles` | The two `.flatpak` bundles (neither can be cross-built) and the Windows installer, each brought to `bundles/` in the run directory. | a machine of each platform |
| `wheel` | `make verify`, then the wheel and sdist, into `pypi/` in the run directory. | anywhere |
| `stage` | Every file `publish` uploads, copied to `staged/` in the run directory; installed on every platform from there, by the install scripts where users run them, and a window opened on each; then stamped with each file's hash. See [Stage](#stage). | the driving machine and each builder |
| `distros` | In a clean container of each distribution the install page names, and of the newest Ubuntu LTS and Fedora: the staged Linux converter, the text looked for in what it wrote; then `install.sh --channel pip` from the staged origin, which must install `libera` and convert a document where the distribution's Python is 3.12 or newer, and refuse, saying why, where it is older. | each Linux builder, with its own container engine |
| | A Windows build later than the rest: `lb release check bundles --only windows-x86_64`, then `lb release check stage`, then `publish` again, which skips what PyPI already has. | the driving machine |
| `publish` | The staged files, refused if the stamp no longer holds. Everything the CDN could refuse is refused first, the bundles signed and `bundles/latest-windows` checked, so a passphrase not given leaves the release where it was rather than half out. Then `libera-core` and `libera-web`, then `libera`, to PyPI; a file PyPI already has is skipped, so a publish that broke part way is run again. Then the bundles, with their signatures, `install.sh` and `install.ps1` to the CDN; then `bundles/latest`, which moves both install scripts to the new version. | anywhere with the credentials |
| `verify` | On every platform, `libera` installed from PyPI alone into a new environment and a document converted: what `stage` checked, now against what PyPI serves. | the driving machine and each builder |
| `downloads` | The published Flatpak and Windows installer installed on each Linux and Windows builder, a window opened and photographed (see [released-gui](#after-it-is-published-released-gui)). None for a pre-release, which moves no pointer. | each Linux and Windows builder |
| `tap` | The Homebrew formula moved to the release by the tap's own generator, which reads it from PyPI, checked to name the version, committed and pushed (`release/phases/chores.py`). None for a pre-release. | the driving machine, with the tap's clone |
| `docs` | The documentation site built and deployed (`make -C docs publish`, through `hop3`), then its `build.json` read back until it names this checkout's `docs/`. None for a pre-release. | the driving machine |

Two things are left that no command covers. The mirrors go up, and somebody installs the release on a machine that has never built it and opens a document.

Any one phase runs on its own, which is what makes a partial redo cheap. `update` to `distros` belong to `check`, `publish` to `docs` to `publish`, and each command refuses the other's. `--only`, on `check`, narrows the phases that run per builder and refuses the rest: wheel, stage and distros work on every builder at once. `publish` checks the stage's stamp before anything long starts:

```sh
lb release check stage
lb release check bundles --only linux-arm64
```

## What a release is

| Artifact | Where it goes | Built by |
| :--- | :--- | :--- |
| `libera_core-X.Y.Z-py3-none-<platform>.whl` | PyPI | each platform's builder, from the core's sdist |
| `libera_core-X.Y.Z.tar.gz` | PyPI | the Mac |
| `libera_web-X.Y.Z-py3-none-any.whl` | PyPI | the Mac |
| `libera-X.Y.Z-py3-none-any.whl` and its sdist | PyPI | the Mac, with the manifest inside |
| `libera-X.Y.Z-amd64.flatpak` and its `.asc` | the CDN | an x86_64 Linux machine, **payload included** |
| `Libera-Suite-Setup-X.Y.Z.exe` and its `.sha256` | the CDN | the Windows machine, **payload included** |
| `install.sh`, `install.ps1`, `bundles/latest*` | the CDN | this repository |

The CDN is for what does not come from PyPI: the bundles and the install scripts. Since 0.7 nothing downloads a payload from it. No phase reads a core an earlier build left: `components` builds each machine's core from the pins, its build tree only a compile cache, and the Flatpak and the Windows installer are made from components built the same way. `src/libera/payload/payload.version` holds the payload's version for the build scripts.

## Which machine can make what, and why

Three constraints have each cost somebody a build:

**There is no macOS container.** A Mac builds its own core natively. Everything else about a Mac release follows from that one fact.

**A Linux core is built in a container, whatever the host is.** `lb container run payload` exists so that a Linux payload never depends on what the host has installed. That holds on a Linux builder as much as on a Mac: the host's own architecture is one more container target, so do not build it natively there. An Apple Silicon Mac can stand in, building `linux/arm64` natively and `linux/amd64` under Rosetta, which is the fallback when a builder is unreachable.

**Flatpak bundles cannot be cross-built.** `flatpak-builder` runs every build command inside bubblewrap, which installs a seccomp filter compiled for the target architecture. Under emulation the kernel is still the host's, so it is rejected:

```
bwrap: Unable to set up system call filtering as requested:
prctl(PR_SET_SECCOMP) reported EINVAL.
```

Rosetta translates instructions; it leaves the kernel's idea of what architecture a BPF program is for alone. So each bundle is built on a machine of its own architecture, then brought here.

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

That table is what each machine *can* do. It is not how a release is built. `make ship` sends the Linux cores to the Linux builders, which is faster than a Mac emulating amd64 and is the only way to get the amd64 bundle at all, and the Windows core and installer to the Windows machine. The Mac then does one thing nothing else can, `core-macos-arm64`, and the machine you type the command on stages and publishes.

An arm64 Linux box has a second job: it is the only place the suite runs on real arm64 hardware outside a container. Run it there before you ship.

`core-macos-x86_64` has no machine and is deferred: Intel Macs are not a target for this beta.

## Before you start

Tag before you build, so the provenance in the manifest is the tag and not a commit that only you have:

```sh
git tag -a 0.1.0 -m 'Libera Suite 0.1.0'
```

Then `lb release check --dry-run`, and `lb release status` after any pause: a release runs over days and several machines.

**The Mac builds its components in a build root of their own**, `$BUILD_ROOT/release`, not in `$BUILD_ROOT`. The trees under `$BUILD_ROOT/src` are where upstream fixes are made and committed before they reach the patch queue, and the components' build fetches any tree that is not its pin plus the queue, which resets it. The release's trees hold only what `fetch` put there; the working trees serve as its `MIRROR`, so nothing already here is downloaded again. Its `out/` stays between releases as a compile cache; the editors, the themes and `dist.sh` (which repackages the theme, the branding and the attribution) are rebuilt every time. The first release built this way builds everything, V8 included. There is no `make payload` to run beforehand: a release once shipped an `editors.tar.gz` older than the licence text inside it, and another packed a build a week older than its trees, both because the payload was built by hand and only packed by the release.

## Any command, on a builder

```sh
lb on linux-x86_64 app test flatpak          # the bundle, converting under the runtime
lb on linux-arm64 --update linux lint         # this commit sent first, then the checks
```

`lb on` runs an `lb` command in a builder's checkout, as `check` runs its builds there: the output streams back; the status is read from what the builder printed. It runs the commit that checkout is at, says when that is not yours, and `--update` sends yours first. Nothing interactive works through it, since there is no terminal at the other end.

## On an arm64 Linux builder

No release depends on this. It is the only place the suite runs on real arm64 hardware:

```sh
lb container run payload --arch arm64            # payload in the pinned container
lb linux test                                # the suite, on Linux, with that payload
lb linux screenshot                                 # a real GTK/WebKitGTK window under Xvfb, screenshotted
lb app check flatpak                         # install the bundle, run --diagnose in the sandbox
```

On a small machine the build is tight on memory before it is slow. `build/engine/payload.sh` and `build/engine/build.sh` size themselves from the cgroup limit; a 4 GB box needs swap to finish the core (see [Build the payload](build.md)). The symptom is `Killed signal terminated program cc1plus`. The answer is `fallocate`.

`lb app build flatpak` ends by installing the bundle and running `libera --diagnose` inside the sandbox, which is as far as a container goes, since there is no display in one. It proves three things: the GNOME runtime supplies GTK and WebKit, the application imports, `--diagnose` says the payload is bundled. `lb app test flatpak` goes one further and converts a document with it.

**`build/out` keeps what every build left**, since each writes a new filename: bundles from earlier versions, and the run directories of earlier commits. None of it can be published, since `publish` uploads the stage of this commit and nothing else, but it takes room: `lb tidy` lists it and removes it.

## After it is published: released-gui

`stage` tests what is about to be published. Once the bundles are on the CDN, `publish`'s last phase asks the build machines whether **what a user downloads** opens a window, and runs again on its own as `lb release publish downloads`.

It copies a script to each machine over ssh, and the script installs what the CDN serves now, the way a user would get it. **It never tests what happens to be installed there**: 0.7.0 was once declared to draw a window by a 0.5.0 left on the builder.

**On Linux**, `build/install/released-gui.sh` runs `install.sh` from the CDN into a Flatpak installation of its own, under `~/.cache/libera-released-gui/`, so the machine's own Libera Suite stays as it is, and refuses a `--version` that is not the release `bundles/latest` names. It runs the bundle under Xvfb against a blank taken out of its own payload, screenshots the result, then counts unique colours, and then spends [five minutes in each editor](#stage). Below two dozen the window opened empty, from a WebKit that never painted or an editor that failed to load. That is the failure which otherwise looks exactly like success. Its verdict is the line it prints, `__LIBERA__=ok` or the reason, never ssh's exit status. The screenshots come back to `build/out/released-gui-<platform>.png`, so the last check is a human looking at one.

**On Windows**, `build/install/released-gui.ps1` runs `install.ps1` from the CDN, which replaces that account's Libera Suite, and refuses a `--version` that is not the one `bundles/latest-windows` names. It converts a document from Markdown to docx and back to text and looks for its words. Then it opens the document in the desktop session, through a scheduled task, since ssh's session has no desktop, and screenshots it DPI-aware. It counts the colours the same way, and fails a window that does not fit the screen. A locked screen draws nothing: it says so, and counts as a failure.

A Linux builder needs `xvfb-run`, `xwininfo` and ImageMagick. It also needs `flatpak` on the host itself, since the copy inside the build container is out of reach. A machine without them names which are missing, prints the line that installs them, and counts as a failure.

This is the one check that exercises the GNOME runtime's WebKit, which is a different library from the distribution's and is the one users get.

## The run directory

Everything a release gathers on the driving machine goes under `build/out/release/<commit>/`, named by the full commit: `pypi/` (the components from every builder, `libera`'s wheel and sdist), `bundles/` (the Flatpaks and the Windows installer) and `staged/`. No phase reads another commit's directory, so a wheel or a bundle an earlier run left cannot be staged as this one's: a phase not run at this commit is a file missing, and `stage` says which phase makes it. `lb release publish` and `lb release status` read the same directory. A commit, even one touching only the docs, means running the phases again; `lb tidy` removes the directories old commits left. A commit made *during* a run stops it after the phase that saw HEAD move, naming both commits: what that phase made is filed under the commit it started from.

## Stage

0.7.0b1 and 0.7.0 both went to PyPI before anything had installed them, and both were broken there: the first without its components, the second before them, so `uvx libera` quietly installed 0.6.0. `stage` is where a release is installed before it is published.

It copies every file `publish` will upload into `staged/` in the run directory: the components, `libera`'s wheel and sdist, the Flatpak bundle and the Windows installer. Beside it, `origin/` holds the same files laid out as the CDN zone (`build/src/libera_build/origin/staged.py`): `install.sh` and `install.ps1` at the root, the bundles and the `latest` and `latest-windows` pointers under `bundles/`, and the three packages under `pypi/`. Each test machine is sent its part and serves it to itself on `127.0.0.1`, as the CDN serves it, so the install page's own command runs against it with one setting changed, `LIBERA_ORIGIN` (and `LIBERA_VERSION` for a pre-release, which no pointer names). Then:

- **On each builder**, `libera` installs into a new environment the way pip installs it, its third-party requirements from PyPI first, then `libera`, `libera-core` and `libera-web` with no index at all, so that nothing but the staged files can satisfy them. It converts a document and reads the text back.
- **On this Mac**, `install.sh` from the staged origin, under a home of its own: pip takes the three packages from `pypi/` (`PIP_FIND_LINKS`) and everything else from PyPI, as it will. It converts a document, and a window opens, whose page photographs its canvas (`libera --shot`), which needs no screen-recording permission. Then five minutes in each editor, below, and `--launcher-remove` takes the `Libera.app` it wrote out of LaunchServices.
- **On each Linux builder**, `released-gui.sh` runs `install.sh` from the staged origin, which installs the Flatpak into an installation of its own, and opens a document under Xvfb; then five minutes in each editor, below, with the Flatpak's own Python.
- **On the Windows builder**, `released-gui.ps1` runs `install.ps1` from the staged origin, which checks the installer against its `.sha256` and runs it; then it converts a document and opens a window in the desktop session (see [released-gui](#after-it-is-published-released-gui)); then five minutes in each editor, below.

**Five minutes in each editor** (`build/install/five-minutes.sh`) is a user's first use: a blank opened in Words, Tables and Slides, a line entered and saved, the line looked for in the file written, then the file opened again in a new window, whose page photographs itself. It drives each window with the gui tier's driver (`tests/d_gui/driver.py`), run in the installed application's own Python (the virtualenv `install.sh` made on the Mac, `flatpak run --command=python3` on Linux), so the web engine, the host and the payload are the ones users got. The text is entered through the editor's API, not typed. The pictures land in `build/out/five-minutes/<platform>-<ext>.png`, for a person to look at. On Windows the installer's application is frozen and has no Python to run the driver in, so `build/install/five-minutes-windows.py` runs the driver's same steps from outside: each window is started with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=N` and driven over the DevTools protocol, and its page photographed with `Page.captureScreenshot`. Nothing in the product changes for it.

Only when all of it passed is the directory stamped: `STAGED.json`, with the commit and each file's SHA-256. `publish` uploads that directory and refuses one whose stamp no longer holds; after another commit there is nothing staged, since the directory is that commit's. `stage` can be run as often as needed; nothing leaves the machines.

The release's provenance, the upstream pins and the commit, is in `libera-web`'s `payload.json`, which its build writes from the manifest `dist.sh` stamps; `libera --payload-status` and the start window show it. `libera`'s own wheel carries no manifest since 0.7.2: nothing read it after 0.6, and it was put there by hand.

## Verify before publishing

```sh
make verify                    # lint, the whole suite, docs links, the patch queue, the converter
lb payload check                            # the queue still applies to the pinned SHAs
```

`stage` installs the release on every platform. One thing remains that no automated check covers: **read the attribution out loud.** It is a licence obligation. It lives in `build/payload/theme/libera/meta/about.json` and `src/libera/host/about.py`, and shows in the editor's About panel and in Help ▸ About.

## Publish

`publish` does this in this order, from the staged directory, because the parts refer to each other:

1. **The packages** to PyPI: `libera-core` (a wheel per platform and its sdist) and `libera-web` first, then `libera`, with `uv publish --check-url https://pypi.org/simple/`. `make publish` uploads `libera` alone, which is not a release, and refuses one whose components PyPI does not have yet: 0.7.0b1 and 0.7.0 went up that way.
2. **The bundles and the Windows installer** to the CDN (`CDN_TOKEN`, scoped to the zone). `publish` first signs each bundle here with the release key (`SIGNING_KEY` in `origin/publish.py`), which may ask its passphrase, and puts the signature beside it as `.asc`; without a good signature nothing goes up, and `publish` refuses at the start when gpg does not have the key. The Windows installer goes up with the rest when it was staged, or with a later `publish` once checked: each pointer, `bundles/latest-windows` for `install.ps1` and `bundles/latest` for `install.sh`, moves only once the files it names are up. A release whose Windows build is a week late ships its Flatpaks today; Windows users keep the previous version until the installer goes up.
3. **The upstream mirrors**, at the same moment the binaries go out, by hand. The AGPL obligation is a commit plus a patch series that provably applies to it; `build/upstream/pins.toml` and `build/upstream/patches/` are that series.
4. **This documentation**, which deploys on its own and is not part of `make ship`:

    ```sh
    cd docs && make check       # a broken link fails the build
    cd docs && make publish     # clean, build, then hop3 deploy
    ```

    `make publish` runs `hop3 deploy --context prod -y` against the app named in `docs/hop3.toml`: `libera-docs`, a static site serving `docs/site/` at `docs.liberasuite.eu`. It depends on `clean build`, so the deployed tree is never a stale one. `make deploy` is an alias. `hop3check` validates the config without touching the server.

5. **Push the tag.**

The last word belongs to the application, on a machine that never built it: `verify` installs it from PyPI and converts, and nothing opens a window, so `pipx install libera==<version>` (with `--pip-args=--pre` for a pre-release), then a document opened. `make ship` prints that line at the end.

## When a step fails

| | |
| :--- | :--- |
| `exec format error` a minute into an image build | No binfmt handler for a foreign architecture. `docker run --privileged --rm tonistiigi/binfmt --install all`, or build that architecture on a machine that is one. |
| `Killed signal terminated program cc1plus` | The OOM killer. Add swap; the build prints the `fallocate`/`mkswap`/`swapon` lines when it detects a small machine. |
| `FATAL: heap out of memory` in a webpack | V8 sizes its heap from the cgroup limit, ignoring the work: a *smaller* container aims lower and dies sooner. `build/engine/payload.sh` sets a floor below 6 GB; see [Build the payload](build.md). |
| A patch no longer applies | News, and something to investigate. `lb payload check` names it; read the upstream change before rebasing. |
| The build ran the JS pipeline unpatched | The source tree was fetched before the patch existed. `git -C $BUILD_ROOT/src/<repo> log --oneline` answers it in one line. |
| `FATAL: artwork in the payload that is not ours` | `dist.sh` found a logo-shaped file it does not recognise. Look at it before deciding: if it is upstream's it wants removing in `build/upstream/patches/web-apps/` or writing over in `payload.sh`; if it is ours, its name goes in `OURS` in `dist.sh`. |

[Build the payload](build.md) has the reasoning behind the rest: why the container is pinned the way it is, why arm64 needs clang 13 exactly, what each silent failure cost.
