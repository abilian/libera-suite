# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two versions move here and they move independently. The **application** is this package, `libera`. The **editor payload** is the Euro-Office build it fetches on first use, versioned separately so that a fix to the host does not force a 120 MB re-download. `libera --version` prints both.

## [0.2.1] - 2026-09-25

The same editors: payload **0.2** is unchanged, so an existing install is not
re-downloaded. Everything here is the host.

### Fixed

- **Help said nothing at all when no browser could be opened.** It asked the
  desktop to open the documentation and threw away the answer, so on a machine
  with none, the menu item did nothing visible. It now puts the URL on screen.
  The same went for external links from inside the editor, which reported
  success in the log whatever the desktop did with them.
- **The installer refused to run twice.** `curl … | sh` over an existing
  install ended in `FATAL: flatpak install failed`, because a Flatpak bundle
  cannot be installed over itself without `--reinstall`. Re-running it now
  replaces the installed copy, which is also how it upgrades.

### Changed

- The package builds with **hatchling**, where it used `uv_build`. `uv_build` ships
  as a platform-specific Rust binary, so anything applying `--no-binary :all:`
  to build dependencies (Homebrew, a distribution packager, an air-gapped
  install) tried to compile it and needed a Rust toolchain for a package that
  is pure Python. `uv build` and `uv sync` are unaffected.

## [0.2.0] - 2026-09-24

This release carries payload **0.2** and is the first that installs on Ubuntu 22.04 and Debian 12.

### Added

- `libera --version`, and `-V`. It names the application and the payload it expects, because a bug report giving only one of them does not say which of the two was in play.
- **Flatpak bundles**, one per architecture: `flatpak install ./libera-0.2.0-amd64.flatpak`. Installing one takes that file and nothing else. The bundle carries the editors, so nothing is downloaded afterwards, though it does resolve `org.gnome.Platform` from Flathub, so a machine with no flathub remote needs one added first. This is the Linux install to prefer: it brings its own GTK and WebKit, which `pip` cannot.
- **An installer script**, for a machine where you have no root. It writes to `~/.local/bin` and `~/.local/share` and nowhere else, and on Linux it installs the Flatpak bundle when `flatpak` is present.

  ```sh
  curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
  ```

- **A Homebrew formula**: `brew install abilian/tap/libera`.

### Changed

- **Linux now needs Ubuntu 22.04, Debian 12, or newer**, where payload 0.1 needed Ubuntu 24.04. Both Linux cores are built on Ubuntu 22.04, so the converter asks for glibc 2.34 and GLIBCXX 3.4.26, where payload 0.1 wanted 2.38 and 3.4.32. Measured by unpacking the published core in a clean container of each release, then running `x2t`.
- The payload is version 0.2, so `libera --payload-install` fetches a new one over any existing install.

### Fixed

- **Installing a payload no longer risks destroying the one already there.** The download was staged in `/tmp` and moved into place. A rename cannot cross a filesystem, so where `/tmp` is its own mount, which is most Linux boxes, the move degraded to a copy. The install stopped being atomic, needed the payload's size twice, and running out of room part-way left a half-populated directory where a working payload had been. Staging now happens beside the destination, so the move is a rename. A failure puts the previous payload back.
- `libera --payload-install` refuses before downloading anything when the disk cannot hold the result. It used to fail a hundred megabytes in, with six tracebacks about individual files.

### Documentation

- [The install page](https://docs.liberasuite.eu/guide/install/) states the Linux floor and how it was measured.
- `libera` 0.1.0 is still on PyPI and still cannot work. Ask for `libera>=0.1.1` until it is yanked.

## [0.1.1] - 2026-09-18

The first release that works, and in practice macOS (Apple Silicon) only: the same wheel installs on Linux and cannot open a window until the distribution's GTK and PyGObject packages are present.

### Fixed

- The payload manifest is found where it is, so `libera --payload-install` no longer answers every request with *"this build ships no manifest, so downloads cannot be verified."*
- The manifest describes the payload the origin is actually serving. Every hash in 0.1.0's copy named bytes that had been rebuilt after it was published, so even with the lookup repaired, every download would have failed verification.

### Changed

- Package metadata a public release should have had: an Apache-2.0 licence expression covering `src/libera/`, classifiers, and project URLs. The editor payload is AGPL-3.0 and its corresponding source is recorded in every payload manifest; see [the licence page](https://docs.liberasuite.eu/licence/) and `libera --payload-status`.
- The macOS bundle declares the deployment target its converter really has, read off `x2t` at build time. It had promised macOS 11 against a binary needing 14, which on Big Sur through Ventura is an application that launches and a converter that cannot load.

## [0.1.0] - 2026-09-16

Published, and broken in three independent ways: the manifest lookup above, a manifest describing artifacts that no longer existed, and a publication that preceded the payload origin itself. **0.1.1 replaces it.** Installing 0.1.0 gets you a wheel that cannot fetch its own payload.
