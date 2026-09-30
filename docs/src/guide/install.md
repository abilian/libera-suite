# Install

Libera Suite runs on **Windows 10 and 11 (x64)**, **Linux (x86_64 and arm64)** and **macOS (Apple Silicon)**.

## Which one am I

| your machine | the line to run | what you get |
| :--- | :--- | :--- |
| **Linux, with `flatpak`** | `curl -fsSL https://cdn.abilian.com/libera/install.sh \| sh` | everything in one download, plus a launcher icon |
| **Linux, without `flatpak`** | the same line | the `libera` command, then a few system packages it names for you |
| **macOS** | the same line | the `libera` command, run from a terminal |
| **Windows** | [download the installer](#on-windows), or in PowerShell: `irm https://cdn.abilian.com/libera/install.ps1 \| iex` | an application in the Start menu, on the desktop, and in Explorer's *Open with* |

On Linux and macOS, one command covers all three cases: it works out which channel suits the machine and takes that one. Windows has its own, below.

**On macOS you get a command and not an icon.** A double-clickable `Libera.app` can be built from a source checkout. It is not yet something we can hand you, being unsigned and tied to the interpreter it was built against. A redistributable bundle is on [the roadmap](../develop/roadmap.md). Until then, macOS means a terminal.

### Before you start

| | |
| :--- | :--- |
| **Linux** | Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9, or anything newer. On something older, take [the Flatpak](#or-on-linux-the-flatpak): it brings its own libraries and does not care what the rest of the machine has. |
| **Python 3.12 or newer** | For every channel except the Flatpak. macOS ships 3.9, so `brew install python@3.13` first; on Ubuntu 22.04, `python3` is 3.10, so install `python3.12`. The installer checks this and says so before doing anything. |
| **About 120 MB** | The editors are a separate download from the application. More on that below. |
| **No root** | Nothing here asks for a password. |

## The quickest way

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

On Linux it installs the Flatpak bundle when `flatpak` is present, which
brings its own GTK and WebKit and skips every question below. Without flatpak,
and on macOS, it builds a virtualenv against a Python on your machine instead.

It writes to `~/.local/bin` and `~/.local/share`, and nowhere else. Open the
URL in a browser to read it first.

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

## On Windows

Download the installer and double-click it:

<https://cdn.abilian.com/libera/bundles/Libera-Suite-Setup.exe>

It installs for your account only, without asking for an administrator
password, and puts Libera Suite in the Start menu and on the desktop. The
editors and fonts are included, so there is nothing to fetch afterwards.

Or, the same thing in one line of PowerShell:

```powershell
irm https://cdn.abilian.com/libera/install.ps1 | iex
```

It downloads the latest installer, checks it against its published SHA-256,
installs it without questions, and checks that Libera Suite runs. Open the
URL in a browser to read it first. Run it again to upgrade.

Two things Windows will say the first time:

- **"Windows protected your PC"**, on the downloaded installer. The installer
  is not yet signed with a code-signing certificate, which is what SmartScreen
  looks for. Choose *More info*, then *Run anyway*. The one-line install is not
  affected.
- **"How do you want to open this file?"**, the first time you double-click a
  document when another program, such as Word, can also open it. Windows asks
  you rather than letting an installer choose. Pick Libera Suite and tick
  *Always*. To change it later: *Settings › Apps › Default apps › Libera Suite*.

To remove it: *Settings › Apps › Installed apps › Libera Suite › Uninstall*.
Your documents, and anything unsaved, are left where they are.

## Check it worked

```sh
libera --diagnose
```

That prints one screen, and it is also the right thing to paste into a bug
report. A working install looks like this:

```
libera    0.2.1
python     3.12.13
platform   macOS-14.8.4-arm64-arm-64bit  arm64
window     ok
payload    0.2  (installed)
  at       /Users/you/Library/Application Support/Libera Suite/payload/0.2
  platform macos-arm64  fonts: core
  built    2026-09-24T19:23:03Z
  x2t      present
  editors  documenteditor, presentationeditor, spreadsheeteditor, visioeditor
state      /Users/you/Library/Application Support/Libera Suite
```

Two lines are the ones to read. **`window ok`** means a window can be opened;
on Linux, `NOT AVAILABLE` means the GTK packages are missing, and running
`libera` prints the exact command for your distribution. **`payload`** names
the editors and where they came from; `MISSING` means step 2 below has not
happened.

Then open something, or run `libera` on its own for the start window:

```sh
libera ~/Documents/note.docx
libera
```

![The start window, with a New tile for each of Document, Spreadsheet and Presentation, an Open button, and a Recent list of three documents.](../assets/start.png)

[Work with documents](documents.md) is the next page: opening, saving,
exporting and printing.

---

The rest of this page is what the install script does, for anyone who would
rather do it by hand or needs a piece of it.

## 1. The application

On Linux, the command needs two flags:

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

This gives you the `libera` command, which is small and cannot edit anything until it has the editors.

### Or, on Linux, the Flatpak

The bundle brings GTK, WebKit and their Python bindings from the GNOME runtime, so none of the above applies. There are no system packages to install and nothing to get wrong:

```sh
arch=amd64     # or arm64, for your machine
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` is one line of text naming the current version, so those commands do not go stale.

**Skip step 2.** The editors are inside the bundle, so there is nothing to fetch, nothing to verify and nothing that needs the network. The download is about 82 MB, and it installs offline apart from the GNOME runtime: the runtime is not inside the bundle, so `flatpak` fetches `org.gnome.Platform` from Flathub the first time. A machine with no flathub remote needs one adding first:

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
On macOS, Gatekeeper has nothing to object to, because Homebrew builds in its
own prefix rather than downloading a finished application. Step 2 still applies.

## 2. The editors

**Not needed if you installed the Flatpak**, which includes its own.

The second download, which the application calls the *payload*, holds the editors, the document engine and the fonts. Ask for it explicitly:

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

The application and the editors are versioned separately, and the application
checks that the editors it finds are the ones it expects. This is why
installing takes two steps: a fix to the application does not move 120 MB.

## Where things live

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, or `~/.local/share/libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |

The editors sit under `payload/<version>/` there; nothing else on your system is touched.

To use a payload from somewhere else, a local build say, set `LIBERA_PAYLOAD` to its directory. It overrides everything above.

## A double-clickable application

On Linux, one command gives you an icon, *Open With*, and documents that open
on a double-click:

```sh
libera --launcher-install
```

It writes a desktop entry and the icon under `$XDG_DATA_HOME`, for your account alone, and tells the desktop about the formats Libera Suite reads. The Flatpak ships both already, so the command declines there and says so.

On macOS there is no shippable equivalent yet. From a source checkout:

```sh
build/macos-app.sh          # builds build/out/Libera.app
open build/out/Libera.app
```

That bundle opens a document on a double-click and shows the Libera mark in
the Dock. It is a launcher around the interpreter it was built against, so it
belongs to your checkout: `/Applications` is not its home, and moving the
checkout means rebuilding it. It is also unsigned and unnotarised, so the
first launch brings **"cannot be opened because the developer cannot be
verified"**. The way past that on macOS 15 and later is System Settings ▸
Privacy & Security ▸ *Open Anyway*; right-click ▸ Open no longer works.

## Remove it

Take these in order. Each is independent, so you can stop after the first.

```sh
libera --payload-remove     # the editors, ~450 MB on disk
libera --launcher-remove    # on Linux, the desktop entry and its icon
```

Remove the application itself with whichever line matches how you installed it:

```sh
flatpak uninstall eu.liberasuite.Libera   # the Flatpak
pipx uninstall libera                     # pipx
uv tool uninstall libera                  # uv tool
brew uninstall abilian/tap/libera         # Homebrew
rm -rf ~/.local/bin/libera ~/.local/share/libera   # the install script
```

Any of those leaves your settings and any unsaved sessions behind,
under the directory in *Where things live*. Delete that directory to remove
every trace. On Linux the install script's virtualenv is inside it, so the last
line above already does both.

## If it did not work

`libera --diagnose` first, then [tell us](../feedback.md) with that output
pasted in. [What works today](status.md) lists the problems we already know
about, so an evening spent reporting one of those is an evening wasted.
