# `build/`

Everything that turns pinned upstream sources into a payload Libera Suite can run. It runs on a laptop; there is no CI.

**How to build one:** [docs/src/develop/build.md](../docs/src/develop/build.md).
**Why any of it is the way it is:** [notes/08-build.md](../notes/08-build.md).

## What is here

There is one directory per kind of thing:

| | |
| :--- | :--- |
| `pyproject.toml`, `src/`, `tests/` | **the front door**, the `lb` command (`src/libera_build/`): every build, check and release command, with `--help` at each level. `build/` is a uv workspace member; its tests are in the same three tiers as the application's |
| `upstream/` | what we build from: `pins.toml`, the upstream revisions by SHA, and `patches/<repo>/`, our changes as `git format-patch` output. `engine/build.sh fetch` reads its repo list from the pins, so the two cannot drift |
| `engine/` | the payload build, in shell, run here or in the build container: `build.sh` (fetch, patch, configure, build `core`: x2t and the native libraries), `payload.sh` (sdkjs, web-apps, fonts, blanks, dictionaries, branding), `dist.sh` (the tarballs and the manifest), `smoke.sh` (does it convert documents, judged by what it wrote), `check-patches.sh`, `toolchain.sh`, `doctrenderer-jsc.sh`, and `common.sh`, which the rest source |
| `payload/` | what ships beside upstream: `theme/` (our branding, copied into `web-apps/theme/` at payload time), `dictionaries.txt` and `fonts-core.txt` (what ships, out of repositories holding far more) |
| `docker/` | the image for `lb payload container`: the engine in a pinned Ubuntu 22.04 container, the reproducible Linux build, and the only way to build Linux from the Mac |
| `test-linux/` | the test image and its two smoke scripts, for `lb linux` |
| `flatpak/` | the Flatpak's manifest and image, for `lb app flatpak`: the Linux install channel |
| `macos/` | the `.app`: `macos-app.sh`, `macos-icon.py`, `launcher.m` |
| `windows/` | the installer and its toolchain: `windows-app.sh`, `windows-setup.ps1`, `msvc-env.sh`, `vcpkg.sh`, and what PyInstaller and Inno Setup read |
| `install/` | what runs on users' machines: `install.sh` (`curl … \| sh`) and `install.ps1` (`irm … \| iex`), published at the origin's root, and `released-gui.sh`, which opens a window from the *published* artifact on a machine it is installed on |
| `builders.toml.example` | the template for `builders.toml`, the machines `lb release ship` drives; that copy is gitignored, as is `out/` |

## Commands

    lb                        every command, and what is usually run
                              (uv run lb, outside the virtualenv; also lb help)
    lb help payload           the commands in one group (lb payload --help)
    lb help payload core      one command: its options, and examples

Each command says which script it runs before running it, so the scripts stay usable on their own for an argument `lb` does not pass. `lb on PLATFORM COMMAND…` runs any of them on a builder from `builders.toml`. The Makefile has only the standard jobs, plus `make payload` (`lb payload all`) and `make ship` (`lb release ship`). The builders, which have nothing installed, run it as `python3 -m libera_build` with `build/src` and `src` on `PYTHONPATH`.

Environment knobs, all with working defaults. The ones a command takes are also its options (`--build-root`, `--mirror`, `--v8-jobs`, `--core-jobs`, `--memory`, `--arch`, `--build-dir`, `--volume`, `--dist`), and its `--help` names the variable:

| | |
| :--- | :--- |
| `BUILD_ROOT` | where sources and output live. `$HOME/euro-office-build` on Linux; an external case-sensitive volume on macOS, because the internal disk is not one and V8 needs it |
| `MIRROR` | a local clone of the upstream repositories to fetch from (default `~/ghorg/euro-office`) |
| `CORE_FONTS` | font source for `payload.sh`, `dist.sh` and `smoke.sh` |
| `PAYLOAD` | payload output directory (default `$BUILD_ROOT/out/payload`) |
| `EO_VERSION` | Euro-Office editor version, default `9.2.1`. Our package version is separate |
| `COMPANY_NAME`, `THEME`, `PUBLISHER_URL`, `APP_COPYRIGHT`, `BLANK_LOCALE` | branding and blanks |
| `V8_BUILD_JOBS` | 4 on macOS; on Linux, memory over two, capped at the core count. Reaches the container too |
| `CORE_BUILD_JOBS` | the same, for core's own ninja. The memory figure comes from the cgroup limit when there is one: `/proc/meminfo` reports the *host's* memory inside a container, so without this a 64 GB builder starts thirty compilers in an 8 GB box |
| `DOCKER_MEMORY` | a ceiling for the build container, e.g. `8g`. Without one the VM takes what the build asks for and the *host* runs out. On a 16 GB Mac that arrives as the build being killed from outside with nothing in the log |
| `V8_KEEP_BUILD_DIR` | default 1: an interrupted V8 build resumes where it stopped |
| `INSTALL_MANIFEST` | `dist.sh` also copies the manifest into the wheel |
| `ARCH` | the containers: the architecture to build for; `payload container` defaults to `amd64`, the others to this machine's |
| `BUILD_DIR` | `payload container` only: where the container's build tree goes. Defaults to `$BUILD_ROOT/linux-<arch>`, a directory on a real disk |
| `VOLUME` | `payload container` only: a named Docker volume, on the VM's own disk |

`build.sh` points `BOTO_CONFIG` at an empty file: depot_tools shells out to gsutil, which picks up `~/.boto` and then fails on stale credentials even for public buckets. `--no_auth` no longer has any effect. The problem belongs to the local environment, so the script handles it and V8 stays unpatched.

## Two rules for editing anything in here

**Patches apply with no fuzz**, through `git am --keep-non-patch --keep-cr`. A patch that has stopped applying is news: find out why. `--keep-cr` is there because upstream keeps CRLF files: `git am` parses a patch as mail, and mailinfo strips the trailing CR from every line, after which no context matches and the series is rejected with nothing to suggest line endings were involved.

**Do not let whitespace tooling near `patches/`.** `git format-patch` output is a wire format: context lines keep whatever trailing whitespace the source had. The `-- ` signature line ends in a space. Stripping either makes `git am` reject the series. This repository's `trailing-whitespace` and `end-of-file-fixer` hooks did that on their first encounter with it, and broke the queue at patch 0002. The three whitespace hooks in `.pre-commit-config.yaml` skip `^build/upstream/patches/` for that reason.
