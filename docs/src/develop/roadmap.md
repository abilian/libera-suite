# Roadmap

This page says what we are doing next and what we have decided against. [What works today](../guide/status.md) is the companion page: it describes the present; this one describes the intent.

Nothing here has a date. The project is small; the things at the top are the things being worked on.

## Now: the first installs

Nothing in the build stands in the way any more. The payload origin is up, both
Flatpak bundles are published, the wheel is on PyPI, and one command installs
it on either platform. People are the missing piece: Libera Suite has not yet
been installed by anyone outside the project, on their own machine, against
their own documents.

That is the next piece of work, and none of it is engineering. The first few
real installs will find things no amount of testing here would, because every
check in this repository runs on a machine that built the thing.

**Installing the payload without a terminal** is what used to be here. Every
channel that can carry the editors now does: the Flatpak has them inside it,
and `curl … | sh` fetches them without the user naming a directory. The one
channel that cannot is PyPI, whose users are at a prompt already. A window that
offers to download still has a place as a fallback, though it gates nothing.

## Next

**Signing and notarisation on macOS.** Everything is already ad-hoc signed, because Apple Silicon refuses to run a binary with no signature at all and the toolchain applies one for free. The absence of a Developer ID therefore does not stop Libera Suite running. It leaves Gatekeeper's quarantine prompt in the way, which on macOS 15 and later right-click ▸ Open no longer dismisses. That is a poor first five minutes.

**A `.flatpakref`.** Both bundles are built, hosted and installable today, and a document converts inside the sandbox on each. The one-URL install is still missing: a `.flatpakref` on a server, and Flathub after that.

**Keyboard shortcuts on Linux.** The menu bar is there and every item on it works. None of them has a key equivalent, because pywebview's GTK menu carries none: giving the bar shortcuts means reaching past it to `Gtk.Application.set_accels_for_action`, and then deciding which keys the page has to stop handling.

**An update path.** Nothing tells a tester that a newer version exists. Saying so in the release notes is enough for a beta. A version check that mentions it once is better. Automatic updates are their own project.

**A redistributable application bundle.** `Libera.app` today is a launcher around the interpreter it was built with. It embeds no Python and no payload, so it runs from your own checkout and is not something you can hand to somebody else.

## Later

**Windows.** Started, and a long way from shipping. The native half builds on a hosted runner: the patch queue applies under MSVC, V8 compiles in about an hour, OpenSSL comes from vcpkg because building 1.1.1w in-tree defeated ten attempts. `x2t` has never been run there. Nothing above it has been tried.

**Tabs.** One window per document today. Windows exist and the Window menu lists them; merging them into one needs real support: `newWindowForTab:`, and moving a document between windows. Turning the tab bar back on does not do it.

**File locking.** Two copies of Libera Suite editing the same document will not notice each other, losing one set of changes.

**Editing PDFs and diagrams.** The payload contains an editor for PDF that nothing routes to yet. Diagrams opens `.vsdx` and shows it; the converter refuses every Visio output format, so there is nothing to save and no blank to start from. Both are upstream capabilities we have not wired up.

**Password-protected documents, digital signatures, mail merge.** Upstream features, none of them reachable today.

**Your name in documents.** Tracked changes and comments are attributed to your account's full name, which you cannot yet change.

**Personal dictionaries.** *Add to dictionary* does not persist, so a word you add comes back next session.

**More fonts, particularly CJK.** The shipped set is 7 MB and renders ordinary documents faithfully; the full set is 248 MB. Where the line goes is an open decision, with CJK the case that most obviously argues for moving it.

**In-application help.** Upstream ships a manual, but it documents ONLYOFFICE and weighs 84 MB in eight languages, so Libera Suite does not carry it. Help comes back when there is documentation of our own to point at; these pages are the substitute.

## Not now

These are outside the current product. Each could arrive one day, in the shape described here. None is being worked on.

**Collaboration, cloud storage, accounts.** Libera Suite edits files on your disk. The engine underneath it is collaborative-first with that switched off. Some form of shared editing may come back, as a mode or as a product of its own. Nothing in the local application waits on it.

**Telemetry, analytics, crash reporting.** There is none today. The beta adds none. Anything of the kind would be opt-in and off until you turn it on. [What leaves your machine](../index.md#what-leaves-your-machine) would list it beside everything else the application does on the network.

**Changing the document engine.** Not something we do today. The patch queue is 34 patches across three repositories. Twenty-one make it build on macOS and six on Windows. Five more are configuration, branding and build fixes, and one fixes an upstream UI bug. **None touches the editing engine** (see [the patch queue](patches.md)). That is what keeps a pin bump a rebase of build configuration. It is a discipline, so if we ever do need the engine to behave differently, the change is carried the same way: one reviewable patch, offered upstream first.

## How to influence this

The most useful thing you can send is a document that renders wrongly, attached. The layout engine is upstream's and mature, so where output is wrong it is far more likely to be our packaging than the engine: a missing font, a missing resource. Those are quick to fix and invisible to us until somebody sends one. [Feedback](../feedback.md) says where to send it.
