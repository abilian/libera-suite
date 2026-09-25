# Documentation, built with Zensical (https://pypi.org/project/zensical/).
#
# Zensical is a dev dependency of libera itself, so `--project ..` runs it from
# the repository's venv rather than needing one in here.

.PHONY: all build serve check clean publish deploy figures shots images

ZENSICAL = uv run --project .. zensical

all: build

# Build to docs/site/.
build:
	$(ZENSICAL) build

# Live-reloading preview.
serve:
	$(ZENSICAL) serve

# The images, regenerated. Neither runs as part of `build`: figures need
# svg-plus, and shots need a payload, a browser and about two minutes.
images: figures shots

figures:
	cd figures && uv run --with svg-plus python document_flow.py
	cd figures && uv run --with svg-plus python what_runs_where.py

# Point LIBERA_PAYLOAD at the payload whose chrome you want photographed: an
# older installed one will quietly give you last release's colours.
shots:
	uv run --project .. --with playwright python shots.py

# Fail on warnings — a broken cross-reference is a broken build.
check:
	$(ZENSICAL) build --strict

# Publish
publish: clean build
	hop3 deploy --context prod -y

# Alias for publish
deploy: publish

clean:
	rm -rf site .cache
