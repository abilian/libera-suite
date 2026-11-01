# The patch queue

Libera Suite does not fork upstream. It pins an upstream revision and applies a series of patches to it, each one a commit with a message explaining what it is for.

```
build/upstream/pins.toml            the upstream revisions, by hash
build/upstream/patches/core/
build/upstream/patches/web-apps/
build/upstream/patches/sdkjs/
build/upstream/patches/libxml2/
```

The pins follow Euro-Office's own desktop releases: the revisions its `DesktopEditors` repository names for a release are the ones we build. One pin is not Euro-Office's: libxml2, the XML parser the converter reads every document with. Core keeps a copy of it, about release 2.9.4, and a 6 KB document of nested entities took that copy to 3.9 GB of memory; we build core against libxml2 2.9.14 instead, from its own repository, whose address is under `[urls]` in `pins.toml`.

`build/engine/build.sh fetch` resets each repository to its pinned hash, cleans it, and applies the series with `git am`, which does not fuzz. A patch that has stopped applying is news: investigate it.

## Why a queue

The queue answers "what did Libera Suite change?" in a form anyone can check. On a long-lived branch that question becomes a diff against a moving target; a pin bump becomes one large merge. The queue gives a series of small rebases that each say what they were for.

It also makes the AGPL obligation concrete: the corresponding source for a release is a commit hash plus a patch series that provably applies to it.

## What is in it

**`core`: the build, the converter, and OpenDocument.** Patches keep their numbers when others leave the queue, so the numbering has gaps.

- *macOS.* Upstream ported the build from qmake to CMake and the port dropped the Mac branches. We put them back in a series of about twenty patches; Euro-Office has since built macOS itself, and the queue keeps only what its build still lacks: `memalign`, which macOS does not have, for openjpeg (`0018`), and two V8 build options of our own (`0009`, `0010`).
- *Windows.* Boost's engine built with a named toolset (`0022`), an external OpenSSL from vcpkg (`0024`), a namespace cryptopp no longer has (`0025`), and one C runtime for every DLL, V8 included, because core's libraries hand `FILE*` handles to one another (`0028`).
- *Elsewhere in the build.* Third-party builders that stream their output (`0023`), doctrenderer against an OpenSSL without MD2 (`0026`), `hypotf` bound to its old glibc version so the Linux core loads on RHEL 9 (`0032`), and libxml2 taken from the pinned checkout rather than core's own copy (`0172`).
- *The converter.* A large CSV read whole (`0029`), characters outside the BMP (`0030`), no empty row after a UTF-8 CSV (`0031`), the last section of an RTF written (`0033`), and the code cache of the editors' scripts kept in a folder the host names, not written beside the scripts (`0034`).
- *OpenDocument* (`0101` onwards). Fixes to reading and writing `.odt`, `.ods` and `.odp`, each found against LibreOffice's own test documents.
- *A hostile document* (`0173` onwards). A picture a document links to is read from a web address only: one linked to a path on the user's disk was copied into everything written from the document (`0175`, ours). An SVG's `<image>` draws only a picture the SVG carries, not a file it names (`0174`). An `.xls` ActiveX control's data is bounds-checked without a sum that can overflow (`0173`). The last two are from ElixirOffice's fork of `core`.
- *PDF* (`0176` onwards). A form saved as an incremental update leaves its XFA out, so that a reader which shows the XFA, Acrobat, shows the fields as filled rather than the form as it was (`0176`, ours). A saved PDF keeps its Creator, which the writer replaced with the Producer, or with its own name when the Creator was a hex string (`0177`, after ElixirOffice's `0011-pdf-preserve-creator`). A page moved after another keeps the size and rotation it inherits from its own parents, where it took those of the page that had been at its position (`0178`, ElixirOffice's). A value typed into a form field is written on the field, not on the first ancestor that already had one, which every field under it inherits: a LiveCycle form, a French Cerfa for one, keeps an empty value at its root, and one name typed became the value of all its fields (`0179`, ours).

