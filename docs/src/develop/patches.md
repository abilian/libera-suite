# The patch queue

Libera Suite does not fork upstream. It pins an upstream revision and applies a series of patches to it, each one a commit with a message explaining what it is for.

```
build/upstream/pins.toml            the upstream revisions, by hash
build/upstream/patches/core/
build/upstream/patches/web-apps/
build/upstream/patches/sdkjs/
```

The pins follow Euro-Office's own desktop releases: the revisions its `DesktopEditors` repository names for a release are the ones we build.

`build/engine/build.sh fetch` resets each repository to its pinned hash, cleans it, and applies the series with `git am`, which does not fuzz. A patch that has stopped applying is news: investigate it.

## Why a queue

The queue answers "what did Libera Suite change?" in a form anyone can check. On a long-lived branch that question becomes a diff against a moving target; a pin bump becomes one large merge. The queue gives a series of small rebases that each say what they were for.

It also makes the AGPL obligation concrete: the corresponding source for a release is a commit hash plus a patch series that provably applies to it.

## What is in it

**`core`: the build, the converter, and OpenDocument.** Patches keep their numbers when others leave the queue, so the numbering has gaps.

- *macOS.* Upstream ported the build from qmake to CMake and the port dropped the Mac branches. We put them back in a series of about twenty patches; Euro-Office has since built macOS itself, and the queue keeps only what its build still lacks: `memalign`, which macOS does not have, for openjpeg (`0018`), and two V8 build options of our own (`0009`, `0010`).
- *Windows.* Boost's engine built with a named toolset (`0022`), an external OpenSSL from vcpkg (`0024`), a namespace cryptopp no longer has (`0025`), and one C runtime for every DLL, V8 included, because core's libraries hand `FILE*` handles to one another (`0028`).
- *Elsewhere in the build.* Third-party builders that stream their output (`0023`), doctrenderer against an OpenSSL without MD2 (`0026`), and `hypotf` bound to its old glibc version so the Linux core loads on RHEL 9 (`0032`).
- *The converter.* A large CSV read whole (`0029`), characters outside the BMP (`0030`), no empty row after a UTF-8 CSV (`0031`), and the last section of an RTF written (`0033`).
- *OpenDocument* (`0101` onwards). Fixes to reading and writing `.odt`, `.ods` and `.odp`, each found against LibreOffice's own test documents.

**`web-apps`: 9 patches, and `sdkjs`: 4.** Four are build fixes. Theme tokens were not substituted when deploying HTML. Two cap how many tasks a build phase runs at once. The fourth runs `npm` and webpack through `node`, since on Windows both exist only as `.cmd` files that Node will not spawn without a shell. One is a rendering fix, for unsized SVG icons in the language picker rendering at 300×150, the CSS default for a replaced element with no intrinsic size. Three are configuration changes that are ours alone. Two are branding. One drops upstream's favicon. The other keeps *About* reachable in the desktop build, where upstream hides it: that dialog shows the licence and the attribution.

The two other `sdkjs` patches choose fonts, and come from ElixirOffice's fork of `sdkjs` (AGPL, like the components), each naming the commit it was taken from. `0002` substitutes a missing font the way Word does: a metric-compatible font first (Carlito for Calibri, Caladea for Cambria, Liberation for Arial, Times New Roman and Courier New), and Calibri, hence Carlito, for a font Word would not know either. `0003` draws the characters of a missing Symbol, Wingdings or Webdings as the Unicode symbols they stand for, where they came out as letters.

`0004` is ours: Markdown keeps its headings through a save. Markdown read into a document gives each heading a style derived from a heading style, which the HTML writer, on the way back to Markdown, did not recognise, so `# Title` came back as `**Title**`. It now writes a heading by its outline level, and leaves out a bold that covers the whole heading.

## One idea per patch

Each patch does one thing and says why. When a patch needs to change, the queue is regenerated from the build tree with `git format-patch`, and is never edited by hand.

Two traps have each cost real time:

**`git am` strips carriage returns.** It parses a patch as mail, so `mailinfo` removes the trailing CR from every line. Any patch touching upstream's CRLF files is then rejected, with nothing to suggest that line endings were the cause. The queue is applied with `--keep-cr`.

**Do not `git add -A` in the build tree.** The payload build stages generated assets into it, so a blanket add sweeps them into your patch.

## Upstreaming

Most of these are upstream's own bugs and should go back.

The `web-apps` fixes are small and self-contained, so they can go as soon as the mirrors exist. The `core` patches are the valuable contribution and have to wait: two of them change platform defines globally, so the Linux build has to confirm they are inert there before we offer a series that could break somebody else's build.

Three patches never leave our tree. `0002` turns off upstream's feature tips and removes their helpdesk links; `0004` retitles the wrapper page; `0008` turns macros off, until there is a macro language worth offering (see [the roadmap](roadmap.md)). They are configuration for a different product.
