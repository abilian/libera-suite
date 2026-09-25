# There is no CI. `make verify` is what "everything passed" means here.
#
# The workflow in .github/ is unrun template scaffolding, and could not run the
# real checks anyway: the payload and a browser are local things.

.PHONY: help all verify clean tidy build publish \
	lint lint-py lint-js format \
	test test-unit test-integration test-e2e test-cov test-browser \
	smoke patches payload-status toolchain-check toolchain-install \
    doctrenderer-jsc doctrenderer-jsc-check \
	payload-fetch payload-configure payload-core payload-assemble \
	payload-dist payload-all release release-check \
	payload-container payload-export payload-install payload-linux \
	ship ship-plan \
	release-status origin-collect origin-push origin-check origin-extras \
	flatpak flatpak-wheels flatpak-check flatpak-smoke flatpak-shell \
	released-gui \
	test-linux gui-linux lint-linux dialog-linux \
	docs-serve docs-check

# `make` on its own prints this. The default goal used to be `all`, which is
# lint and the test suite -- useful, but not what an unfamiliar reader wants
# from an unqualified `make`.
#
# Read out of this file rather than written beside it: a hand-kept list is a
# second copy of the target names, and a second copy drifts. A target shows up
# here when it carries a `## summary`, so the ones nobody types -- lint-py,
# flatpak-wheels -- stay out of the way by saying nothing.
.DEFAULT_GOAL := all

##@ Everyday
help: ## list these targets
	@awk 'BEGIN { FS = ":.*## " } \
		/^##@ / { printf "\n%s\n", substr($$0, 5); next } \
		/^[a-z][a-z0-9-]*:.*## / { printf "  %-24s %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@echo

all: lint test ## lint, then the whole test suite

# Everything, in the order that fails fastest. Needs an installed payload, a
# browser, and a built core for the last two.
verify: lint test docs-check patches smoke ## everything: lint, tests, docs links, patch queue, converter

##@ Static checks
# --- static ------------------------------------------------------------------

lint: lint-py lint-js ## ruff, ty, pyrefly, mypy on src, plus biome on the bridge JS

lint-py:
	uv run --active ruff check
	uv run --active ruff format --check
	uv run --active ty check src
	uv run --active pyrefly check src
	uv run --active mypy src
	# uv run --active mypy --strict src

# The bridge is JavaScript and ruff has nothing to say about it.
#
# biome.json's `includes` carries three exclusions that are pruning, not
# scoping: `includes` says what to *check*, and biome walks everything else
# looking for it. flatpak-builder leaves build/flatpak/builddir/var/run behind
# as a symlink to /run, so on Linux that walk descends into the host's sockets
# and reports 18 700 diagnostics from them. On macOS it only looked like two
# harmless warnings, because /run does not exist there.
lint-js:
	npx --yes @biomejs/biome@2.5.13 check

format: ## reformat the Python and the JavaScript
	uv run --active ruff format src tests
	uv run --active ruff check src tests --fix
	uv run --active ruff format src tests
	npx --yes @biomejs/biome@2.5.13 check --write

##@ Tests
# --- tests -------------------------------------------------------------------
#
# Markers come from the directory (see tests/conftest.py). The upper two levels
# skip rather than fail when there is no payload or no browser.

test: ## the whole suite (~40s)
	uv run pytest

test-unit: ## fast and isolated; needs no payload and no browser
	uv run pytest -m unit

test-integration: ## the host over HTTP; needs an installed payload
	uv run pytest -m integration

test-e2e: ## the editor in headless Chromium; needs a payload and a browser
	uv run pytest -m e2e

test-cov: ## the suite with a coverage report
	uv run pytest --cov=libera --cov-report=html --cov-report=term tests

# The browser the e2e tests drive, once: about 115 MB. They find it without
# help afterwards -- see tests/c_e2e/conftest.py -- and skip with this command
# in the message when it is missing. A system Chromium or Chrome does as well,
# and CHROMIUM=/path/to/browser overrides both.
test-browser:
	uv run playwright install chromium

##@ Building the payload
# --- building the payload ----------------------------------------------------
#
# The long half of this project. Runs on the machine, writes to $BUILD_ROOT --
# $HOME/euro-office-build on Linux, an external case-sensitive volume on macOS.
# Prerequisites are in docs/src/develop/build.md; clang and lld are required on
# Linux even though everything else builds with gcc.
#
# Run these in order the first time. `payload-all` does exactly that.

# Is this machine equipped? A second, against the hour every one of these
# otherwise costs: a missing glib2-devel stops V8's `gn gen` *after* a
# quarter-hour fetch, and a missing libstdc++-static arrives as a message
# about namespaces. Every payload target depends on it, and a phony
# prerequisite runs once per `make` however many targets want it.
toolchain-check: ## is this machine equipped to build the payload?
	@sh build/toolchain.sh check

