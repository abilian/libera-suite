# Install

Libera Suite runs on **Linux (x86_64 and arm64)** and **macOS (Apple Silicon)**. Windows is planned; see [What works today](status.md).

On Linux it needs Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9, or anything
newer than those. On something older, use [the
Flatpak](#or-on-linux-the-flatpak): it brings its own libraries and does not
care what the rest of the machine has.

## The quickest way

One command installs it on either platform, without root. It works out which
channel suits the machine and takes that one:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

On Linux it installs the Flatpak bundle when `flatpak` is present, which
brings its own GTK and WebKit and skips every question below. Without flatpak,
and on macOS, it builds a virtualenv against your system Python instead.

It writes to `~/.local/bin` and `~/.local/share`, and asks for no password.
Open the URL in a browser to read it first.

With options:

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

Both flags are needed because the window is GTK. Its Python half is a
distribution package built for one particular interpreter, which an isolated
virtualenv cannot see. Without the flags, Libera Suite
installs cleanly and then opens no window.

**`uv tool` has no equivalent flag**, so on Linux it cannot be used. Use `pipx`,
or the Flatpak below, which brings its own GTK and needs none of this.

You also need the GTK packages themselves. Run `libera` and it prints the exact
line for your distribution; it knows apt, dnf, pacman and zypper.

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

On Linux it brings its own GTK and WebKit, so no system packages are needed.
On macOS, Gatekeeper has nothing to object to. Step 2 still applies.

## 2. The payload

**Not needed if you installed the Flatpak**, which carries its own.

The payload holds the editors, the document engine and the fonts. Ask for it explicitly:

```sh
libera --payload-install
```

It downloads about 120 MB from `cdn.abilian.com` (107 MB on macOS) and checks every file against hashes that shipped inside the application, stopping on the first that disagrees.

If you have built the artifacts yourself, or been given them, install from a directory instead:

```sh
libera --payload-install --from /path/to/artifacts
```

Building them yourself is documented in [Build the payload](../develop/build.md).

It then builds a font index on your machine, which takes a moment.

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

To use a payload from somewhere else, a local build say, set `LIBERA_PAYLOAD` to its directory. It overrides everything above.

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
