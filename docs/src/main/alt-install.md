# Other ways to install

[Install](install.md) has the usual way in for each platform, which suits most people. This page is for everything else: choosing a channel yourself, installing by hand, and knowing where things go.

## The install script's options

`install.sh` takes options. Piped, it needs `sh -s --` in front of them:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
```

| | |
| :--- | :--- |
| `--prefix DIR` | install somewhere else (default: `~/.local`) |
| `--channel pip` | on Linux, install the Python package even when Flatpak is there |
| `--no-payload` | install the command now, download the editors later |
| `--origin URL` | download from somewhere other than the public server |

It writes to `~/.local/bin` and `~/.local/share` and nowhere else. Open its URL in a browser to read it before running it.

## pipx or uv

Libera Suite is on PyPI as `libera`, and needs Python 3.12 or newer. On macOS:

```sh
uv tool install libera      # or: pipx install libera
libera --payload-install
```

On Linux, the window is drawn by GTK, whose Python bindings come from your distribution and are built for its own Python. An isolated environment cannot see them, so `pipx` needs two flags:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
libera --payload-install
```

Without them, Libera Suite installs cleanly and then opens no window. `uv tool` has no equivalent of `--system-site-packages`, so on Linux use `pipx`. The first run of `libera` names any GTK packages your distribution is missing; it knows apt, dnf, pacman and zypper.

## The Flatpak, by hand

This is what the install script does when Flatpak is present:

```sh
arch=amd64     # or arm64, for your machine
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` holds the current version number, so these lines stay valid from one release to the next. The bundle, about 82 MB, contains the editors. It runs on the GNOME runtime, which `flatpak` downloads from Flathub the first time; a machine without the Flathub remote needs it added first:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## The editors

The Windows installer and the Flatpak include the editors. Every other channel downloads them once, after the application. `libera` offers to the first time it runs; this does it explicitly:

```sh
libera --payload-install
```

It downloads about 120 MB from `cdn.abilian.com` and checks every file against fingerprints that came inside the application, stopping at the first that disagrees. It then builds a font index for your machine, which takes a moment.

To install editors you built yourself, or were given, point it at their directory:

```sh
libera --payload-install --from /path/to/artifacts
```

[Build the payload](../develop/build.md) explains how to build them. `libera --payload-remove` deletes them again; they take about 450 MB on disk.

## Where things live

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, or `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

The editors sit under `payload/<version>/` there. To use editors from somewhere else, a local build for instance, set `LIBERA_PAYLOAD` to their directory; it overrides everything above.

## A launcher entry on Linux

The install script and the Flatpak both put Libera Suite in your applications menu. After any other install, this does the same, for your account alone: an icon, *Open With*, and documents that open on a double-click.

```sh
libera --launcher-install
libera --launcher-remove     # to take it out again
```

## A double-clickable application on macOS

There is no ready-made one yet. From a source checkout you can build one for yourself:

```sh
build/macos-app.sh          # builds build/out/Libera.app
open build/out/Libera.app
```

It opens documents on a double-click and shows the Libera icon in the Dock. It runs the Python it was built with, so it belongs to that checkout: leave it there, and rebuild it if the checkout moves. It is not signed, so the first launch says **"cannot be opened because the developer cannot be verified"**. On macOS 15 and later, the way past it is *System Settings ▸ Privacy & Security ▸ Open Anyway*.