# The same list, installed. Debian, Fedora and Arch have measured package
# names; `list` prints them without installing anything.
toolchain-install: ## install what toolchain-check asks for
	@sh build/toolchain.sh install

# Clone or reset to the pinned SHAs and apply the patch queue. ~2 GB from
# GitHub unless MIRROR points at local clones.
payload-fetch: toolchain-check # clone the pinned sources and apply the patch queue
	sh build/build.sh fetch

# The fast diagnostic: surfaces missing tools and CMake gaps in minutes,
# rather than forty of them into a build.
payload-configure: toolchain-check # the fast diagnostic: missing tools and CMake gaps
	sh build/build.sh configure

# x2t and the native libraries. The long one -- V8 alone is ~30 min.
payload-core: toolchain-check # x2t and the native libraries (long: V8 alone is ~30 min)
	sh build/build.sh build

# sdkjs, web-apps, fonts, blank documents, dictionaries, branding.
payload-assemble: toolchain-check # sdkjs, web-apps, fonts, blanks, dictionaries, branding
	sh build/payload.sh

BUILD_ROOT_NOTE = left alone: $${BUILD_ROOT:-the payload and core build}

FONTS ?= core

payload-dist: toolchain-check # the tarballs and the manifest a release is made of
	sh build/dist.sh --fonts $(FONTS)

# The whole chain, ending with the check that it converts a document.
payload-all: payload-fetch payload-configure payload-core payload-assemble smoke ## fetch, configure, core, assemble, then smoke

##@ Exploration
# --- does the Mac need V8 at all? --------------------------------------------
#
# Exploratory. upstream carries a JavaScriptCore backend for doctrenderer and
# turns it on for macOS under qmake; the CMake port we use defaults it off, so
# we build V8 on the Mac too -- half an hour, and five of the 21 core patches.
# `doctrenderer-jsc-check` converts a document with each engine and compares the PDF.

doctrenderer-jsc: ## build doctrenderer against macOS's JavaScriptCore
	sh build/doctrenderer-jsc.sh build

doctrenderer-jsc-check: doctrenderer-jsc ## convert with each engine and compare the PDF
	sh build/doctrenderer-jsc.sh check

##@ The payload, in the container
# --- the same thing in the container -----------------------------------------
#
# The reproducible path, and the only one for Linux: a pinned Ubuntu image, so
# the host's toolchain stops being an input. Five host dependencies and a
# Homebrew glib were found this way -- see notes/08-build.md.

# fetch, configure, core, payload, dist and smoke, all inside the image.
payload-container: ## build the Linux payload in the pinned container
	sh build/docker.sh all

# The built artifacts out of the container's volume and onto this machine.
# Prints the directory it wrote, which is what payload-install reads.
payload-export: # copy the container's artifacts onto this machine
	sh build/docker.sh export

# Install the payload this machine runs, the way a user installs it: every
# hash checked against the manifest. `make test` resolves it from there, so
# nothing needs LIBERA_PAYLOAD.
#
# Defaults to the container's artifacts. After a *native* payload-dist, point
# it at that build instead: make payload-install DIST=$$BUILD_ROOT/out/dist/0.1
DIST ?=
payload-install: ## install built artifacts the way a user would
	uv run libera --payload-install --from "$${DIST:-$$(sh build/docker.sh export)}"

# Everything between a clean checkout and `make test`, on Linux.
payload-linux: payload-container payload-install ## payload-container, then payload-install

##@ Linux
# --- the suite, on Linux ------------------------------------------------------
#
# Everything else about this project is verified on a Mac. These two are the
# only place the host, the bridge and the editor are exercised on Linux at all,
# and the first run of them found four tests that passed only because the
# machine was a Mac -- plus the pipx trap now described in src/libera/gui.py.
#
# They cover different halves. `test-linux` is the suite: `libera --serve`
# driven by headless Chromium, which is the editor and the bridge but not the
# window. `gui-linux` opens the window pywebview actually builds on Linux --
# GTK 3 and WebKitGTK, under Xvfb -- and screenshots it, because a window that
# maps and never paints looks like success from everywhere else.
#
# Both need a Linux payload: build one with `make payload-container` (add
# BUILD_DIR=/path on a disk with 30 GB free) and export it, or pass DIST=.

# The whole suite on Linux. Arguments reach pytest: make test-linux ARGS="-k bridge"
ARGS ?=
test-linux: ## the suite, on Linux, in the container
	sh build/test-linux.sh test $(ARGS)

