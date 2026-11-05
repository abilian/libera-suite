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
| `--origin URL` | download from somewhere other than the public server |

It writes to `~/.local/bin` and `~/.local/share` and nowhere else. Open its URL in a browser to read it before running it.

## pipx or uv

Libera Suite is on PyPI as `libera`, and needs Python 3.12 or newer. Its [components](#the-editors) come with it. On macOS and Windows:

```sh
uv tool install libera      # or: pipx install libera
```

To try it without installing it, `uvx libera` runs it from a cache.

On Linux, the window is drawn by GTK, whose Python bindings come from your distribution and are built for its own Python. An isolated environment cannot see them, so `pipx` needs two flags:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
```

Without them, Libera Suite installs cleanly and then opens no window. `uv tool` has no equivalent of `--system-site-packages`, so on Linux use `pipx`. The first run of `libera` names any GTK packages your distribution is missing; it knows apt, dnf, pacman and zypper.

## The Flatpak, by hand

This is what the install script does when Flatpak is present:

```sh
arch=amd64     # or arm64, for your machine
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
# on arm64: ver=0.4.1, the last version built for it
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` holds the current version number, so these lines stay valid from one release to the next. The bundle, about 70 MB, contains the components. It runs on the GNOME runtime, which `flatpak` downloads from Flathub the first time; a machine without the Flathub remote needs it added first:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

From version 0.7.0 each bundle has a signature beside it, so you can check that it is ours before you install it. In the same folder, with `ver` and `arch` set as above:

```sh
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak.asc"
curl -fsSL https://keys.openpgp.org/vks/v1/by-fingerprint/E1B31B9935BEDA0C53D21A1DD35A9ACA9BE0C732 | gpg --import
gpg --verify "libera-$ver-$arch.flatpak.asc" "libera-$ver-$arch.flatpak"
```

GnuPG must say `Good signature from "Libera Suite release signing <releases@liberasuite.eu>"`, and the primary key fingerprint it prints must be `E1B3 1B99 35BE DA0C 53D2 1A1D D35A 9ACA 9BE0 C732`. Its warning that the key is not certified only means that you have not told GnuPG to trust this key yourself. The install script does not make this check.

## The components {#the-editors}

Every channel installs the components with the application. The Windows installer and the Flatpak contain them. With pip, pipx or uv they are two Python packages that `libera` requires: `libera-core`, the document engine, built for each platform, and `libera-web`, the editing components and the fonts. Together they are about 90 MB to download. The first run then builds a font index for your machine, which takes a moment.

PyPI has `libera-core` for Windows x64, Linux x86_64 and macOS on Apple Silicon. On any other machine, pip builds it from source, which takes most of an hour and needs the tools [Build the components](../develop/build.md) lists.

Versions before 0.7 downloaded their components separately, into the folders below. `libera --payload-remove` deletes what they left there.

## Where things live

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, or `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

That is where Libera Suite keeps what it needs between runs, such as the Recent list and unsaved sessions. The components are not there: they are installed with the application, and `libera --payload-status` says where. To use components from somewhere else, a local build for instance, set `LIBERA_PAYLOAD` to their directory; it overrides the installed ones.

## A launcher entry on Linux

The install script and the Flatpak both put Libera Suite in your applications menu. After any other install, this does the same, for your account alone: an icon, *Open With*, and documents that open on a double-click.

```sh
libera --launcher-install
libera --launcher-remove     # to take it out again
```

## A double-clickable application on macOS

The install script writes one, `Libera.app`, into the Applications folder of your home folder. After any other install, such as Homebrew, `pipx` or `uv tool`, this does the same:

```sh
libera --launcher-install
libera --launcher-remove     # to take it out again
```

It opens documents on a double-click and shows the Libera icon in the Dock. It is a small launcher for the Python of the install that wrote it, so after uninstalling that, or moving it to another Python, run `libera --launcher-install` again.

From a source checkout you can build one for that checkout:

```sh
build/macos/macos-app.sh          # builds build/out/Libera.app
open build/out/Libera.app
```

It runs the Python of the checkout, so it belongs there: leave it there, and rebuild it if the checkout moves. It is not signed, so the first launch says **"cannot be opened because the developer cannot be verified"**. On macOS 15 and later, the way past it is *System Settings ▸ Privacy & Security ▸ Open Anyway*.
