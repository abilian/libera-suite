# Build the payload

The payload is built from pinned upstream sources plus our patches, on your own machine or on a build host you can reach. The only CI is a Windows probe that answers cheap questions on a hosted runner; nothing is gated on it.

## What you need

```sh
lb toolchain install              # what it will install: build/engine/toolchain.sh list
lb toolchain check                # what is missing, and the line that installs it
```

Debian, Fedora and Arch have measured package names. openSUSE is a best-effort mapping. On anything else `toolchain-check` names the tools and leaves the package manager to you. On **macOS** it comes to the Xcode command line tools plus CMake, Ninja and Node 20.

Every payload target depends on `toolchain-check`. Each thing it looks for otherwise fails late and in somebody else's words: a missing `glib2-devel` stops V8's `gn gen` *after* depot_tools has fetched V8, which took 991 seconds on Fedora 43, and a missing `libstdc++-static` arrives as a message about namespaces. `build/engine/toolchain.sh` holds the one list, which the container image checks against too.

**A native build needs an old clang, which most distributions no longer have.** V8 8.9 does not compile under clang 16 or later, so `toolchain-check` refuses anything newer. Fedora 43 defaults to clang 21. It packages `clang15`, which is the newest V8 accepts, but no matching `lld15`, so there is no complete toolchain there to point the build at. Use the container, which pins clang 14 and is the release path anyway.

`clang` and `lld` are **not optional**, even though everything else builds with gcc. V8's `nc-build.py` aborts with `Tool not found: clang` before compiling anything. Its gn args set `is_clang=true` and `use_lld=true`, then run ninja with `CC=clang CXX=clang++`. Neither `build-essential` nor the Fedora development group provides them.

`llvm` comes with them, for one binary: `is_clang=true` makes `gcc_toolchain.gni` set `ar` to `llvm-ar`, which Ubuntu ships in the `llvm` package. Without it V8 compiles a hundred files and then fails at the first `AR` step with `/usr/bin/llvm-ar: not found`: a path, with no package name anywhere in it.

Fedora needs `perl-core`, because OpenSSL's `Configure` needs `FindBin` and `IPC::Cmd`, which the minimal `perl` package leaves out.

`libglib2.0-dev` / `glib2-devel` is V8's, and the one to be suspicious about. V8's Linux gn args set `use_sysroot=false`, so it compiles against whatever glib the host has, with no downloaded sysroot in the way. `gn gen` then fails before anything compiles if the four `.pc` files are missing. On the laptop this was written on, `pkg-config --modversion glib-2.0` answered from **Homebrew**: a native build would have linked V8 against linuxbrew headers, with nothing on screen to say so, which is the argument for the container.

`python-is-python3` on Debian, `python-unversioned-command` on Fedora: boost's `nc-build.py` runs bare `python` to drive boostdep's `depinst.py`; Ubuntu has shipped no `/usr/bin/python` since 20.04. The failure is a `FileNotFoundError: 'python'` out of the middle of a traceback that never names boost.

`libstdc++-static` is split out on Fedora as well. Its absence looks like this: ICU's Linux configure line is `CXXFLAGS=-static-libstdc++ -static-libgcc` (`Common/3dParty/icu/nc-build.py`), Fedora ships `libstdc++.a` in a package of its own, and Debian's `g++` includes it. Without it the first C++ link in `configure` fails with `cannot find -lstdc++`. That link happens to be the namespace probe, so configure reports `Namespace support is required to build ICU`, which says nothing about static linking. The real error is in `config.log`, in the work tree.

On **Linux arm64 only**, V8 8.9 demands clang **13 exactly** and aborts on anything else (`nc-build.py`, around the `targetarch == "arm64"` check). x86_64 has no version gate. Ubuntu 24.04 has no clang 13 at all; its packages start at 14. That is one of the two reasons the container base is 22.04, where `lb container run payload` (`libera_build/buildbox.py`) picks clang 13 for arm64 and 14 for x86_64 off one image.

Either way you also need time and disk. **V8 is built from source**, on every platform, and takes about half an hour in a build tree of several gigabytes. `Common/3dParty/v8/hashes.txt` lists cache keys for a Nextcloud store that wants credentials we do not have, so upstream's `ensure_dep` finds nothing and falls through to building it.

`git` needs a configured `user.email` and `user.name`, because applying the patch queue is the first thing the build does and `git am` makes commits.

Set `BUILD_ROOT` to somewhere with room. It defaults to `$HOME/euro-office-build` on Linux, and on macOS to an external case-sensitive volume, because the internal disk is case-insensitive and V8's checkout does not come through that intact. `build.sh` checks for it and refuses at the start.

```sh
export BUILD_ROOT=/somewhere/with/room
```

## The Mac does not build V8