# The type checkers, on Linux. `sys.platform` is a fact at check time, so a
# checker on a Mac prunes every non-macOS branch before looking at it -- two
# real defects have hidden there.
lint-linux: ## the type checkers on Linux, where the branches are live
	sh build/test-linux.sh lint

# A real GTK window, opened, screenshotted and checked for having been painted.
gui-linux: ## a real GTK window under Xvfb, screenshotted
	sh build/test-linux.sh gui

# The GTK question behind the close prompt, the recovery offer and the reload
# offer, driven from both the threads that ask it.
dialog-linux: ## the GTK question the host asks, answered
	sh build/test-linux.sh dialog

##@ The Flatpak
# --- the Flatpak ---------------------------------------------------------------
#
# Also in a container, and also from the Mac: flatpak-builder needs user
# namespaces and /dev/fuse, and Docker grants both. What the container has no
# answer for is a display, so `flatpak-check` goes as far as installing the
# bundle and asking `libera --diagnose` whether a window could be opened --
# the GNOME runtime is what supplies GTK and WebKit, and that is the half that
# would break silently. Actually driving the GUI still wants a Linux box.
#
#   ARCH=amd64 make flatpak   x86_64 instead of this machine's architecture

# Wheels, flatpak-builder, the bundle, then the check.
flatpak: ## wheels, then the bundle, then the check
	sh build/flatpak.sh build

# The offline wheel set on its own. `flatpak` does this when it is missing.
flatpak-wheels:
	sh build/flatpak.sh wheels

# Install the built bundle and run it, without rebuilding.
flatpak-check: ## install the built bundle and run --diagnose in it
	sh build/flatpak.sh check

# And have it convert a document: x2t is compiled against Ubuntu 22.04 and runs
# here under the GNOME runtime's newer glibc, which nothing else checks.
flatpak-smoke: ## and have it convert a document
	sh build/flatpak.sh smoke

flatpak-shell: # a shell inside the Flatpak's container
	sh build/flatpak.sh shell

# --- does the *released* artifact draw a window -------------------------------
#
# `gui-linux` above opens a window from the build tree, in the test container.
# This opens one from what a user downloads -- the published Flatpak, whose GTK
# and WebKit come from the GNOME runtime rather than the distribution -- and it
# runs on the Linux builders, because this Mac has no X server to draw into.
# The screenshots land in build/out/released-gui-<platform>.png.
#
#   make released-gui ARGS="--on fedora.zt"   one machine
released-gui: ## a real window from the *published* release, screenshotted
	sh build/released-gui.sh $(if $(ARGS),$(ARGS),--all)

##@ Releasing
# --- the one command ----------------------------------------------------------
#
# `make release` builds every artifact this project ships, or refuses to build
# half of them. Native on macOS, containers for Linux, and the build trees go
# on $BUILD_ROOT -- an external case-sensitive volume on this Mac -- rather
# than into Docker volumes on the VM's internal disk.
#
#   core-macos-arm64.tar.gz     native
#   core-linux-x86_64.tar.gz    container, jammy + clang 14
#   core-linux-arm64.tar.gz     container, jammy + clang 13
#   editors / fonts / manifest  platform-neutral, manifest over all of it
#   the wheel                   with the manifest stamped in
#   Libera.app                 ad-hoc signed
#   two .flatpak bundles        one per architecture
#
# Hours. `make release-check` first: it verifies the preconditions -- clean
# tree, docker, uv, iconutil, and enough disk on $BUILD_ROOT -- and prints the
# plan without building anything.
#
# **`make ship` is the one to reach for.** This target compiles the Linux cores
# in containers on this Mac, arm64 natively and amd64 under emulation, and it
# cannot produce the Flatpak bundles at all (bubblewrap's seccomp filter does
# not cross architectures). `ship` sends that work to the Linux builders, which
# is both faster and the only way the bundles get built. This one stays for a
# machine with no builders to reach.
#
#   make release ARCHES=amd64        skip Linux arm64
#   make release FORCE_NATIVE=1      rebuild the native core even if it is there
#   make release V8_BUILD_JOBS=4     a bigger or idler machine
#   make release DOCKER_MEMORY=12g   likewise
#   make release FONTS=full          the larger font pack
release-check: ## what would stop a release, without starting one
	sh build/release.sh --dry-run

release: ## the whole release, in order
	sh build/release.sh

