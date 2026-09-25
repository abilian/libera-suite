# The patch queue

Libera Suite does not fork upstream. It pins an upstream revision and applies a series of patches to it, each one a commit with a message explaining what it is for.

```
build/pins.toml            the upstream revisions, by hash
build/patches/core/        27 patches
build/patches/web-apps/     6 patches
build/patches/sdkjs/        1 patch
```

`build/build.sh fetch` resets each repository to its pinned hash, cleans it, and applies the series with `git am`, which does not fuzz. A patch that has stopped applying is news: investigate it.

## Why a queue

The queue answers "what did Libera Suite change?" in a form anyone can check. On a long-lived branch that question becomes a diff against a moving target; a pin bump becomes one large merge. The queue gives a series of small rebases that each say what they were for.

It also makes the AGPL obligation concrete: the corresponding source for a release is a commit hash plus a patch series that provably applies to it.

## What is in it

**`core`: 27 patches, 21 macOS and 6 Windows.** Upstream ported the build from qmake to CMake and the port dropped the Mac branches wholesale; the root `.pro` files are gone. The macOS series puts them back: boost, ICU, OpenSSL and V8 on macOS, the Cocoa file transporter, Core Text font enumeration, Mach-O link options and rpath, plus a handful of platform defines. The Windows series (`0022`–`0027`) is smaller and newer: boost through `build.bat`, an external OpenSSL from vcpkg, a namespace cryptopp no longer has, and two guards around code that MSVC rejects.

**`web-apps`: 6 patches, and `sdkjs`: 1.** Three are build fixes. Theme tokens were not substituted when deploying HTML; the other two cap how many tasks a build phase runs at once. One is a rendering fix, for unsized SVG icons in the language picker rendering at 300×150, the CSS default for a replaced element with no intrinsic size. Two are configuration changes that are ours alone. One drops upstream's favicon.

## One idea per patch

Each patch does one thing and says why. When a patch needs to change, the queue is regenerated from the build tree with `git format-patch`, and is never edited by hand.

Two traps have each cost real time:

**`git am` strips carriage returns.** It parses a patch as mail, so `mailinfo` removes the trailing CR from every line. Any patch touching upstream's CRLF files is then rejected, with nothing to suggest that line endings were the cause. The queue is applied with `--keep-cr`.

**Do not `git add -A` in the build tree.** The payload build stages generated assets into it, so a blanket add sweeps them into your patch.

## Upstreaming

Most of these are upstream's own bugs and should go back.

The `web-apps` fixes are small and self-contained, so they can go as soon as the mirrors exist. The `core` patches are the valuable contribution and have to wait: two of them change platform defines globally, so the Linux build has to confirm they are inert there before we offer a series that could break somebody else's build.

Two patches never leave our tree. `0002` turns off upstream's feature tips and removes their helpdesk links; `0004` retitles the wrapper page. They are configuration for a different product.
