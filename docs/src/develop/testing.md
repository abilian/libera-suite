# How this is tested

Everything except the native window is automated, and one checkout drives all of it. One command runs the suite locally, another runs the same suite in a Linux container, and the same command reaches either Linux builder over ssh. The application in its real window runs under test on all three platforms; what is still done by hand is the menus and the dialogs, which need a click.

```sh
make verify                        # locally: lint, 1027 tests, docs, patch queue, converter
make test-gui                      # the application in a real window, here
lb linux test                      # the same suite, in the Linux test container
lb linux gui-test                  # the real window too, under Xvfb
lb on linux-x86_64 linux gui-test  # the real window, on the x86_64 builder
lb on windows-x86_64 app windows-gui-test   # and in WebView2, on the Windows builder
```

## The three platforms

| | What runs automatically | Where |
|---|---|---|
| **Linux** x86_64, arm64 | the whole suite, the real GTK window, the type checkers | the test container, locally or on either builder |
| **macOS** arm64 | the whole suite, the real AppKit window, the type checkers, the docs checks | natively, on a machine with a payload |
| **Windows** x64 | the patch queue on every push, the payload and the installer, the real WebView2 window | a GitHub runner, and the Windows builder |

**Linux** has the most automation, because all of it fits in a container. `lb linux test` mounts a payload, installs Chromium and runs `pytest` inside the image, so the integration and end-to-end tiers run there exactly as they do natively. `lb linux gui` goes further and opens a real GTK window under Xvfb, screenshots it and counts the colours in the image: under two dozen means the window came up empty, which is how a WebKit that refuses to paint presents itself. `lb linux dialog` answers the GTK question the host asks before overwriting a file. Both arches are real machines (`build/builders.toml`), and `lb on PLATFORM COMMAND…` runs any of this on either one, against the commit the calling checkout sits at.

**macOS** runs the whole suite natively, under `make verify`. Its window layer is AppKit through pywebview, which nothing headless drives, so the menu bar, the file dialogs and printing are checked by opening the application.

**Windows** is the thinnest. On every push that touches `build/`, `.github/workflows/windows.yml` verifies that the patch queue still applies with `core.autocrlf` off, which is a corruption a Mac cannot reproduce. A version tag builds the payload and the installer on a hosted runner. The Windows builder does the same for a release. The `gui` tier runs there too, with `lb on windows-x86_64 app windows-gui-test`: an ssh session has no desktop, so `build/windows/gui-test.sh` runs the tier as a scheduled task in the desktop session of the user it connects as, at the console or over Remote Desktop, which must be active, and hands back pytest's output. The rest of the suite does not run on Windows yet.

A Linux payload has to be built on Linux. A Flatpak bundle cannot be cross-built at all, because bubblewrap's seccomp filter is per-architecture. The builders exist for that reason. It is also why "run the tests on every platform" means ssh rather than a matrix in a YAML file.

## Why not a hosted CI run

The suite needs the editor payload: `x2t` as a real binary, the fonts, the blank documents, several hundred megabytes of it, built from pinned upstream sources over several hours. The upper tiers need a browser as well. A hosted runner starts with none of that, so the two workflows in `.github/` do the one job that needs a Windows kernel and nothing else. The standard for "everything passed" is `make verify` on a machine that has a payload or can fetch one.

The suite finds the payload this tree wants and no other: `LIBERA_PAYLOAD` if set, an installed payload of exactly that version, this checkout's build tree (native or the container's), and otherwise that version downloaded from the origin into `~/.cache/libera-tests/`, once, checked against its manifest. It used to take any payload installed on the machine, and a checkout wanting 0.4.1 reported the bugs of a leftover 0.2 as failures. A version not yet published, with no build tree, skips the upper tiers, and the header says why.

## What the tests assert

```sh
uv run pytest                 # all of it, both trees
uv run pytest -m unit         # 562 tests, against nothing at all
uv run pytest -m integration  # 160, the host over HTTP against a real payload
uv run pytest -m e2e          # 83, the editor in headless Chromium
uv run pytest -m gui          # 3, the application in a real window
```

Each level sits in its own directory, which also supplies the marker on every test it holds. `build/tests/` holds another 216 for the build and release tooling, which need no payload. The whole run takes about five minutes.