##@ The payload origin
# --- collecting the artifacts, and putting them on the CDN --------------------
#
# A release is built on several machines -- this one, a Linux box per
# architecture, and later a second Mac and a Windows box -- and the payload
# origin is one directory that has to hold all of their cores at once. The
# builders are listed in build/builders.toml (gitignored; see the .example).
#
#   make origin-collect            scp each builder's core here, restamp the manifest
#   make origin-push               upload what the manifest names
#   make origin-check              fetch it all back and verify, with no token
#
#   DRY=1      say what would happen and change nothing
#   QUICK=1    origin-check: sizes only, skipping a quarter of a gigabyte of hashing
#   WHEEL=...  origin-check: take the manifest from a wheel rather than from this
#              tree. WHEEL=pypi asks whether what PyPI serves and what the origin
#              serves agree, which is the question nothing asked before 0.1.0.
##@ Shipping
# --- the one command ----------------------------------------------------------
#
# `make ship` is a whole release, driven from here and compiled on the machines
# that can compile it. Ten phases, in the only order they work in:
#
#   update   git pull each builder, and refuse a dirty one
#   native   the macOS core, here, because there is nowhere else for it
#   build    the Linux cores, on their own machines, in parallel
#   collect  scp every core here, restamp the manifest over all of them
#   push     upload the payload to the origin
#   check    fetch it back with no token and verify every hash
#   bundles  the two .flatpak bundles, each on a machine of its architecture
#   wheel    make verify, then the wheel
#   publish  the wheel to PyPI, the bundles and install.sh to the origin
#   verify   read the *published* wheel back and check it against the origin
#
# Hours, most of it unattended. `make ship-plan` first: it prints the plan and
# runs nothing. Every phase asserts on what the machine printed rather than on
# an exit status, because over ssh an exit status describes the shell.
#
#   make ship ARGS="build bundles"        two phases, not all ten
#   make ship ARGS="--only linux-arm64"   one builder
#   make ship ARGS="--yes"                do not stop to confirm PyPI
#
# It does not survive this terminal closing or this laptop sleeping. Run it
# under tmux.
ship: ## the whole release: build on the builders, publish everything
	python3 build/remote.py $(ARGS)

ship-plan: ## what `make ship` would do, running nothing
	python3 build/remote.py --dry-run

# Where a release has got to, measured rather than remembered: the tree, the
# artifacts on this disk, the origin and PyPI, then the next command. Read-only,
# needs no token, and it is the thing to run after a weekend.
release-status: ## where this release has got to, and the next command
	@sh build/origin.sh status

origin-collect: ## gather every platform's artifacts and restamp the manifest
	sh build/origin.sh collect

origin-push: ## upload the collected artifacts to the payload origin
	sh build/origin.sh push

origin-check: ## read the origin back as a stranger and verify every hash
	sh build/origin.sh check

# The bundles and install.sh, which the payload manifest does not name: they
# carry the *application* version and it moves independently of the payload's.
origin-extras: ## upload the Flatpak bundles and install.sh
	sh build/origin.sh extras

##@ Checking what was built
# --- checking the payload and the queue --------------------------------------

# The converter, not the host: fonts, docx -> odt -> docx, and docx -> pdf
# through doctrenderer when a payload has been built.
smoke: ## the converter: fonts, docx -> odt -> docx, docx -> pdf
	sh build/smoke.sh

# Does the patch queue still apply to the pinned SHAs? Scratch worktrees, so it
# disturbs nothing and costs seconds. Run it after editing build/patches/.
patches: ## does the patch queue still apply to the pinned SHAs?
	sh build/check-patches.sh

payload-status: ## which payload is in use, and where it came from
	uv run libera --payload-status

##@ Documentation
# --- docs --------------------------------------------------------------------

docs-serve: ## preview the documentation site
	$(MAKE) -C docs serve

docs-check: ## build the docs, failing on a broken link
	$(MAKE) -C docs check

##@ Packaging
# --- packaging ---------------------------------------------------------------

# NB: never put `build` in this list. build/ is the Euro-Office build scripts
# and the patch queue, not an artefact directory -- uv_build writes dist/ and
# nothing else. `rm -rf build` here used to delete 25 patches and 1100 lines of
# shell every time someone ran `make build`, and a later `git pull` does not
# bring a deleted working tree back: `git restore build/` does.
clean: ## remove Python caches and dist/
	rm -rf .pytest_cache .ruff_cache dist __pycache__ .mypy_cache \
		.coverage htmlcov .coverage.* *.egg-info
	adt clean

# Every build on this machine: the repository's artefacts and $BUILD_ROOT
# both, which is the payload, the native core and the container trees.
#
# Dry by default, because it deletes a day of V8, ICU and container builds and
# the list is worth a glance. `make tidy YES=1` does it.
tidy: ## remove every build (dry run; add YES=1 to do it)
	@sh build/tidy.sh

build: ## the wheel
	rm -rf dist
	uv build

publish: build ## the wheel, to PyPI
	uv publish
