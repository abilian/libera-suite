# `build/`

Everything that turns pinned upstream sources into a payload Libera Suite can run. It runs on a laptop; there is no CI.

**How to build one:** [docs/src/develop/build.md](../docs/src/develop/build.md).
**Why any of it is the way it is:** [notes/08-build.md](../notes/08-build.md).

## What is here

| | |
| :--- | :--- |
| `pins.toml` | the upstream revisions, by SHA. `build.sh fetch` reads its repo list from here, so the two cannot drift |
| `patches/<repo>/` | our changes to upstream, as `git format-patch` output — 21 on `core`, 6 on `web-apps`, 1 on `sdkjs` |
| `build.sh` | fetch and patch the sources, configure, build `core` (x2t and the native libraries) |
| `payload.sh` | build the JS half: sdkjs, web-apps, fonts, blanks, dictionaries, branding |
| `dist.sh` | the distributable tarballs and the manifest the wheel verifies them against |
| `smoke.sh` | prove the result converts documents, by looking inside what it wrote |
| `docker.sh`, `docker/` | the same scripts in a pinned Ubuntu 22.04 container — the reproducible Linux build, and the only way to build Linux from the Mac |
| `macos-app.sh`, `macos-icon.py`, `macos/` | the `.app` bundle |
| `flatpak.sh`, `flatpak/` | the Flatpak, built in its own pinned container — the Linux install channel |
| `test-linux.sh`, `test-linux/` | the repository's own tests, on Linux — the only place they run there |
| `install.sh` | what `curl … | sh` runs on a user's machine; published at the origin root |
| `released-gui.sh` | open a window from the *published* artifact and prove it drew something |
| `remote.py`, `builders.toml` | the release, driven from here onto the build machines |
| `release.sh` | the whole release in order, or a refusal — `--dry-run` first |
| `common.sh` | sourced by the rest: paths, `built()`, `generate_fonts()`, `relocate()` |
| `theme/` | our branding: config, LESS and artwork, copied into `web-apps/theme/` at payload time |
| `dictionaries.txt`, `fonts-core.txt` | what ships, out of repositories that carry far more |
| `payload.version` | the payload version the manifest and the installer agree on |

## Commands

    build/build.sh fetch [repo...]   clone or reset to the pinned SHAs, apply patches
    build/build.sh configure         cmake configure only — the fast diagnostic
    build/build.sh build             full build (long; V8 alone is ~30 min)
    build/payload.sh                 the editor payload (~4 min)
    build/dist.sh [--fonts core|full]  tarballs and manifest
    build/dist.sh --manifest-only    just the manifest, over what is already there
    build/smoke.sh                   prove it converts documents
    build/check-patches.sh           does the queue still apply to the pins?
    build/macos-app.sh               the .app bundle
    build/docker.sh all              all of the above in a container, for Linux
    build/docker.sh export           its artifacts onto this machine
    build/flatpak.sh build           the Flatpak, in a container of its own
    build/flatpak.sh check           install the bundle and run --diagnose in it
    build/test-linux.sh lint         ruff, ty, pyrefly and mypy, on Linux
    build/test-linux.sh test         the repository's tests, on Linux
    build/test-linux.sh gui          a real GTK window under Xvfb, screenshotted

    build/released-gui.sh --all      the same window, from what users download,
                                     on every Linux builder in builders.toml
    build/release.sh --dry-run       what a release would do, and what would stop it
    build/release.sh                 all of it, or nothing — `make release`

`make release` builds natively only where it has to: macOS, which has no
container. On Linux every core comes out of `docker.sh`, including the host's
own architecture — that is what the container is for, and requiring a native
C++ toolchain there would ask for the thing it was written to avoid.

The repository Makefile wraps the first four as `make payload-fetch`,
`payload-configure`, `payload-core` and `payload-assemble`, with `payload-all`
for the chain and `payload-dist`, `smoke` and `patches` for the rest. Use the
scripts directly when you want to pass an argument the target does not.

