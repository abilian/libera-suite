# Roadmap

This page says what we are doing next and what we have decided against. [What works today](../main/status.md) is the companion page: it describes the present; this one describes the intent.

Nothing here has a date. The order is the commitment.

## The goal, as a test

Libera Suite is meant to replace Microsoft Office. We read that as one test: **an organisation of a few dozen people, on Windows and macOS, uninstalls Office and does not reinstall it within a month.** Each release removes one reason it would. These are the reasons, roughly in the order such an organisation meets them:

1. It cannot be installed without a security warning, or by an administrator onto many machines.
2. It does not speak the users' language.
3. A document from outside looks wrong.
4. Something done daily is missing: tabs, a password-protected file, a signature, a PDF to fill in, a Visio diagram to edit.
5. It is not clear who maintains it, or for how long.

## Now: 0.5, the beta in other people's hands

The beta has been public since October 2026. 0.5 is about what its testers meet first.

**The interface in your language.** The editor already has its own translations; the menus, the start window and the dialogs do not. 0.5 runs the whole application in the system's language, starting with French, German, Italian and Spanish, the languages this site has. A new document follows it too: today File ▸ New gives a US Letter page in American English, whatever the system says.

**The fonts installed on your machine.** 0.5 makes the fonts installed on the machine visible to the editor and to the converter alike, so the screen and the PDF agree. Until then the editor saw only the fonts Libera Suite ships, and a document set in a font you had installed got a substitute.

**A save that loses the text is a failed save.** Every format Save As offers is now checked by reading the document's text back. The application itself will refuse a save whose result has lost the text, and keep the document recoverable.

**Libera Suite sends your documents nowhere on its own, by construction.** Today it is a promise about our code. 0.5 makes the editor's page unable to send anything off the machine. The one thing it still fetches is a picture a document links to by address rather than carrying, as every office suite does: that is the document's own reference, and only the picture comes back. The converter is measured the same way.

**Following Euro-Office's desktop release.** Euro-Office now publishes desktop builds of its own. Our editors move to the revisions behind them, so a bug fixed there is fixed here.

**Old editor versions are removed.** Each update leaves the previous version's editors on disk, about 400 MB each. 0.5 removes the ones no copy of Libera Suite still uses.

**Installs without a warning.** Three things wait on accounts and keys, and each ships in a 0.5.x as soon as it is ready: signing and notarisation on macOS, where Gatekeeper's prompt is a poor first five minutes; a `.flatpakref`, then Flathub; and code signing on Windows, so SmartScreen stops warning about the installer.

## Next: parity with Euro-Office Desktop

Euro-Office publishes a desktop application of its own, built on the same editors as Libera Suite. Someone comparing the two should find nothing in it that is missing here, macros apart (see below). Every feature on this list exists upstream already, in the editors we ship or beside them, so the work is wiring each one to the host and testing it, not writing it. This is the order we do them in.

**Tabs.** One window per document today. Several documents in one window needs real support: `newWindowForTab:` on macOS, its equivalent on Linux and Windows, and moving a document from one window to another.

**The interface in every language the editors speak.** The editors are translated into 46 languages. 0.5 translates our own part (the menus, the start window, the dialogs) into four. The rest follow, each once a native speaker has read it: our part is small beside the editors'.

**PDF: editing and forms.** Upstream has a PDF editor and a form creator, which the payload leaves out because nothing routes to them yet. Both come in: annotating and editing a PDF, filling in a form and saving it, and creating one. A viewer alone would add little to the system's own, so PDF ships when saving holds up.

**Password-protected documents and digital signatures.** Upstream has both, and neither is reachable today. Opening and saving a protected document, then signing one and checking a signature.

**Plugins, including the AI assistant.** Upstream's plugin system, and the plugins it carries, AI assistant included. The AI assistant is off until it is configured, and it talks only to a provider the user chooses, which may run on their own machine. [What leaves your machine](../index.md#what-leaves-your-machine) will say so beside everything else.

**Documents on a Nextcloud, ownCloud or Seafile server.** As in Euro-Office Desktop, a window on the server's own editors: the documents stay on that server, and editing with other people is that server's work. It is off until the user adds a server, and a local document's window never reaches the network either way.

**Signed installers**, on macOS and Windows, are already in 0.5.x, above.

## Alongside

**The host becomes a runtime.** The package splits in two: a host that runs apps, and the editors as one app among others. Nothing changes for a user. It comes when a second app does, or earlier if the boundary between the Apache-licensed host and the AGPL editors has to be shown in the code.

**Fidelity, measured.** A document from outside that looks wrong is the third reason on the list. The editor is mature, so a wrong layout is more often our packaging (a font, a resource) than the engine. Only a measurement finds those: a corpus of test documents, reference PDFs exported from Word, a score per page, and a harness that gives the same pixels twice. The score then gates releases, and every document a user reports goes into the corpus.

## Later, towards 1.0

One feature at a time, each measured before it is promised. Most exist in the editor already and are not wired up.

**Editing diagrams.** Diagrams opens `.vsdx` and shows it. The converter writes no Visio format, so this needs converter work first. Euro-Office Desktop does not edit diagrams either.

**Mail merge.** An upstream feature, not reachable today.

**Macros, in VBA, JavaScript and Python.** Macros are off today. The editor's own are JavaScript against its API, and run none of the VBA that an organisation's workbooks and documents carry, which is what someone coming from Microsoft Office means by macros. They come back in three languages: Excel's VBA, so the macros already in those files run; JavaScript, the editor's own; and Python. Euro-Office Desktop has the JavaScript macros, so until then this is the one feature it has that Libera Suite leaves out.

**In-application help.** Upstream's manual documents ONLYOFFICE and weighs 84 MB, so Libera Suite does not ship it. Help comes back when there is documentation of our own to point at; these pages are the substitute.

**More fonts, particularly CJK.** The shipped set is 7 MB and renders ordinary documents faithfully; the full set is 248 MB. Where the line goes is an open decision, and the fidelity corpus will say how many documents fall back.

**Windows on ARM.** It runs the x64 build under emulation today.

## 1.0

1.0 means the test above passes for one real organisation. On top of the features: signed installers on Windows and macOS, a deployment an administrator can script (an MSI or equivalent, a `pkg`, a system Flatpak), a published support window for each release, and a security contact. The fifth reason is answered by Abilian's commitment, written down where an organisation's procurement can find it.

## Not now

These are outside the current product. Each could arrive one day, in the shape described here. None is being worked on.

**A collaboration server of our own, and accounts.** Libera Suite edits files on your disk, and opens the ones on a server you already use (see above). Running such a server is a separate product, which may reuse the host. Nothing in the local application waits on it.

**Telemetry, analytics, crash reporting.** There is none. Anything of the kind would be opt-in and off until you turn it on. [What leaves your machine](../index.md#what-leaves-your-machine) would list it beside everything else the application does on the network.

**Changing the document engine.** The patch queue makes upstream build on macOS and Windows, brands it, and fixes the converter, mostly for OpenDocument files. **None of it touches the editing engine** (see [the patch queue](patches.md)), which is what keeps following upstream affordable. If we ever need the engine to behave differently, the change goes in the same way: one reviewable patch, offered upstream first.

## How to influence this

The most useful thing you can send is a document that renders wrongly, attached. The layout engine is upstream's and mature, so where output is wrong it is far more likely to be our packaging than the engine: a missing font, a missing resource. Those are quick to fix and invisible to us until somebody sends one. [Feedback](../feedback.md) says where to send it.