doctrenderer, the part of x2t that runs the editors' code (PDF, HTML, Markdown and EPUB export, and printing), runs it in macOS's own JavaScriptCore. Upstream abstracts the engine behind `js_internal/js_base.h` and ships two implementations, `v8` and `jsc`; its CMake build has `USE_JAVASCRIPT_CORE` for the second, and core `0210` makes the option leave V8 out of the build and the link. `build.sh` sets it on macOS.

It is not a preference: V8 14.6, which Euro-Office's `main` builds, needs a libc++ with `std::atomic_ref`, which only the macOS 15.4 SDK has, and Xcode 16.3 needs macOS 15. Measured on 30 documents against V8 (`lb fidelity`), it prints the same pages, and each such conversion takes about 0.7 s longer, the time JavaScriptCore takes to compile sdkjs with no code cache. See `notes/19-js-engine.md` in the development repository for the numbers.

None of this reaches Linux, where `jsc_base.mm` does not apply: it is Objective-C++ and links a framework. WebKitGTK ships a JavaScriptCore with a C API, which would be a third implementation of `js_base.h`, written from scratch against that API.

## The steps

```sh
make payload       # the whole chain, ending in the smoke check
```

Take them one at a time the first time on a new machine: `configure` surfaces missing tools and CMake gaps in minutes, before a forty-minute build reaches them:

```sh
lb payload build fetch                # clone or reset to the pinned revisions, apply patches
lb payload build configure            # the fast diagnostic
lb payload build core                 # x2t and the native libraries; the long one
lb payload build assemble             # sdkjs, web-apps, fonts, blanks, dictionaries, branding
lb payload test                # check the result converts a document
lb payload build dist                 # the distributable tarballs and their manifest
```

Each is a thin wrapper over the script of the same name in `build/`; run those directly when you want to pass something the target does not.

`uv sync` does the same itself. The two component packages, `components/core` and `components/web`, are workspace members whose build hooks build their wheels from the pinned sources, as pip does where PyPI has no wheel for the platform: libera-core's in `$BUILD_ROOT`, in the build container on Linux, libera-web's with that core's x2t, which makes the slide themes. `lb components build` makes the same two wheels on purpose, for PyPI: run it on each platform. It makes libera-core's sdist too, which carries the pins, the patch queues and the build scripts, and builds the core's wheel from that sdist, so each run tests what pip builds where there is no wheel. uv keeps the wheels and builds them again only when what they are built from changes: the pins, the patch queue, the scripts in `build/engine/`. A first `uv sync` builds the core, about an hour, with no output but uv's spinner; `lb payload build` first shows the build as it goes. With a built core it takes a few minutes, and the next one nothing.

Or skip packaging entirely while developing and point at the build tree:

```sh
export LIBERA_PAYLOAD="$BUILD_ROOT/out/payload"
```

## Linux

The steps above are the steps: the scripts run natively on Linux, with nothing in them macOS-only any more. Two differences:

- **`V8_BUILD_JOBS` scales with the machine.** Linking `v8_monolith` takes about 2 GB a job, so the default is memory over two, capped at the core count. macOS keeps its hardcoded 4, because the laptop builds while being used for other things. Override either.
- **Relocation checks; it does not rewrite.** `DT_NEEDED` records a soname and never a path, so a moved payload still finds its libraries through `LD_LIBRARY_PATH`, which both the build and the host set. A recorded `RPATH` pointing into the build tree is still reported (it is searched first, so a machine that happens to have that directory would silently load from it) and stripped when `patchelf` is installed.

Of the 28 `core` patches, 21 are macOS work and 7 are Windows. All but one sit inside an `if(APPLE)`, `if(WIN32)` or `if(NOT WIN32)` block, or in files only a Windows build reads, so they are inert here. The exception is `0019`, which adds zlib's sources to the `IWorkFile` target for every platform; ELF resolves those symbols lazily where Mach-O demands them at link, so Linux never needed the patch and is unharmed by it. **No native Linux build has been run yet**; the container path below is the exercised one.

### In a container

`ENGINE` picks the container engine. Without it, the first installed of `docker` then `podman` on macOS, and of `podman` then `docker` elsewhere:

```sh
ENGINE=podman lb container run payload
```

On Linux the choice has a consequence beyond taste. A bind mount passes uids through unchanged there, so a container running as root writes a build tree you cannot then delete without `sudo`. That is why `$BUILD_ROOT/linux-amd64` comes out owned by root on Fedora and by you on a Mac, where the daemon lives in a VM that maps ownership across the share. Rootless podman maps container root to your own uid through a user namespace, so the same build writes files you own.

Two things do not transfer. Rootless podman cannot run the `--privileged` container that registers binfmt handlers, so a cross-architecture build needs them from the distribution instead, as `qemu-user-static`. podman also refuses an unqualified image name, where docker reads one as `docker.io/library/…` without saying so. The scripts therefore qualify the images they build themselves as `localhost/…` under podman, and pass `--pull=never` everywhere, so a missing image fails outright; nothing goes looking in the registries.

