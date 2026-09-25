# Build the payload

The payload is built from pinned upstream sources plus our patches, on your own machine or on a build host you can reach. The only CI is a Windows probe that answers cheap questions on a hosted runner; nothing is gated on it.

## What you need

```sh
make toolchain-install     # what it will install: build/toolchain.sh list
make toolchain-check       # what is missing, and the line that installs it
```

Debian, Fedora and Arch have measured package names. openSUSE is a best-effort mapping. On anything else `toolchain-check` names the tools and leaves the package manager to you. On **macOS** it comes to the Xcode command line tools plus CMake, Ninja and Node 20.

Every payload target depends on `toolchain-check`. Each thing it looks for otherwise fails late and in somebody else's words: a missing `glib2-devel` stops V8's `gn gen` *after* depot_tools has fetched V8, which took 991 seconds on Fedora 43, and a missing `libstdc++-static` arrives as a message about namespaces. `build/toolchain.sh` holds the one list, which the container image checks against too.

**A native build needs an old clang, which most distributions no longer have.** V8 8.9 does not compile under clang 16 or later, so `toolchain-check` refuses anything newer. Fedora 43 defaults to clang 21. It packages `clang15`, which is the newest V8 accepts, but no matching `lld15`, so there is no complete toolchain there to point the build at. Use the container, which pins clang 14 and is the release path anyway.

`clang` and `lld` are **not optional**, even though everything else builds with gcc. V8's `nc-build.py` aborts with `Tool not found: clang` before compiling anything. Its gn args set `is_clang=true` and `use_lld=true`, then run ninja with `CC=clang CXX=clang++`. Neither `build-essential` nor the Fedora development group provides them.

`llvm` comes with them, for one binary: `is_clang=true` makes `gcc_toolchain.gni` set `ar` to `llvm-ar`, which Ubuntu ships in the `llvm` package. Without it V8 compiles a hundred files and then fails at the first `AR` step with `/usr/bin/llvm-ar: not found`: a path, with no package name anywhere in it.

Fedora needs `perl-core`, because OpenSSL's `Configure` needs `FindBin` and `IPC::Cmd`, which the minimal `perl` package leaves out.

`libglib2.0-dev` / `glib2-devel` is V8's, and the one to be suspicious about. V8's Linux gn args set `use_sysroot=false`, so it compiles against whatever glib the host has, with no downloaded sysroot in the way. `gn gen` then fails before anything compiles if the four `.pc` files are missing. On the laptop this was written on, `pkg-config --modversion glib-2.0` answered from **Homebrew**: a native build would have linked V8 against linuxbrew headers, with nothing on screen to say so, which is the argument for the container.

`python-is-python3` on Debian, `python-unversioned-command` on Fedora: boost's `nc-build.py` runs bare `python` to drive boostdep's `depinst.py`; Ubuntu has shipped no `/usr/bin/python` since 20.04. The failure is a `FileNotFoundError: 'python'` out of the middle of a traceback that never names boost.

`libstdc++-static` is split out on Fedora as well. Its absence looks like this: ICU's Linux configure line is `CXXFLAGS=-static-libstdc++ -static-libgcc` (`Common/3dParty/icu/nc-build.py`), Fedora ships `libstdc++.a` in a package of its own, and Debian's `g++` includes it. Without it the first C++ link in `configure` fails with `cannot find -lstdc++`. That link happens to be the namespace probe, so configure reports `Namespace support is required to build ICU`, which says nothing about static linking. The real error is in `config.log`, in the work tree.

On **Linux arm64 only**, V8 8.9 demands clang **13 exactly** and aborts on anything else (`nc-build.py`, around the `targetarch == "arm64"` check). x86_64 has no version gate. Ubuntu 24.04 has no clang 13 at all; its packages start at 14. That is one of the two reasons the container base is 22.04, where `build/docker.sh` picks clang 13 for arm64 and 14 for x86_64 off one image.

Either way you also need time and disk. **V8 is built from source**, on every platform, and takes about half an hour in a build tree of several gigabytes. `Common/3dParty/v8/hashes.txt` lists cache keys for a Nextcloud store that wants credentials we do not have, so upstream's `ensure_dep` finds nothing and falls through to building it.

`git` needs a configured `user.email` and `user.name`, because applying the patch queue is the first thing the build does and `git am` makes commits.

Set `BUILD_ROOT` to somewhere with room. It defaults to `$HOME/euro-office-build` on Linux, and on macOS to an external case-sensitive volume, because the internal disk is case-insensitive and V8's checkout does not come through that intact. `build.sh` checks for it and refuses at the start.

```sh
export BUILD_ROOT=/somewhere/with/room
```

## Does the Mac need V8?

Maybe not. Two targets exist to find out:

```sh
make doctrenderer-jsc          # build doctrenderer against macOS's JavaScriptCore
make doctrenderer-jsc-check    # convert a document with each engine, and compare the PDF
```

Upstream abstracts the JS engine behind `js_internal/js_base.h` and carries two implementations, `v8` and `jsc`. The second is Objective-C++ against Apple's JavaScriptCore framework, and upstream's own qmake build turns it on for macOS. The CMake port we use defaults it off, so we build V8 on the Mac too: half an hour, and five of the `core` patches.

Measured so far: it compiles with no patches, links the system framework, and renders the smoke document to a PDF with the same page, font and text-operator counts as V8. That is one four-line document, so it says the integration holds. Whether every document renders identically is a separate question.

None of this reaches Linux, where `jsc_base.mm` does not apply: it is Objective-C++ and links a framework. WebKitGTK ships a JavaScriptCore with a C API, which would be a third implementation of `js_base.h`, written from scratch against that API.

## The steps

```sh
make payload-all       # the whole chain, ending in the smoke check
```

Take them one at a time the first time on a new machine: `payload-configure` surfaces missing tools and CMake gaps in minutes, before a forty-minute build reaches them:

```sh
make payload-fetch       # clone or reset to the pinned revisions, apply patches
make payload-configure   # the fast diagnostic
make payload-core        # x2t and the native libraries; the long one
make payload-assemble    # sdkjs, web-apps, fonts, blanks, dictionaries, branding
make smoke               # check the result converts a document
make payload-dist        # the distributable tarballs and their manifest
```

Each is a thin wrapper over the script of the same name in `build/`; run those directly when you want to pass something the target does not.

Then install what you built:

```sh
libera --payload-install --from "$BUILD_ROOT/out/dist/0.2"
```

Or skip packaging entirely while developing and point at the build tree:

```sh
export LIBERA_PAYLOAD="$BUILD_ROOT/out/payload"
```

## Linux

The steps above are the steps: the scripts run natively on Linux, with nothing in them macOS-only any more. Two differences:

- **`V8_BUILD_JOBS` scales with the machine.** Linking `v8_monolith` takes about 2 GB a job, so the default is memory over two, capped at the core count. macOS keeps its hardcoded 4, because the laptop builds while being used for other things. Override either.
- **Relocation checks; it does not rewrite.** `DT_NEEDED` records a soname and never a path, so a moved payload still finds its libraries through `LD_LIBRARY_PATH`, which both the build and the host set. A recorded `RPATH` pointing into the build tree is still reported (it is searched first, so a machine that happens to have that directory would silently load from it) and stripped when `patchelf` is installed.

Of the 27 `core` patches, 21 are macOS work and 6 are Windows. All but one sit inside an `if(APPLE)`, `if(WIN32)` or `if(NOT WIN32)` block, so they are inert here. The exception is `0019`, which adds zlib's sources to the `IWorkFile` target for every platform; ELF resolves those symbols lazily where Mach-O demands them at link, so Linux never needed the patch and is unharmed by it. **No native Linux build has been run yet**; the container path below is the exercised one.

### In a container

`ENGINE` picks the container engine, `docker` by default and `podman` if that is the only one installed:

```sh
ENGINE=podman make payload-container
```

On Linux the choice has a consequence beyond taste. A bind mount passes uids through unchanged there, so a container running as root writes a build tree you cannot then delete without `sudo`. That is why `$BUILD_ROOT/linux-amd64` comes out owned by root on Fedora and by you on a Mac, where the daemon lives in a VM that maps ownership across the share. Rootless podman maps container root to your own uid through a user namespace, so the same build writes files you own.

Two things do not carry over. Rootless podman cannot run the `--privileged` container that registers binfmt handlers, so a cross-architecture build needs them from the distribution instead, as `qemu-user-static`. podman also refuses an unqualified image name, where docker reads one as `docker.io/library/…` without saying so. The scripts therefore qualify the images they build themselves as `localhost/…` under podman, and pass `--pull=never` everywhere, so a missing image fails outright; nothing goes looking in the registries.

`build/docker.sh` runs the same scripts in an Ubuntu 22.04 image. It is how a Linux payload gets built from the Mac. It is also the reproducible way to build one anywhere: the host's toolchain stops being part of the answer.

```sh
make payload-linux          # the whole thing: build in the container, install here
```

That is two targets, and either is useful alone:

```sh
make payload-container      # fetch, configure, core, payload, dist, smoke, in the image
make payload-install        # the artifacts out of the volume and installed on this machine
```

`payload-install` copies the tarballs out of the container's volume and installs them the way a user does, with every hash checked against `manifest.json`, so `make test` resolves the payload with nothing set in the environment. After a *native* `make payload-dist`, point the same target at that build instead: `make payload-install DIST=$BUILD_ROOT/out/dist/0.2`.

