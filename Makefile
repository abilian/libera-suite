# There is no CI. `make verify` is what "everything passed" means here.
#
# The workflow in .github/ is unrun template scaffolding, and could not run the
# real checks anyway: the payload and a browser are local things.
#
# The standard jobs only, and three of this project's own. Building, packaging
# and releasing are `lb` (build/src/libera_build), whose --help lists every option and gives
# examples, which a make target with an environment variable cannot.

.PHONY: help all verify lint lint-py lint-js lint-linux format \
	test test-unit test-integration test-e2e test-gui \
	docs docs-serve docs-publish clean build publish payload ship

LB := uv run lb

# `make` on its own runs lint and the suite; `make help` lists the targets.
#
# Read out of this file rather than written beside it: a hand-kept list is a
# second copy of the target names, and a second copy drifts. A target shows up
# here when it carries a `## summary`.
.DEFAULT_GOAL := all

help: ## list these targets
	@awk 'BEGIN { FS = ":.*## " } \
		/^[a-z][a-z0-9-]*:.*## / { printf "  %-18s %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@echo
	@echo "  lb --help            building, packaging, releasing (uv run lb, outside the venv)"

all: lint test ## lint, then the whole test suite

# Everything, in the order that fails fastest. Needs an installed payload, a
# browser, and a built core for the last two.
verify: lint test docs ## everything: lint, tests, docs links, patch queue, converter
	$(LB) payload patches
	$(LB) payload smoke

# The editors in every language they ship, not test's sample: about 9 minutes
# more (tests/c_e2e/host/test_languages.py). Prerequisites see it too.
verify: export LIBERA_ALL_LOCALES = 1

# --- static ------------------------------------------------------------------

lint: lint-py lint-js ## ruff, ty, pyrefly, mypy on src, plus biome on the bridge JS

# The type checkers run once per platform, wherever `make lint` runs.
#
# `sys.platform` is a fact at check time: a checker prunes the branches for
# every other platform before looking at them, and reports an attribute that
# only exists elsewhere -- `os.startfile`, `ctypes.windll`, `pwd` -- as missing.
# So each machine used to lint clean on code that failed on the others. Three
# rounds of it reached main from Windows (SO_EXCLUSIVEADDRUSE, then four
# `startfile`/`windll` reads), and one went the other way unseen: `pwd` in a
# path Windows reaches, which only ran because a swallowed ImportError hid it.
#
# Each checker spells the flag and the platform its own way, hence three lists.
# About five seconds for all nine, against one for three.
# The application, and the build tooling (build/src/libera_build).
TYPED             := src build/src

TY_PLATFORMS      := darwin linux win32
PYREFLY_PLATFORMS := darwin linux windows
MYPY_PLATFORMS    := darwin linux win32

lint-py:
	uv run --active ruff check
	uv run --active ruff format --check
	@set -e; for p in $(TY_PLATFORMS); do \
		echo "uv run --active ty check --python-platform $$p $(TYPED)"; \
		uv run --active ty check --python-platform $$p $(TYPED); done
# The scripts outside src that import it: a signature changed there broke
# docs/shots.py with nothing to say so.
	uv run --active ty check docs/shots.py docs/cards.py \
		build/test-linux/dialog-smoke.py build/windows/associations.py
	@set -e; for p in $(PYREFLY_PLATFORMS); do \
		echo "uv run --active pyrefly check --python-platform $$p $(TYPED)"; \
		uv run --active pyrefly check --python-platform $$p $(TYPED); done
	@set -e; for p in $(MYPY_PLATFORMS); do \
		echo "uv run --active mypy --platform $$p $(TYPED)"; \
		uv run --active mypy --platform $$p $(TYPED); done
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

# The same checkers on Linux, in the test container. `sys.platform` is a fact
# at check time, so on a Mac every non-macOS branch goes unchecked; two real
# defects hid there.
lint-linux: ## the type checkers on Linux, where the Linux branches are live
	$(LB) linux lint

format: ## reformat the Python and the JavaScript
	uv run --active ruff format src tests build/src
	uv run --active ruff check src tests build/src --fix
	uv run --active ruff format src tests build/src
	npx --yes @biomejs/biome@2.5.13 check --write

# --- tests -------------------------------------------------------------------
#
# Markers come from the directory (see tests/conftest.py). The upper two levels
# install what they need the first time (the payload this tree wants, and
# Playwright's Chromium), and skip only when that cannot be done.

test: ## the whole suite (~4 min); `uv run pytest` takes its options
	uv run pytest

test-unit: ## fast and isolated; needs no payload and no browser
	uv run pytest -m unit

test-integration: ## the host over HTTP; needs an installed payload
	uv run pytest -m integration

test-e2e: ## the editor in headless Chromium; needs a payload and a browser
	uv run pytest -m e2e

# Real windows, on this platform: skipped by every other run, because they
# take the focus while they are up. On Linux they need a display --
# `lb linux gui-test` brings an Xvfb one.
test-gui: ## the application in a real window, in the engine that ships
	uv run pytest -m gui

# --- docs --------------------------------------------------------------------
#
# The site is its own deployment and no part of `ship`: it carries no version,
# refers to no artifact by hash, and a typo in it should not wait for a release.

docs: ## build the documentation site, failing on a broken link
	$(MAKE) -C docs check

docs-serve: ## preview the documentation site
	$(MAKE) -C docs serve

docs-publish: ## deploy the documentation site to docs.liberasuite.eu
	$(MAKE) -C docs publish

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

build: ## the wheel
	rm -rf dist
	uv build

publish: build ## the wheel, to PyPI
	uv publish

# --- this project's own ------------------------------------------------------

# The payload for this machine, from a clean checkout: hours the first time.
payload: ## build the editor payload here (lb payload --help for the steps)
	$(LB) payload all

# The release, on the builders. Phases and --only: lb release --help.
ship: ## the whole release (lb release ship --help for its phases)
	$(LB) release ship
