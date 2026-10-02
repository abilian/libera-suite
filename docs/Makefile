# Documentation, built with Zensical (https://pypi.org/project/zensical/).
#
# Zensical is a dev dependency of libera itself, so `--project ..` runs it from
# the repository's venv rather than needing one in here.

.PHONY: all preprocess build serve preview check clean publish deploy figures shots cards images

ZENSICAL = uv run --project .. zensical

all: build

# Every edition's news, and every edition but English's config and assets:
# see preprocess.py. Each edition builds to its own site/<lang>/, English from
# zensical.toml and the others from the generated zensical.<lang>.toml; then
# SITE_ROOT writes what is at the root, which belongs to none of them: the
# chooser (index.html), and redirects from where English used to be.
preprocess:
	uv run --project .. python preprocess.py

SITE_ROOT = uv run --project .. python preprocess.py --site-root
EACH_EDITION = for config in zensical.*.toml; do $(ZENSICAL) build $(1) -f $$config || exit 1; done

# Build to docs/site/: every edition under /<lang>/, and the chooser at the root.
build: preprocess
	$(ZENSICAL) build
	@$(call EACH_EDITION)
	$(SITE_ROOT)

# Live-reloading, one edition at a time, so the language selector is hidden
# and the root chooser is not there: `make serve EDITION=fr` for another
# edition, and `make preview` for the whole site as it is deployed.
serve: preprocess
	$(ZENSICAL) serve $(if $(EDITION),-f zensical.$(EDITION).toml)

preview: build
	python3 -m http.server -d site 8000

# The images, regenerated. None runs as part of `build`: figures need
# svg-plus, shots need a payload, a browser and about two minutes, and cards
# need a browser and the network (Lato comes from Google Fonts).
images: figures shots cards

figures:
	cd figures && uv run --with svg-plus python document_flow.py
	cd figures && uv run --with svg-plus python what_runs_where.py

# Point LIBERA_PAYLOAD at the payload whose chrome you want photographed: an
# older installed one will quietly give you last release's colours.
shots:
	uv run --project .. --with playwright python shots.py

# The Open Graph cards, after shots: they show the Words screenshot.
cards:
	uv run --project .. --with playwright python cards.py

# Fail on warnings — a broken cross-reference is a broken build.
check: preprocess
	$(ZENSICAL) build --strict
	@$(call EACH_EDITION,--strict)
	$(SITE_ROOT)

# Publish
publish: clean build
	hop3 deploy --context prod -y

# Alias for publish
deploy: publish

clean:
	rm -rf site .cache src/news i18n/*/news i18n/*/assets zensical.*.toml
