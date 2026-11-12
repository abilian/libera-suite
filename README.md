# Libera Suite

**A desktop office suite you can own.** Libera Suite opens the documents other people send you (`.docx`, `.xlsx`, `.pptx`, ODF), edits them on your machine and saves them back. It runs on your own computer, with no account to create and nothing in it that phones home.

Five editors share one application. The file picks the editor, so there is nothing to choose.

| | |
| :--- | :--- |
| **Libera Words** | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | `.pptx` `.odp` |
| **Libera PDF** | `.pdf`: comment, fill in, rearrange |
| **Libera Diagrams** | opens `.vsdx` to read |

![Libera Words, with a document open: the editor's toolbar in the Libera Words purple, and a laid-out page below it.](https://docs.liberasuite.eu/en/assets/words.png)

Abilian builds the host as free software under the Apache License 2.0. The editors inside it come from [Euro-Office](https://github.com/Euro-Office) (itself an AGPL fork of ONLYOFFICE by Ascensio System SIA), running locally, with a short patch queue of our own: it makes them build on every platform, brands them, sets a few of the editor's options, and fixes bugs, most of them in the converter.

## Using it

```sh
libera report.docx        # a window, in Words, because the file says so
libera budget.xlsx        # Tables
libera *.pptx             # one window each
libera                    # the start window: new, open, recent
```

![The start window, with a New tile for each of Document, Spreadsheet and Presentation, an Open button, and a Recent list of three documents.](https://docs.liberasuite.eu/en/assets/start.png)

[What works today](https://docs.liberasuite.eu/en/main/status/) sets out the full list with its gaps. It covers editing, saving and exporting, with PDF in the Save As popup. It also covers blank documents, images, printing, spell check in six languages, crash recovery and a Recent list.

```sh
libera -v FILE            # what it is doing; -vv how; -vvv every request
libera --diagnose         # everything worth pasting into a bug report
libera --payload-status   # which editors are in use, and the revisions they were built from
```

## How it works

The editors are a web application. Everything they cannot do in a browser (read a file from disk, convert it, save it, list the fonts, put a dialog on screen) they ask of one injected JavaScript object, `window.AscDesktopEditor`, which the host exists to answer.

We implement it in Python, behind the webview your system already ships. The host serves the editor over a loopback HTTP server and defines `AscDesktopEditor` before the editor's own code runs, so nothing about the editor itself changes.

| | |
| :--- | :--- |
| **The payload** | The editors: `sdkjs`, `web-apps`, the `x2t` converter, fonts, dictionaries. Built from upstream sources pinned by SHA, plus our patch queue. Two Python packages, `libera-core` and `libera-web`, about 100 MB to download, or inside the bundle. |
| **The host** | `src/libera/`: the loopback HTTP server, the webview, the file dialogs, the menu bar and the converter calls, in about 12,000 lines of Python across 60 modules. All of the desktop application is here. |
| **The bridge** | Three small JavaScript files, spliced into the `<head>` of every page the host serves. Our code and theirs never share a file. |

**We do not fork the engine.** The patch queue makes upstream build on macOS and Windows, brands it, sets a few of the editor's options (no upstream helpdesk, no macros), and fixes bugs: in the converter, mostly for OpenDocument files, and a handful in the editors, among them font substitution and two cross-site scripting holes. Each patch is small and explained, so following upstream means rebasing a short series. Every release records the exact revisions it was built from, so the corresponding source is a commit plus a series that provably reapplies to it, and `lb payload check` checks that it still does.

Everything we ship, we build. [`build/`](build/README.md) compiles the editors and the native converter from pinned upstream sources, on all three systems, with our patch queue applied.

## Where it stands

**Early, and running.** All five editors work today on **Windows** 10 and 11 (x64), **Linux** (x86_64; arm64 stays on 0.4.1) and **macOS** (Apple Silicon).

Tabs on Linux and Windows, and signing on macOS and Windows, are still to come. Linux and Windows have a menu bar drawn in the window, which shows few keyboard shortcuts on Linux and none on Windows. [What works today](https://docs.liberasuite.eu/en/main/status/) lists the known issues, so an evening spent reporting one is an evening wasted. [The roadmap](https://docs.liberasuite.eu/en/develop/roadmap/) says what comes next and what we have decided against.

The most useful thing you can send us is a document that renders wrongly, attached. The layout engine is upstream's and mature, so where output is wrong it is far more likely to be our packaging (a font we did not ship, a resource we failed to serve) than the engine.

## Installing it

[Install](https://docs.liberasuite.eu/en/main/install/) gives the full instructions for each platform. There are four ways in. The first works on Linux and macOS alike.

**One command, no root.** It picks the channel that suits the machine:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

**Homebrew**, on Linux and macOS alike:

```sh
brew install abilian/tap/libera
```

**Linux: the Flatpak.** The bundle includes the editors, GTK and WebKit, so there is nothing else to fetch and nothing to get wrong:

```sh
arch=amd64     # or arm64
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

**From PyPI**, where the editors are two packages of their own, `libera-core` and `libera-web`, which `libera` requires:

```sh
pipx install --system-site-packages libera        # Linux: the flag is not optional
uv tool install libera                            # macOS
```

> **Linux is x86_64**; arm64 stays on 0.4.1 for now. The converter is built on Ubuntu 22.04 and needs glibc 2.34 and GLIBCXX 3.4.29: Ubuntu 22.04, Debian 12, Fedora 36, RHEL 9 and anything newer, measured in a clean container of each. The Flatpak needs none of that, since the editors inside it run against the GNOME runtime.
>
> **macOS is Apple Silicon**, on macOS 14 or later. There is no Intel build.

## Building it

```sh
git clone https://github.com/abilian/libera-suite && cd libera-suite
uv sync
make payload                     # fetch, patch, build, assemble, smoke-test (long: V8 alone is ~30 min)
export LIBERA_PAYLOAD="$BUILD_ROOT/out/payload"
uv run libera document.docx
```

```sh
make verify                  # everything below, in the order that fails fastest
make test                    # unit, the host over HTTP, the editor in headless Chromium
make lint                    # ruff, ty, pyrefly, mypy, biome — green, and expected to stay that way
lb payload test             # the converter: fonts, docx -> odt -> docx, docx -> pdf
lb payload check           # does the patch queue still apply to the pinned SHAs?
```

The test suite enforces one house rule: **assert on content, never on exit codes.** A converter that writes an empty document exits zero. A PDF with no glyphs in it is the right size. So the end-to-end run photographs the editor's own canvas and measures the ink on it.

| | |
| :--- | :--- |
| `docs/` | The documentation site, published at <https://docs.liberasuite.eu/>. Start at [Developers](https://docs.liberasuite.eu/en/develop/). |
| `notes/` | Where the reasoning lives: vision, specs, architecture, packaging, our relationship with upstream, the bugs that escaped to a user, a survey of how Euro-Office is put together. It stays in the development repository. |
| [`build/`](build/README.md) | Building the editors and the native binaries from pinned source plus our patches. |

The package and the command are `libera`. The repository directory is `local-office`.

## Credit

Libera Suite includes components from [Euro-Office](https://github.com/Euro-Office), itself a fork of [ONLYOFFICE](https://www.onlyoffice.com/) by Ascensio System SIA. Those components are AGPL v3 and are modified. The same line appears in Help ▸ About inside the application, in the editor's own About panel, and in what a software centre shows for the Flatpak.

The editors, the document engine and the format support are theirs. That is the hard part: twenty years of correctly reading a `.docx` written by somebody else's software. The host, the packaging and the desktop integration are ours. We are grateful for both.

## Licence

Libera Suite ships as two artifacts under different licences.

**The host is [Apache-2.0](LICENSE)**: everything in `src/libera/`, which is the whole of this package.

**The editor payload is AGPL-3.0**: Euro-Office plus our patch queue against it (GUI assets are CC-BY-SA-4.0). It arrives as two packages of its own, `libera-core` and `libera-web`, or inside a bundle, never vendored into the host's wheel.

[Licence and attribution](https://docs.liberasuite.eu/en/licence/) has the corresponding-source detail: what each release records, and where to fetch it.