The `gui` tier runs in the engine a user has. It launches the shipped CLI on two documents of different types and lets it open real windows. Each window's own page then photographs its canvas and posts it to the host: `libera --shot FILE` arms that in a window as well as under `--serve`, each window posting to a name of its own. The ink measurement below therefore runs against WKWebView, WebKitGTK or WebView2, with no screenshot utility and no screen-recording permission anywhere.

Two things keep that safe to run on a machine somebody is using. Every launch gets a home of its own, so it cannot hand its documents to a Libera Suite the user has open, nor leave any state behind. The tier is also skipped unless a run asks for it by marker, because a real window takes the focus while it is up. On Linux it wants a display, which `lb linux gui-test` supplies with Xvfb; on Windows a logged-on session, which `lb app windows-gui-test` reaches through a scheduled task. A run in which every test skipped itself is a failure there, not a pass.

The assertions open the output, because this toolchain reports success on broken results. `allfontsgen` exits 0 having found no fonts and writes a well-formed `AllFonts.js`, after which the editor draws every glyph as a box. `x2t in.docx out/Editor.bin` writes a blank document and exits 0, because it takes the output format from the extension and `.bin` names none. So the end-to-end tier photographs the editor's own canvas from inside the page and measures the ink on it. Rows of dark pixels are grouped into bands. The check complains if there are too few bands, if two sit closer together than a line of text can be, or if one is a hairline rule. A regression in the blank documents collapsed the leading, and the pages rendered as overlapping, struck-through lines while every cheaper check passed. A good render has band pitch `[30, 17, 30]`; that one had `[12, 5, 23]`.

Three tests check the code against its own documentation: the layer order in `host/__init__.py` against the real import graph, the HTTP route table against the list the API exposes, and each platform's window module against the `Toolkit` protocol every platform answers.

## The type checkers run once per platform

```sh
make lint          # ruff, ty, pyrefly, mypy, biome
make lint-linux    # the same type checkers in the Linux container
```

`sys.platform` is a fact at check time, so a checker on a Mac prunes every non-macOS branch before looking at it. Each machine used to pass on code that failed on the others, and three rounds of that reached `main` from Windows. `make lint` runs `ty`, `pyrefly` and `mypy` once per platform each (`darwin`, `linux`, `win32`), which costs about five seconds in total. `make lint-linux` runs them inside the container, where the Linux branches are live code: two defects hid there, a `Window | None` dereferenced in `set_fullscreen` and a list with no inferrable element type in `find_front_window`.

## What a release checks that a test run cannot

The suite tests this checkout. These read what a user downloads:

- `lb release check` fetches the published payload as a stranger would and verifies every hash.
- `lb release matrix` converts a document with the Linux cores about to be published, in a clean container of each distribution the install page names, and looks for the text in the output. Its first run found the page claiming Fedora 35 and RHEL 9, where glibc 2.34 cannot load a core that needs 2.35.
- `lb release released-gui` runs the *published* Flatpak on each Linux builder under Xvfb and screenshots it. It is the only check that exercises the GNOME runtime's WebKit, which is not the distribution's.

Each release phase verifies its own artifact too, after the bundle phase once found a core tarball an earlier build had left behind and reported a pass for a bundle it never produced.

## The documentation

```sh
cd docs
make check       # all six editions, strict: a broken cross-reference fails the build
make switcher    # where a click on the language selector actually lands
```

`preprocess.py` refuses to build when a translated edition does not have exactly the pages of `docs/src/` minus `develop/`. It asks whether each page exists, never whether it is current, so a changed English page can leave its translations stale. `make switcher` drives Chromium over the built site, because the behaviour under test appears nowhere in the HTML: the interplay between `assets/lang.js` and the theme's own alternate-version handler.

## What is left to a person

- The menu bar, the file dialogs, printing, file associations and drag and drop. The menus' wiring is pinned per platform: a macOS item whose selector no class implements does nothing, silently, and a GTK item wired to the wrong callable raises on a thread where no one is reading. `lb linux dialog` answers a real GTK question from both threads it gets asked on. No test moves a pointer onto a native menu and clicks it.
- A pass over all four applications before a release goes out.
- Anything about how a document looks beyond the ink measurement above.
