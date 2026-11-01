# Developers

Libera Suite is a Python host around upstream editors. Most of the work is in the integration points: what the editor expects from a desktop host, how the payload is built, and how our changes to upstream are kept reviewable.

- [Architecture](architecture.md): the pieces and how they talk.
- [Build the payload](build.md): building the editors and the native binaries.
- [The patch queue](patches.md): how our changes to upstream are kept.
- [How this is tested](testing.md): the pyramid, and what each level is allowed to trust.
- [Cutting a release](release.md): which machine makes what, and in what order.
- [Roadmap](roadmap.md): what is next and what we have decided against.

## In six slides

<div class="deck" data-pdf="../pdf/Libera%20Suite%20for%20developers.pdf"><a href="../pdf/Libera%20Suite%20for%20developers.pdf">Libera Suite for developers, in six slides (PDF)</a></div>

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
make help             # the standard jobs: lint, test, docs, the wheel
lb --help             # building, packaging, releasing
```

The Makefile holds what any Python project has, plus `make payload` and `make ship`. Everything else is `lb` (`uv run lb` outside the virtualenv), a group per job (`payload`, `toolchain`, `app`, `linux`, `release`), and `--help` at every level lists the options with examples, each naming the environment variable it sets. The steps of `make payload` are each a command, to resume a build that failed in the middle: `lb payload --help`.

`lb tidy` removes every artefact a build on this machine wrote, which is mostly the Flatpak: its builddir, its ostree store and flatpak-builder's cache came to 1.4 GB on the laptop this was written on. It leaves `$BUILD_ROOT` alone, because that is the payload and the native core, and hours of V8 and ICU should not be removable by a repository-level tidy.

## Running the checks

```sh
uv run pytest                 # everything
uv run pytest -m unit         # fast and isolated
uv run pytest -m integration  # the host, against a real payload
uv run pytest -m e2e          # the editor, in a real browser
```

The suite is a pyramid, one directory per level, and the marker comes from the directory. The two upper levels skip themselves when they have nothing to run against: no payload, or no Chromium (set `CHROMIUM=/path/to/browser` if yours is somewhere unusual). A skip and a pass look the same in pytest's summary line, so the run names the payload it found before anything executes.

[How this is tested](testing.md) is the whole picture: what each level may trust, why the e2e tier measures pixels, and which checks only exist on the builders.

To look at the editor by hand, with devtools, a real browser and no window toolkit in the way, run `libera --serve`, which prints the URL it is listening on:

```sh
uv run libera --serve ~/Documents/note.docx --port 43110
```