The container has its own three: `make payload-container` runs the whole chain
in the image, `make payload-export` copies the artifacts out of its volume, and
`make payload-install` does both and installs the result for this machine.
`make payload-linux` is the first and last together — everything between a
clean checkout and `make test` on Linux.

A third container runs the tests: `make test-linux` is the suite on Linux and
`make gui-linux` opens the window pywebview actually builds there — GTK 3 and
WebKitGTK under Xvfb, screenshotted, because a window that maps and never
paints looks like success from everywhere else. Both need a Linux payload.

The Flatpak has its own container and its own two: `make flatpak` builds the
bundle and `make flatpak-check` installs it and runs `libera --diagnose`
inside the sandbox. That is as far as a container goes — there is no display in
one — so it proves the runtime supplies GTK and WebKit and that the application
imports, and leaves driving the GUI to a Linux box.

Environment knobs, all with working defaults:

| | |
| :--- | :--- |
| `BUILD_ROOT` | where sources and output live. `$HOME/euro-office-build` on Linux; an external case-sensitive volume on macOS, because the internal disk is not one and V8 needs it |
| `MIRROR` | a local clone to fetch from instead of GitHub (default `~/ghorg/euro-office`) |
| `CORE_FONTS` | font source for `payload.sh`, `dist.sh` and `smoke.sh` |
| `PAYLOAD` | payload output directory (default `$BUILD_ROOT/out/payload`) |
| `EO_VERSION` | Euro-Office editor version, default `9.2.1` — **not** our package version |
| `COMPANY_NAME`, `THEME`, `PUBLISHER_URL`, `APP_COPYRIGHT`, `BLANK_LOCALE` | branding and blanks |
| `V8_BUILD_JOBS` | 4 on macOS; on Linux, memory over two, capped at the core count. Reaches the container too |
| `CORE_BUILD_JOBS` | the same, for core's own ninja. The memory figure comes from the cgroup limit when there is one — `/proc/meminfo` reports the *host's* memory inside a container, so without this a 64 GB builder starts thirty compilers in an 8 GB box |
| `DOCKER_MEMORY` | a ceiling for the build container, e.g. `8g`. Without one the VM takes what the build asks for and the *host* runs out — on a 16 GB Mac that arrives as the build being killed from outside with nothing in the log |
| `V8_KEEP_BUILD_DIR` | default 1 — an interrupted V8 build resumes instead of restarting |
| `INSTALL_MANIFEST` | `dist.sh` also copies the manifest into the wheel |
| `ARCH` | `docker.sh` only: the architecture to build for, default `amd64` |
| `BUILD_DIR` | `docker.sh` only: where the container's build tree goes. Defaults to `$BUILD_ROOT/linux-<arch>` — a real disk, not a Docker volume |
| `VOLUME` | `docker.sh` only: a named Docker volume instead, on the VM's own disk |
| `ARCHES` | `release.sh` only: which Linux architectures to attempt, default `amd64 arm64` |

`build.sh` points `BOTO_CONFIG` at an empty file: depot_tools shells out to gsutil, which picks up `~/.boto` and then fails on stale credentials even for public buckets, and `--no_auth` no longer has any effect. A local environment problem, deliberately handled in the script rather than patched into V8.

## Two rules for editing anything in here

**Patches apply with no fuzz.** `git am --keep-non-patch --keep-cr`, and a patch that has stopped applying is news rather than something to guess at. `--keep-cr` because upstream keeps CRLF files: `git am` parses a patch as mail, and mailinfo strips the trailing CR from every line, after which no context matches and the series is rejected with nothing to suggest line endings were involved.

**Do not let whitespace tooling near `patches/`.** `git format-patch` output is a wire format: context lines keep whatever trailing whitespace the source had, and the `-- ` signature line ends in a space. Stripping either makes `git am` reject the series — which is what this repository's `trailing-whitespace` and `end-of-file-fixer` hooks did on their first encounter with it, breaking the queue at patch 0002. `.pre-commit-config.yaml` excludes `^build/patches/` from all three whitespace hooks for that reason.