**`web-apps`: 12 patches, and `sdkjs`: 5.** Five are build fixes. Theme tokens were not substituted when deploying HTML. Two cap how many tasks a build phase runs at once. The fourth runs `npm` and webpack through `node`, since on Windows both exist only as `.cmd` files that Node will not spawn without a shell. The fifth makes the SVG sprites before the tasks that read them: the sprites are written into the source tree, and a task running beside them now and then read one half written and failed. One is a rendering fix, for unsized SVG icons in the language picker rendering at 300×150, the CSS default for a replaced element with no intrinsic size. Three are configuration changes that are ours alone. Two are branding. One drops upstream's favicon. The other keeps *About* reachable in the desktop build, where upstream hides it: that dialog shows the licence and the attribution.

Two are security fixes, from ElixirOffice's fork of `web-apps`, for places where the editor wrote a document's own text into its page as HTML. A document can carry markup there, and the page holds the bridge, so the markup ran beside it. The popup that describes a tracked change inserted the font of a formatting change and a paragraph's new style as the document names them; it ran as soon as the cursor entered the change. The Formula Wizard wrote each argument's value and the results the same way, so a cell holding markup ran it when the wizard was opened on a formula reading that cell. Both now escape what they show. `tests/c_e2e/host/test_hostile_document.py` holds them, beside the places that already showed such text as text: a change's author, a comment, a link's tooltip, a sheet's name. Neither fix is upstream yet.

The two other `sdkjs` patches choose fonts, and come from ElixirOffice's fork of `sdkjs` (AGPL, like the components), each naming the commit it was taken from. `0002` substitutes a missing font the way Word does: a metric-compatible font first (Carlito for Calibri, Caladea for Cambria, Liberation for Arial, Times New Roman and Courier New), and Calibri, hence Carlito, for a font Word would not know either. `0003` draws the characters of a missing Symbol, Wingdings or Webdings as the Unicode symbols they stand for, where they came out as letters.

`0004` is ours: Markdown keeps its headings through a save. Markdown read into a document gives each heading a style derived from a heading style, which the HTML writer, on the way back to Markdown, did not recognise, so `# Title` came back as `**Title**`. It now writes a heading by its outline level, and leaves out a bold that covers the whole heading.

`0005` is ours too, and lets the PDF editor open a PDF at all. `CPDFDoc`'s constructor assigned `widgets`, `annots` and `drawings`, which its prototype defines as getters with no setters, and the bundle's strict mode refuses that: "Cannot set property widgets of #<CPDFDoc> which has only a getter". The patch drops the three assignments.

**`libxml2`: 2 patches.** Core builds libxml2 from a list of its sources, without libxml2's own build system, so the first writes the version header that system would have written. The second carries over the one change core's copy makes that matters to us: with `XML_ERROR_DISABLE_MODE`, which core's build defines, libxml2 writes no parser messages to the converter's error output.

## One idea per patch

Each patch does one thing and says why. When a patch needs to change, the queue is regenerated from the build tree with `git format-patch`, and is never edited by hand.

Two traps have each cost real time:

**`git am` strips carriage returns.** It parses a patch as mail, so `mailinfo` removes the trailing CR from every line. Any patch touching upstream's CRLF files is then rejected, with nothing to suggest that line endings were the cause. The queue is applied with `--keep-cr`.

**Do not `git add -A` in the build tree.** The payload build stages generated assets into it, so a blanket add sweeps them into your patch.

## Upstreaming

Most of these are upstream's own bugs and should go back.

The `web-apps` fixes are small and self-contained, so they can go as soon as the mirrors exist. The `core` patches are the valuable contribution and have to wait: two of them change platform defines globally, so the Linux build has to confirm they are inert there before we offer a series that could break somebody else's build.

Three patches never leave our tree. `0002` turns off upstream's feature tips and removes their helpdesk links; `0004` retitles the wrapper page; `0008` turns macros off, until there is a macro language worth offering (see [the roadmap](roadmap.md)). They are configuration for a different product.
