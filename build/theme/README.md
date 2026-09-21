# Our theme

Branding in `web-apps` is a directory under `web-apps/theme/`, selected by `THEME`. We keep ours here instead and `payload.sh` assembles it into the pinned source tree at build time — additive, so it stays out of `patches/` and `build.sh fetch`'s `git clean` removes it again.

`libera` is **standalone**. It used to be copied over `theme/euro-office` with only our `meta/config.json` on top, because we had no artwork of our own and inheriting theirs tracked their changes. We have artwork now, so it carries its own LESS and its own images and shares nothing.

## What is in it

`meta/config.json` is the brand surface: company name, URLs, the attribution line, and which file each logo slot uses. Every key also has an environment-variable override (`COMPANY_NAME`, `PUBLISHER_URL`, `ATTRIBUTION`, …) — except `loader_logo` and `loader_logo_dark`, which are config-file-only.

`assets/less/theme.less` is imported **last** by every editor's `app.less`, through a stub `build/theme.config.mjs` writes. LESS resolves a variable to its last definition, so a variable set there beats the one upstream declared — `@brand-primary` is one line and reaches every `.btn-primary` in the build. Prefer a variable; `overrides/` is for what cannot be one, and today that is one thing, the per-editor header colour.

`assets/img/` holds two drawings and no duplicates:

| file | what it is |
| :--- | :--- |
| `header/wordmark-ink.svg` | `libera`, ink, for a light ground |
| `header/wordmark-paper.svg` | the same drawing with the ink fill swapped for paper, for a dark one |

The source of truth is `brand/svg/` in the branding repository, built by its own `build_svgs.py` from the Lato outlines. Change a drawing there and copy it here; do not edit one in place. `wordmark-paper.svg` is the one file with no counterpart there — it is `wordmark-libera.svg` with `#1E1A17` replaced by `#F6F1E9`, and `diff`ing the two with both fills normalised should show no other difference.

**No tiles here, and that is measured rather than an oversight.** The header's logo slot is `<div class="extra">`, and in a desktop build nothing ever fills it: `#header-logo` is created only for a page given a `customization.logo`, and this host gives the editor no config object at all. Euro-Office's theme carried five per-editor icon rules pointed at that slot, so they had never rendered either. The per-editor identity in the editor is the header *colour*; the tiles live on the start window and on the application icon.

## The four names that are not ours

Upstream hardcodes four logo filenames, two in `about.less` and two in `header.less`, so our artwork has to arrive under them. `payload.sh` copies the two wordmarks to those four names after the theme is in place; the table is in that script, and it is the reason nothing in our LESS overrides a logo. Two of the names, `about/logo_s.svg` and `about/logo-white_s.svg`, hold **ONLYOFFICE's own wordmark** in the stock tree, and `deploy-theme-images.js` overlays rather than replaces — so a file of that name in the theme is the only thing that keeps it out of the payload.

A fifth, the embedded viewer's, no theme can reach at all: `deploy-theme-images.js` writes a theme's `embed/logo.svg` into each `apps/<editor>/embed/resources/img/`, while the only stylesheet that asks for one reads `apps/common/embed/resources/img/logo.svg` — which nothing writes. So the copies it makes are unreferenced and the one that renders is upstream's. `payload.sh` overwrites it after the build instead.

A sixth was not a logo slot at all and needed a patch: `apps/<editor>/main/resources/img/favicon.ico` is ONLYOFFICE's stacked-sheets device, and `deploy-theme-images.js` writes nothing into `<editor>/main/`. `build/patches/web-apps/0006-brand-drop-the-ONLYOFFICE-favicon.patch` deletes it and the `<link>` that would otherwise 404.

**What keeps this honest is not the list.** `build/dist.sh` enumerates every brand-shaped file in the staged tree and fails unless each one is ours — an allowlist, because the file that matters is the one nobody thought to look for. Add a drawing here and its name goes in `OURS` there.

`loader_logo` and `loader_logo_dark` are paths, not filenames, and that is deliberate: the token is substituted into `index_loader.html` as a bare `src`, which resolves against `apps/<editor>/main/` and not against the image directory. Upstream's default therefore 404s — `web-apps/build/README.md` lists it as a known one — and the loading screen shows a broken image. The `../../common/main/resources/img/header/` prefix is what makes it load.
