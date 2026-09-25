# Developers

Libera Suite is a Python host around upstream editors. Most of the work is in the integration points: what the editor expects from a desktop host, how the payload is built, and how our changes to upstream are kept reviewable.

- [Architecture](architecture.md): the pieces and how they talk.
- [Build the payload](build.md): building the editors and the native binaries.
- [The patch queue](patches.md): how we carry changes to upstream.
- [Cutting a release](release.md): which machine makes what, and in what order.
- [Roadmap](roadmap.md): what is next and what we have decided against.

## Getting the source

```sh
git clone https://github.com/abilian/libera-suite
cd libera-suite
uv sync
```

!!! note "On Linux, the virtualenv has to see the system's PyGObject"

    The window is GTK and WebKit, whose Python half is not a wheel: it is `python3-gi`, which your distribution installs into `/usr/lib/python3/dist-packages`. A plain virtualenv never has it on `sys.path`, so `uv run libera FILE` will tell you it needs GTK even on a machine that has it.

    ```sh
    export UV_PYTHON=/usr/bin/python3    # where your distribution's gi is
    uv sync
    sed -i 's/^include-system-site-packages = false/include-system-site-packages = true/' .venv/pyvenv.cfg
    ```

    `UV_PYTHON` is the line that matters on a distribution whose Python is newer than the `3.12` in `.python-version`, which Fedora's is. uv reads it ahead of that file, and without it `uv sync` rebuilds the environment on 3.12, where a `gi` built for 3.14 cannot be imported however the virtualenv was made.

    uv rewrites `pyvenv.cfg` when it builds the environment again, which is why the `sed` comes last. With `UV_PYTHON` set it stops rebuilding, so the line is still there after a sync that installs packages.

    `libera` prints all three, with your own paths in them, when it finds itself in a virtualenv that cannot reach GTK.

    The test suite does not need this. It drives the editor through `libera --serve` and a headless browser, never opening a window. Only running the application does.

Point the application at a payload you have built, and run it:

```sh
export LIBERA_PAYLOAD=/path/to/build/out/payload
uv run libera ~/Documents/note.docx
```

## Seeing what it is doing

```sh
libera FILE          # warnings and errors only
libera -v FILE       # what it is doing: opening, saving, windows
libera -vv FILE      # and how: HTTP routes, x2t command lines
libera -vvv FILE     # and every request, as it starts and finishes
libera -q FILE       # errors only
```

`-vv` is usually the one you want when something is wrong: it prints the exact `x2t` command line, which you can then run by hand.

## What there is to run

```sh
make help
```

It reads the targets out of the Makefile, so it cannot fall behind them. A target appears there when it carries a `## summary`, which is how the ones you never type stay out of the way: the steps of `payload-all` are all still there to resume a build that failed in the middle.

`make tidy` removes every artefact a build on this machine wrote, which is mostly the Flatpak: its builddir, its ostree store and flatpak-builder's cache came to 1.4 GB on the laptop this was written on. It leaves `$BUILD_ROOT` alone, because that is the payload and the native core, and hours of V8 and ICU should not be removable by a repository-level tidy.

## Running the checks

```sh
uv run pytest                 # everything
uv run pytest -m unit         # fast and isolated
uv run pytest -m integration  # the host, against a real payload
uv run pytest -m e2e          # the editor, in a real browser
```

The suite is a pyramid, one directory per level. Markers are applied by directory:

- `tests/a_unit/` runs against nothing: no payload, server or browser.
- `tests/b_integration/` starts the host's HTTP server on a loopback port and talks to it the way the bridge does, and runs x2t out of the payload. It checks, among other things, that every format the Save As dialog offers is one the converter actually writes, because x2t refuses several ids that look perfectly plausible next to the ones it accepts.
- `tests/c_e2e/` runs the shipped command line. `libera --serve` in a subprocess, headless Chromium pointed at the URL it prints, and then assertions on what came back. It also drives the keyboard through Playwright, which needs its own browser once:

```sh
uv run playwright install chromium
```

The last one is the important one. It carries the project's one hard-won lesson: **assert on content, never on exit codes.** A converter that writes an empty file exits zero. A browser that quits early exits zero. A PDF with no glyphs in it is the right size. So the e2e run photographs the editor's own canvas from inside the page, measures ink on it, and fails if the rows of text are closer together than a line of text can be. That is what a real regression looked like while every cheaper check reported success.

Both levels below `a_unit` skip themselves when they have nothing to run against: no installed payload, or no Chromium. Set `CHROMIUM=/path/to/browser` if yours is somewhere unusual.

To look at the editor by hand, with devtools, a real browser and no window toolkit in the way, run `libera --serve`, which prints the URL it is listening on:

```sh
uv run libera --serve ~/Documents/note.docx --port 43110
```
