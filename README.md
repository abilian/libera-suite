# Libera Suite

**A desktop office suite you can own.** Libera Suite opens the documents other people send you (`.docx`, `.xlsx`, `.pptx`, ODF), edits them on your machine and saves them back. It runs on your own computer, with no account to create and nothing in it that phones home.

Four editors share one application. The file picks the editor, so there is nothing to choose.

| | |
| :--- | :--- |
| **Libera Words** | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | `.pptx` `.odp` |
| **Libera Diagrams** | opens `.vsdx` to read |

Abilian builds it as free software under the AGPL. The editors inside it are [Euro-Office](https://github.com/Euro-Office), an AGPL fork of ONLYOFFICE by Ascensio System SIA, running locally and unmodified.

## Using it

```sh
libera report.docx        # a window, in Words, because the file says so
libera budget.xlsx        # Tables
libera *.pptx             # one window each
libera                    # the start window: new, open, recent
```

[What works today](docs/src/guide/status.md) sets out the full list with its gaps: editing, saving and exporting (the Save As popup offers PDF), a blank document of any of the four kinds, images, printing, spell check in six languages, crash recovery and a Recent list.

```sh
libera -v FILE            # what it is doing; -vv how; -vvv every request
libera --diagnose         # everything worth pasting into a bug report
libera --payload-status   # which editors are in use, and the revisions they were built from
```

## How it works

The editors are a web application. Everything they cannot do in a browser (read a file from disk, convert it, save it, list the fonts, put a dialog on screen) they ask of one injected JavaScript object, `window.AscDesktopEditor`. That object is the whole of the integration.

We implement it in Python, behind the webview your system already ships. The host serves the editor over a loopback HTTP server and defines `AscDesktopEditor` before the editor's own code runs, so nothing about the editor itself changes.

| | |
| :--- | :--- |
| **The payload** | The editors: `sdkjs`, `web-apps`, the `x2t` converter, fonts, dictionaries. Built from upstream sources pinned by SHA, plus our patch queue. ~120 MB, installed out of tree or shipped inside the bundle. |
| **The host** | `src/libera/`: the loopback HTTP server, the webview, the file dialogs, the menu bar and the converter calls, in about 4,700 lines of Python across 32 modules. All of the desktop application is here. |
| **The bridge** | Three small JavaScript files, spliced into the `<head>` of every page the host serves. Our code and theirs never share a file. |

Five thousand lines is a codebase a small team can read in an afternoon and still be maintaining in ten years.

**We do not fork the engine.** The patch queue is 28 patches across three upstream repositories: 24 of them make it build on macOS, 3 are configuration and branding, 1 fixes an upstream UI bug. **None touches the editing engine**, so following upstream means rebasing build configuration. Every release records the exact revisions it was built from, so the corresponding source is a commit plus a series that provably reapplies to it, and `make patches` checks that it still does.

Everything we ship, we build. [`build/`](build/README.md) compiles the editors and the native converter from pinned upstream sources, including on macOS, where upstream publishes no binaries of its own.

## Where it stands

**Early, and running.** All four editors work today on **macOS** (Apple Silicon) and **Linux** (x86_64 and arm64). Windows is not started.

Tabs, file locking, and signing and notarisation on macOS are still to come. Linux has a menu bar and a launcher entry; neither carries keyboard shortcuts, because pywebview's GTK menu has no way to attach them. [What works today](docs/src/guide/status.md) lists the known issues, so nobody need waste an evening reporting one. [The roadmap](docs/src/develop/roadmap.md) says what comes next and what we have decided against.

The most useful thing you can send us is a document that renders wrongly, attached. The layout engine is upstream's and mature, so where output is wrong it is far more likely to be our packaging (a font we did not ship, a resource we failed to serve) than the engine.

## Installing it

[Install](docs/src/guide/install.md) gives the full instructions for each platform.

**Linux: the Flatpak.** The bundle carries the editors, GTK and WebKit, so there is nothing else to fetch and nothing to get wrong:

```sh
flatpak install --user libera-0.1.0-amd64.flatpak     # or -arm64
flatpak run eu.liberasuite.Libera
```

**macOS, and Linux without Flatpak.** The `libera` command comes from PyPI and fetches the editors on first run:

```sh
uv tool install libera                            # macOS
pipx install --system-site-packages libera        # Linux: the flag is not optional
libera --payload-install
```

> **macOS works today.** `libera` is on PyPI and the payload origin is serving, so the block above is the real thing on an Apple Silicon Mac running macOS 14 or later.
>
> **Linux works on both architectures.** Payload 0.2 is built on Ubuntu 22.04, and `x2t` from it runs on Ubuntu 22.04 and Debian 12, x86_64 and arm64 -- measured in a clean container of each. Payload 0.1 needed Ubuntu 24.04. [Release 0.2](notes/plans/release-0.2.md) is what remains.

## Building it

```sh
git clone https://github.com/abilian/libera-suite && cd libera-suite
uv sync
make payload-all                 # fetch, patch, build, assemble, smoke-test (long: V8 alone is ~30 min)
export LIBERA_PAYLOAD="$BUILD_ROOT/out/payload"
uv run libera document.docx
```

```sh
make verify      # everything below, in the order that fails fastest
make test        # 314 tests: unit, the host over HTTP, the editor in headless Chromium
make lint        # ruff, ty, pyrefly, mypy, biome — green, and expected to stay that way
make smoke       # the converter: fonts, docx -> odt -> docx, docx -> pdf
make patches     # does the patch queue still apply to the pinned SHAs?
```

The test suite enforces one house rule: **assert on content, never on exit codes.** A converter that writes an empty document exits zero. A PDF with no glyphs in it is the right size. So the end-to-end run photographs the editor's own canvas and measures the ink on it.

| | |
| :--- | :--- |
| [`docs/`](docs/src/index.md) | The documentation site, at <https://docs.liberasuite.eu/>. Start at [Developers](docs/src/develop/index.md). |
| [`notes/`](notes/01-vision.md) | Where the reasoning lives: vision, specs, architecture, packaging, and our relationship with upstream. |
| [`notes/plans/`](notes/plans/release-0.2.md) | What a release still needs, with the state measured each time and the commands to finish it. |
| [`notes/lessons-learned.md`](notes/lessons-learned.md) | Bugs that escaped to a user, and what each generalises to. Read before touching the host or the bridge. |
| [`notes/euro-office-map.md`](notes/euro-office-map.md) | How Euro-Office is put together, and the `AscDesktopEditor` contract. The survey everything else is built on. |
| [`build/`](build/README.md) | Building the editors and the native binaries from pinned source plus our patches. |
| [`CLAUDE.md`](CLAUDE.md) | The orientation an agent gets, which happens to be the fastest one for a human too. |

The package and the command are `libera`. The repository directory is `local-office`.

## Credit

Libera Suite is based on [Euro-Office](https://github.com/Euro-Office), itself based on [ONLYOFFICE](https://www.onlyoffice.com/) by Ascensio System SIA. The same line appears in Help ▸ About inside the application.

The editors, the document engine and the format support are theirs. That is the hard part: twenty years of correctly reading a `.docx` written by somebody else's software. The host, the packaging and the desktop integration are ours. We are grateful for both.

## Licence

Libera Suite is **AGPL-3.0**, as is the Euro-Office code it is built from (GUI assets are CC-BY-SA-4.0). The host loads upstream's JavaScript in-process and injects code into their runtime, which reads as a combined work. The whole of it is therefore AGPL, and stays that way.

[Licence and attribution](docs/src/licence.md) has the corresponding-source detail: what each release records, and where to fetch it.
