# Install

Libera Suite runs on **Linux (x86_64 and arm64)** and **macOS (Apple Silicon)**. Windows is planned; see [What works today](status.md).

The Linux requirement is a **glibc version**, which cuts across distributions. The converter
in payload 0.2 needs **glibc 2.34** and **GLIBCXX 3.4.26**, the latter from GCC
9.1 or newer. Your machine answers the first question:

```sh
ldd --version | head -1
```

Anything from late 2021 onwards clears it. Ubuntu 22.04 and Debian 12 were
measured, by unpacking the published core in a clean container of each and
running `x2t`; Fedora 35, RHEL 9 and its rebuilds, and the rolling
distributions are all above the line by their own glibc versions. Debian 11,
RHEL 8 and openSUSE Leap 15.x are below it.

**musl is not glibc**, so Alpine will not run the payload at all, whatever its
version.

If you are below the line, the Flatpak is the answer: the editors inside it run
against the GNOME runtime's own libraries, so the host's glibc stops mattering.
How far back that goes is set by Flatpak itself and we have not measured it.

Payload 0.1 needed Ubuntu 24.04. If you installed it before, `libera
--payload-install` moves you on.

!!! warning "Do not install 0.1.0"

    `libera` 0.1.0 is on PyPI and cannot install its payload: it looks for the manifest that verifies downloads in the wrong directory. The hashes it carries describe artifacts that were rebuilt after it was published. It is **not yanked yet**, so `pipx install libera` can still choose it: ask for `libera>=0.1.1` until it is.

## The quickest way

One command installs it on either platform, without root. It works out which
channel suits the machine and takes that one:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

On Linux that installs the Flatpak bundle when `flatpak` is present, which
brings its own GTK and WebKit and skips every question below. Otherwise it
builds a virtualenv against your system Python. On macOS it always does the
latter.

It writes to `~/.local/bin` and `~/.local/share` and nowhere else, and asks for
no password. Read it first if you would rather: it is served as plain text, so
opening the URL in a browser shows it.

A pipe cannot pass options on its own, because the shell takes them for itself.
`-s --` says the rest of the line belongs to the script:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
```

| | |
| :--- | :--- |
| `--prefix DIR` | install somewhere else (default: `~/.local`) |
| `--channel pip` | on Linux, skip the Flatpak and use the Python package |
| `--no-payload` | install the command now, fetch the editors later |
| `--origin URL` | somewhere other than the public origin |

The rest of this page is what that script does, for anyone who would rather do
it by hand or needs a piece of it.

## 1. The application

On Linux, the command carries two flags:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
```

On macOS, neither is needed:

```sh
uv tool install libera      # or: pipx install libera
```

Libera Suite's window is GTK and WebKit. The Python half of those (PyGObject) is not a wheel. It is a package your distribution installs at `/usr/lib/python3/dist-packages/gi`. An isolated virtualenv never has it on `sys.path`, however thoroughly you have installed it. Measured on a Debian box carrying every package below:

| | |
| :--- | :--- |
| `pipx install libera` | no window |
| `pipx install --system-site-packages libera` | works |
| `uv tool install libera` | no window |

**`uv tool` has no equivalent flag**, so on Linux there is no spelling of it that opens a window. That leaves `pipx`, or the Flatpak, which brings its own GTK and WebKit and sidesteps the whole question. `--python` is there for the same reason: your distribution built PyGObject for one interpreter. `--system-site-packages` opens the virtualenv onto whichever interpreter it was made from. A pipx that defaults to a newer Python than your distribution ships installs cleanly and still cannot find `gi`. `libera` names both versions when that happens.

You also need the system packages themselves. `libera` checks before it does anything else and prints the line for your distribution, so if you are unsure, just run it. It knows apt, dnf, pacman and zypper. On anything else it names the three components instead: four commands, none of which exists, are four wrong answers.

This gives you the `libera` command, which is small and cannot edit anything until it has the payload.

### Or, on Linux, the Flatpak

The bundle carries GTK, WebKit and their Python bindings in the GNOME runtime, so none of the above applies. There are no system packages to install and nothing to get wrong:

```sh
arch=amd64     # or arm64, for your machine
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` is one line of text naming the current version, so those commands do not go stale.

**Skip step 2.** The editors are inside the bundle, so there is nothing to fetch, nothing to verify and nothing that needs the network. The download is about 82 MB, and it installs offline apart from the GNOME runtime: the bundle carries the application and not the runtime, so `flatpak` fetches `org.gnome.Platform` from Flathub the first time. A machine with no flathub remote needs one adding first:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Updates do not re-download the editors, because Flatpak stores files by content hash: a release that only changes the application moves only the application. There are two bundles, one per architecture, because a Flatpak cannot be cross-built.

A hosted `.flatpakref`, so that installing takes one URL, is on the [roadmap](../develop/roadmap.md).

### Or, either platform, Homebrew

Homebrew runs on Linux and macOS alike. The line is the same on both:

```sh
brew install abilian/tap/libera
```

It builds in Homebrew's own prefix and brings its own GTK, WebKit and PyGObject
on Linux, so none of the system-package question above applies there. On macOS nothing is signed or notarised; Gatekeeper has nothing to say about a formula. Step 2 still applies: the editors are fetched separately.

## 2. The payload

**Not needed if you installed the Flatpak**, which carries its own. A 120 MB wheel per platform is not something to put on PyPI, so `pipx` is the one channel that has to fetch the payload separately.

The payload holds the editors, the document engine and the fonts. Ask for it explicitly:

```sh
libera --payload-install
```

It downloads about 120 MB from `cdn.abilian.com` (107 MB on macOS), checks every artifact against hashes that shipped inside the wheel, and stops on the first that disagrees. The origin is therefore ordinary storage: a mirror needs no cooperation from us, because the hashes decide.

If you have built the artifacts yourself, or been given them, install from a directory instead:

```sh
libera --payload-install --from /path/to/artifacts
```

Building them yourself is documented in [Build the payload](../develop/build.md).

The install unpacks the files and then runs a font indexer locally, because some of the payload's files record absolute paths and have to be generated on your machine.

## Check what you have

```sh
libera --payload-status
```

## Where things live

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, or `~/.local/share/libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |

The payload sits under `payload/<version>/` there; nothing else on your system is touched.

To point Libera Suite at a payload somewhere else (a local build, say), set `LIBERA_PAYLOAD` to its directory. That overrides everything else and lets you develop against a payload you have not installed.

## A double-clickable application

This gives you an icon, *Open With*, and documents that open on a double-click.

On Linux, one command:

```sh
libera --launcher-install
```

It writes a desktop entry and the icon under `$XDG_DATA_HOME`, for your account alone, and tells the desktop about the formats Libera Suite reads. The Flatpak ships both already, so the command declines there and says so.

On macOS, build an application bundle:

```sh
build/macos-app.sh          # builds build/out/Libera.app
open build/out/Libera.app
```

The bundle is unsigned and unnotarised. It launches the interpreter it was built against, so it belongs to your checkout. `/Applications` is not its home; move the checkout and rebuild it.

## Remove it

```sh
libera --payload-remove     # the editors
libera --launcher-remove    # on Linux, the desktop entry and its icon
```