**That base is what sets the floor for everybody who installs the result.**
Built on 22.04, the shipped `x2t` asks for glibc 2.34 and GLIBCXX 3.4.29, which
is Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9 and anything newer. Measured by
unpacking the published core in a clean container of each and running it. Moving
the base up moves that floor and strands users; amd64 was on noble once, needed
glibc 2.38, and would not load on Debian 12 at all. musl is not glibc, so Alpine
cannot run it whatever its version. The Flatpak sidesteps all of this, since the
editors inside it run against the GNOME runtime's libraries.

`lb container run payload` runs the same scripts in an Ubuntu 22.04 image. It is how a Linux payload gets built from the Mac. It is also the reproducible way to build one anywhere: the host's toolchain stops being part of the answer.

That is two commands, and either is useful alone:

```sh
lb container run payload               # fetch, configure, core, payload, dist, smoke, in the image
lb container export payload                  # the artifacts out of the volume, and where they are
```

`container export payload` copies the tarballs out of the container's volume and prints where it put them. `lb linux test` installs the component wheels of its architecture, which `lb components build` makes on a Linux machine of it; the Mac's own are macOS binaries.

Underneath, the same container takes one step at a time:

```sh
lb container image payload                  # build the image (about two minutes)
lb container versions payload               # what it is pinned to
lb container run payload dist.sh --fonts core   # one build/ script, in the container
lb container export payload                           # where the artifacts are; prints it
lb container shell payload                  # poke around inside
```

`export` writes the artifacts' location to stdout and everything else to stderr, so a script can capture it. The default build tree is already on this disk, so that is `$BUILD_ROOT/linux-<arch>/out/dist/<version>`. With `--volume` it copies them out first, into `$BUILD_ROOT/out/dist/<version>`, through a tar pipe, so extraction runs as you and nothing lands owned by root. The copy is extracted into a fresh directory and checked there, on both ends' exit statuses, since a pipeline's own is only tar's, and on content: an earlier export's files in the destination would otherwise pass for this one's. Either way it checks that the manifest and at least one tarball are there.

Three things are pinned, as `ARG`s at the top of `build/docker/Dockerfile`, because each drifts on its own schedule. Moving the toolchain means bumping one of them by hand; nothing else in the file decides what gets installed.

| | |
| :--- | :--- |
| `BASE_DIGEST` | `ubuntu:22.04` by digest, because a tag is a branch with better marketing |
| `APT_SNAPSHOT` | a date on `snapshot.ubuntu.com`, so every `.deb` is the one that was current then |
| `NODE_VERSION`, `NODE_SHA256_*` | the tarball from `nodejs.org`, by version and SHA-256 |
| `CLANG_VERSION` | 14 on x86_64, 13 on arm64 (V8 8.9 demands exactly 13 there): see below |

Node comes from a tarball, because NodeSource's `curl | bash` of `setup_20.x` adds a repository serving whatever 20.x is current that week: the same Dockerfile built twice would get two different Nodes. The setup script itself is unpinned code fetched at build time.

**`CLANG_VERSION=14`** is the one pin that is not simply "the newest thing that works". V8 8.9 does not compile under clang 16 or later: `-Wenum-constexpr-conversion` became an error, which `src/base/bit-field.h:43` trips in every torque-generated file: about a hundred of them, a hundred files into a thirty-minute build. Clang is used for V8 and for nothing else, since `core` is a gcc build, so this pins one dependency's compiler and leaves the image's alone. `update-alternatives` puts the unversioned names where `nc-build.py` and gn look for them.

Bumping it invalidates V8's object tree and **ninja will not notice**: it keys on the command line, where `/usr/bin/clang++` is the same string before and after. Delete `$BUILD_ROOT/out/core/third_party/work/v8/v8/v8/out.gn` by hand when you change it.

`apt-get update` exits 0 when every index fails to download: it falls back to whatever is already in `/var/lib/apt/lists` and mentions it in a `W:` line. An unreachable snapshot would therefore install today's packages and look exactly like success, so the image checks that apt is resolving against the snapshot before it installs anything.

The last layer checks the toolchain itself: every tool on `PATH`, `perl` with `FindBin` and `IPC::Cmd`, and a static C++ link. That last one is ICU's namespace probe, so a missing `libstdc++.a` fails here in a second, where a build takes twenty minutes to fail with a message about namespaces. The check earned its place on the first build, failing on `libtool`: Debian's package of that name ships only `libtoolize`; `/usr/bin/libtool` is in `libtool-bin`.

`lb container versions payload` prints the pins and the compiler versions out of the finished image; `/etc/libera-build-packages.txt` inside it is every package and version.