Underneath, `build/docker.sh` takes the same steps one at a time:

```sh
build/docker.sh image       # build the image (about two minutes)
build/docker.sh versions    # what it is pinned to
build/docker.sh all         # fetch, configure, build, payload, dist, smoke
build/docker.sh export      # the artifacts onto this machine; prints where
build/docker.sh shell       # poke around inside
```

`export` writes to `$BUILD_ROOT/out/dist` and prints that directory on stdout, with everything else on stderr, which is how `payload-install` reads it. It copies through a tar pipe, so extraction runs as you and nothing lands owned by root. It also checks that the manifest and at least one tarball arrived, because the exit code of a pipeline comes from tar.

Three things are pinned, as `ARG`s at the top of `build/docker/Dockerfile`, because each drifts on its own schedule. Moving the toolchain means bumping one of them by hand; nothing else in the file decides what gets installed.

| | |
| :--- | :--- |
| `BASE_DIGEST` | `ubuntu:22.04` by digest, because a tag is a branch with better marketing |
| `APT_SNAPSHOT` | a date on `snapshot.ubuntu.com`, so every `.deb` is the one that was current then |
| `NODE_VERSION`, `NODE_SHA256_*` | the tarball from `nodejs.org`, by version and SHA-256 |
| `CLANG_VERSION` | 14 on x86_64, 13 on arm64 (V8 8.9 demands exactly 13 there): see below |

Node comes from a tarball, because NodeSource's `curl | bash` of `setup_20.x` adds a repository carrying whatever 20.x is current that week: the same Dockerfile built twice would get two different Nodes. The setup script itself is unpinned code fetched at build time.

**`CLANG_VERSION=14`** is the one pin that is not simply "the newest thing that works". V8 8.9 does not compile under clang 16 or later: `-Wenum-constexpr-conversion` became an error, which `src/base/bit-field.h:43` trips in every torque-generated file: about a hundred of them, a hundred files into a thirty-minute build. Clang is used for V8 and for nothing else, since `core` is a gcc build, so this pins one dependency's compiler and leaves the image's alone. `update-alternatives` puts the unversioned names where `nc-build.py` and gn look for them.

Bumping it invalidates V8's object tree and **ninja will not notice**: it keys on the command line, where `/usr/bin/clang++` is the same string before and after. Delete `$BUILD_ROOT/out/core/third_party/work/v8/v8/v8/out.gn` by hand when you change it.

`apt-get update` exits 0 when every index fails to download: it falls back to whatever is already in `/var/lib/apt/lists` and mentions it in a `W:` line. An unreachable snapshot would therefore install today's packages and look exactly like success, so the image checks that apt is resolving against the snapshot before it installs anything.

The last layer checks the toolchain itself: every tool on `PATH`, `perl` with `FindBin` and `IPC::Cmd`, and a static C++ link. That last one is ICU's namespace probe, so a missing `libstdc++.a` fails here in a second, where a build takes twenty minutes to fail with a message about namespaces. The check earned its place on the first build, failing on `libtool`: Debian's package of that name ships only `libtoolize`; `/usr/bin/libtool` is in `libtool-bin`.

`build/docker.sh versions` prints the pins and the compiler versions out of the finished image; `/etc/libera-build-packages.txt` inside it is every package and version.

Two mounts:

- **The build tree goes on a real disk**, at `$BUILD_ROOT/linux-<arch>`, beside the native one. It used to be a named Docker volume, which lives on the VM's disk (the Mac's internal one). A full build is around 30 GB: the first attempt died with `No space left on device` while `$BUILD_ROOT` had 295 GB free. `VOLUME=name` puts the old behaviour back. V8 needs a case-sensitive filesystem, which is why `$BUILD_ROOT` is an external volume on macOS in the first place.
- **`MIRROR=DIR` is optional and read-only.** It is a local clone to copy git objects from, which saves pulling 1.5 GB from GitHub; an existing `$BUILD_ROOT/src` serves. Without it the fetch clones from upstream and says so.

## Windows

Partly. There is no Windows machine here, so the work happens on a hosted runner: `.github/workflows/windows-probe.yml` checks the toolchain and the patch queue on every push, and builds `core` on request. That much works -- V8 compiles in about an hour, OpenSSL comes from vcpkg -- and `x2t` has never been run there. See `notes/14-windows.md` in the development repository.

## Notes

**The pins are hashes, never branches.** A patch queue is only meaningful against a fixed base; "it built last week" has to stay reproducible. Bumping a pin is a decision, and may mean rebasing patches.

**Check what the command wrote.** `build/smoke.sh` converts a document and then looks inside the result for an embedded font and text-drawing operators, because a PDF of the right size with no glyphs in it is the failure that looks like success.