Two mounts:

- **The build tree goes on a real disk**, at `$BUILD_ROOT/linux-<arch>`, beside the native one. It used to be a named Docker volume, which lives on the VM's disk (the Mac's internal one). A full build was around 30 GB, before the fetch took only the pinned commits and the third-party work trees went once installed: the first attempt died with `No space left on device` while `$BUILD_ROOT` had 295 GB free. `--volume NAME` puts the old behaviour back. V8 needs a case-sensitive filesystem, which is why `$BUILD_ROOT` is an external volume on macOS in the first place. On macOS the core alone now peaks at 4.4 GB and leaves 2.4 GB (sources 0.9, the build 1.5), measured from an empty build root.
- **`MIRROR=DIR` is optional and read-only.** It is a local clone to fetch the pinned commits from instead of GitHub; an existing `$BUILD_ROOT/src` serves. Each tree gets its pinned commit alone, with no history: 180 MB of git for core rather than 870.

## Windows

The Windows machine is a builder like the Linux ones, reached over OpenSSH with Git Bash as its shell, and listed in `build/builders.toml` as `windows-x86_64`. From here:

```sh
lb on windows-x86_64 --update toolchain install --dry-run   # what it would install, changing nothing
lb on windows-x86_64 toolchain install            # windows-setup.ps1: Visual Studio's C++ tools, the SDK, Perl, NASM, Inno Setup
lb on windows-x86_64 toolchain check              # in a new session, which sees the new PATH
lb on windows-x86_64 payload build                  # fetch, configure, core, assemble, dist, smoke: hours, V8 about one
lb on windows-x86_64 app build windows                  # the application and its installer
```

**Smart App Control must be off.** It blocks unsigned programs and DLLs it does not know. A build makes and runs its own: V8's tools, the converter, and Strawberry Perl's modules, where it shows first as *"An Application Control policy has blocked this file"*. In evaluation mode it starts enforcing on its own, which is how a machine that built on Monday stops on Friday. `toolchain check` reads its state and says so; turning it off is by hand, in Windows Security ▸ App & browser control, and on some versions of Windows it cannot be turned back on without a reset.

Every item is checked on the file the build uses, whoever installed it, so a machine another tool set up (an Ansible playbook, Chocolatey) gets only what it lacks; the dry run lists that first. On the machine itself the same commands are `uv run lb …`. An administrator's ssh session has full administrator rights, which `windows-setup.ps1` needs; `toolchain install` runs it there, and `toolchain.sh` anywhere else.

The first line takes hours, V8 alone about one, with OpenSSL from vcpkg. `windows-app.sh` freezes the environment `uv run` syncs, whose components `uv sync` builds from the pins (an hour the first time, minutes after), and refuses a frozen tree that cannot find them. It writes the frozen application and `Libera-Suite-Setup-<version>.exe`, and copies the installer into `build/out/bundles/` with its SHA-256. Unlike the macOS `.app`, it embeds its own interpreter, because a Windows user has no Python.

`make ship` builds Windows with the rest. Its `components` phase runs `components build` there; `bundles` runs `app build windows` there, which freezes the components `uv sync` builds from the pins, and brings the installer and its `.sha256` here, into the run directory (`build/out/release/<commit>/bundles/`), where `stage` gathers them with the Flatpaks. The upload checks the hash first and each stored size after, and moves `bundles/latest-windows`, the version `install.ps1` installs, last, so the installer is on the origin before any user is sent to it.

A Windows build that comes after the release's Flatpaks is checked like the rest, then published again, PyPI skipping the files it already has:

```sh
lb release check bundles --only windows-x86_64   # the installer, made there and brought here
lb release check stage                           # installed and opened there, with the rest
lb release publish                               # the new files; latest-windows moves last
```

The Flatpaks have their own pointer, `bundles/latest`, so either can go first. `publish` refuses to move it while `latest-windows` names no installer on the origin, unless it brings one itself. Publishing is never done from the Windows machine: Git for Windows once turned `install.sh` to CRLF in a checkout there, and an upload from it broke `curl | sh` for everyone.

`.github/workflows/windows.yml` builds the same on a GitHub runner, by hand or on a version tag: the payload with `lb payload build`, then the installer with `lb app build windows`, both uploaded as the run's artifacts. On every push that touches `build/`, it checks that the patch queue still applies on Windows. See `notes/14-windows.md` in the development repository.

## Notes

**The pins are hashes, never branches.** A patch queue is only meaningful against a fixed base; "it built last week" has to stay reproducible. Bumping a pin is a decision, and may mean rebasing patches.

**Check what the command wrote.** `build/engine/smoke.sh` converts a document and then looks inside the result for an embedded font and text-drawing operators, because a PDF of the right size with no glyphs in it is the failure that looks like success.
