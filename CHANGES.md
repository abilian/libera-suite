# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two versions move here and they move independently. The **application** is this package, `libera`. The **editor payload** is the Euro-Office build it fetches on first use, versioned separately so that a fix to the host does not force a 120 MB re-download. `libera --version` prints both.

## [0.3.3] - 2026-10-02

### Changed

- **Save As starts in the document's own folder.** It started wherever the last save went, Downloads more often than not. A document still starts there when it has never been saved, or when its folder has gone, such as on a drive that is no longer connected.
- **Libera Suite's questions read the same on every platform.** On Linux and Windows, the offer to recover unsaved changes answered "Recover" or "Without". The offer to reload a stuck editor gave no reason. Both now say what macOS always said. The first offers Recover or Open Saved Version; the second names the error that stopped the editor.

### Fixed

- **Other web pages can no longer reach your documents.** The editor talks to Libera Suite over a local connection, which any page open in your browser could reach too. A page from another site could erase the unsaved edits of an open document, have it saved, or copy a file from your computer into the document. A site that pointed its own name at your machine could also read what came back, the open document included. Libera Suite now answers only its own pages.
- **Saving a new document asks where.** A document made with File ▸ New was saved without asking into Libera Suite's own session folder. You would not think to look there. Recent did not list it either. Its first save now asks where, as Save As does. Closing its window with Save leaves the window open and says to use Save As.
- **Diagrams open.** Opening any `.vsdx` failed while adding it to the Recent list, which had no entry type for a diagram.
- **A crash while you type no longer loses your unsaved edits.** Libera Suite keeps every edit since the document was opened, so they can be recovered after a crash. That record was rewritten whole with each change, so a crash or a full disk at the wrong moment left it empty. Each change is now added to the end of it.
- **On macOS, Save As offers the formats of the window you are in.** It offered the first window's. Save As in a spreadsheet opened after a Words document listed Word formats, then wrote the spreadsheet under a `.docx` name.
- **A Save As that fails leaves the document where it was.** The window took the new name before the file was written, so after a failed Save As the next Save went to the name that had failed instead of to the open document.
- **On macOS, a recovery prompt that fails no longer discards the edits it was offering back.** A prompt that could not appear counted as choosing Open Saved Version.
- **A document that cannot be opened says so.** File ▸ Open, Open Recent and a Finder double-click gave no message at all for a document the converter could not read. A second `libera FILE` on such a document also started a second copy of the application.
- **Print says when nothing could show the PDF.** It used to do nothing, silently. On Linux, Print and Open File Location could also hold the editor's request for as long as the PDF viewer or file manager stayed open; they now wait five seconds at most.
- **An edit Libera Suite failed to record is reported**, with an offer to reload the window. The editor went on showing an edit that no save would have written.
- **Opening a document that is already open no longer takes the other window's edits.** If the first window had unsaved changes, Libera Suite offered to recover them as if after a crash, and recovering moved them out from under that window, which then could not record another edit. The second window now opens the file as it is on disk.
- **A reload that cannot keep your edits no longer happens.** Reload converts the edits into the document and reopens it. When reopening failed, the document and its edits were already gone and the window reloaded empty. A failed conversion now leaves everything as it was. Reload then says it could not reload and that Save will keep the edits.
- **"Open Saved Version" is answered once.** Edits declined after a crash were offered again every time that document was opened.
- **The start window works again after a cancelled Open.** Cancelling the file dialog, or choosing a document that would not open, left every button in the start window disabled.
- **Pictures whose names contain spaces show in documents.** A picture inserted from a file such as "My Photo.png" was stored and then never found.
- **Libera Suite always answers its editors.** A request it could not read, or one that failed inside Libera Suite, was dropped without an answer, which the editor took for a lost connection. It now answers with an error and logs the failure.
- **Installing the payload reports its failures as sentences.** Font generation failing, a damaged `config.toml`, a full disk during a download and Ctrl-C during installation each printed a traceback or the wrong advice. Ctrl-C while fonts were being generated also left the previous payload where nothing would find it; it is now put back.
- **`--payload-install --trust-manifest` works without `--from`.** It asked for a manifest at `None/manifest.json`.
- **Options that belong to another command are refused.** `libera --from DIR` opened the start window and ignored the directory; `--from`, `--trust-manifest`, `--port`, `--work` and `--shot` now say which command they go with.
- **A CSV the converter reads wrongly says so when it opens.** In a CSV larger than about 500 KB, the converter skips one character in every 500,000, and when that character is a quote, a comma or a line break, a row is wrong on screen, and wrong in the file after a save. Libera Suite now names those rows when the file opens. The converter itself is fixed for the next payload.
- **The editor's File menu always offers Save As.** It sometimes offered Download As instead, which is the web editor's entry. The editor decides once, while it loads, whether it is a desktop application. The part of it that says so could arrive after the question; when it did, Save As was gone until the document was reopened. Libera Suite now gives the answer before the question is asked.
- **A document no longer stops at "Loading document: 8%".** About one opening in fifty stayed there for good, with no error. The editor asks for its fonts in a burst, Libera Suite's local server queued only five connections, and a font request that found the queue full was refused; the editor never asks again. The queue is now as long as the system allows.
- **On Windows, starting without a payload shows why.** The windowed build has no standard input, and checking for a terminal there failed before the explanation could appear.

## [0.3.2] - 2026-10-01

### Fixed

- **File ▸ Save writes the document in the format it has.** A document in anything but its editor's first format (`.odt`, `.ods`, `.odp`, `.csv`) was saved as a `.docx`, `.xlsx` or `.pptx` inside Libera Suite's own session folder, and the editor reported it saved. The document itself was never written. Closing the window with Save did the same, then cleared the recovery marker, so the edits were lost. A format the converter reads and cannot write, such as `.doc`, now asks where to save a new file, and closing such a window with Save leaves it open and says to use Save As.
- **CSV and TSV files open.** They failed with "could not open" and nothing more. The converter needs to be told how the text is encoded and what separates the fields; Libera Suite now reads both off the file (UTF-8 or Windows-1252; comma, semicolon or tab), and a save writes them back the same way, so a semicolon file from a French Excel stays one.
- **A UTF-8 CSV no longer gains an empty row with each save.** The converter's UTF-8 reader took the end of the text for one more row. Libera Suite now hands it the text in UTF-16, which it measures correctly.
- **Save As `.tsv` writes tabs.** It wrote commas.
- **A document is never replaced by text the converter garbled.** On macOS and Linux, a CSV, TSV or `.txt` holding a character outside Unicode's first 65,536, an emoji say, came out in Latin-1 where UTF-8 was asked for: "é" became the single byte `E9`, through the whole of a CSV. The converter reported success. Such a save now fails and leaves the file as it was; Save As `.xlsx` or `.docx` keeps everything. The fault is in the converter, which only a new payload can fix.
- **A `.txt` opens past its first emoji.** Everything after it used to be dropped on opening, so a save wrote back only what came before.
- **Markdown opens.** Words listed `.md` among the formats it reads, and refused every one.
- **The scroll wheel scrolls spreadsheets on macOS.** Documents and presentations scrolled, while a spreadsheet did not move. On a Mac the spreadsheet engine listens for the browser's old `mousewheel` event, and since a recent Euro-Office change the editor's interface listens for the newer `wheel` event on the same element, which silences the old one there. Libera Suite now registers the old event as the new one, as the engine already does on Linux and Windows.

## [0.3.1] - 2026-09-30

Fixes to the host only. The payload stays at 0.3, so the editors are not downloaded again.

### Fixed

- **A document double-clicked in Finder opens while Libera.app is running.** macOS said "Libera cannot open files in the PowerPoint Presentation (.pptx) format" instead, about a file it opened fine at launch. Finder launches the application only when it is not running; while it runs, a double-click sends it an "open documents" event, and nothing answered that.
- **File ▸ New creates any kind of document from any window**: New ▸ Document, Spreadsheet or Presentation. It used to create the front window's kind only. The start window, which offers every kind, closes once used, so a Words user had no way to a new spreadsheet. On macOS, ⌘N still creates the front window's kind. The editor's own File ▸ Create New, which could only make its own kind, now asks which of the three to create.
- **Updating with the install script no longer deletes your data on Linux.** Without Flatpak, `install.sh` kept its virtualenv at `~/.local/share/libera`, which is also where Libera Suite keeps the editors, the sessions crash recovery reads, and the editor's own settings. Every install starts by deleting the virtualenv, so running the script again to update deleted all of those too. The virtualenv now has a directory of its own, `~/.local/share/libera/venv`. An existing install is moved on its next update, leaving everything else in place, and a launcher entry pointing at the old path is rewritten.
- **No more `! 304` lines on the terminal.** Since 0.3.0 the server answers *not modified* for files the web view already holds. Each of those answers printed a warning. They are now as quiet as any other success.

### Documentation

- The documentation is in **English, French, German, Italian and Spanish**, each edition under its own address (`/en/`, `/fr/`, `/de/`, `/it/`, `/es/`). The developer pages stay in English. The site root sends a reader to their own language, or the one they chose last, and lists all five without JavaScript. Every address the English pages had before redirects to its `/en/` page.
- The Home menu now holds Install, a new *Other ways to install*, What works today, and a new About page with credits. Install is organised by platform, with Homebrew on macOS.
- The site serves its own fonts, Inter and JetBrains Mono. It used to load them from Google Fonts, which sent every reader's address to Google.

## [0.3.0] - 2026-09-29

The first release for **Windows**, and the first with payload **0.3**, so the editors are re-downloaded once on Linux and macOS. The payload moved for attribution: the panel naming the upstream authors and the licence was switched off in every desktop build, and turning it back on changes the editor bundle and not the host.

0.2.2 was prepared and never published; everything it would have shipped is here.

### Added

- **Windows 10 and 11 (x64).** An installer that needs no administrator password and installs for the current account, with the editors and fonts inside it, so nothing is fetched afterwards. It puts Libera Suite in the Start menu, on the desktop, and in Explorer's *Open with* for the formats it reads. Or in PowerShell, `irm https://cdn.abilian.com/libera/install.ps1 | iex`, which checks the installer against its published SHA-256, installs it without questions, checks that it runs, and upgrades when run again. The installer is not yet code-signed, so SmartScreen objects to the downloaded one the first time; [the install page](https://docs.liberasuite.eu/en/main/install/#windows) has the way past it. The one-line install does not meet it.
- **One Libera Suite per user.** Opening a document while Libera Suite is running now hands it to the running instance. It used to start a second process, which could not share the first one's port and so came up on another origin: another localStorage, an editor that had forgotten its theme and units, plus a second taskbar icon for what looks like one application. The running instance publishes where it is in a file under the state directory, with a random token the handover has to present, because any web page the user visits can send a POST to `127.0.0.1`.

- **About now names who wrote the editors, on every surface.** Attribution has been written down since 0.1 and was reachable from none of them.
    - **In the editor**, `File ▸ About` is back. Upstream sets `customization.about = false` in two places whenever the page finds `window.AscDesktopEditor`, on the assumption that the native shell supplies an About of its own, as theirs does. Ours did not, so the theme's attribution string was compiled into all five editors and displayed by nothing: measured on the running editor, `#left-btn-about` and `#about-menu-panel` were both `display:none` and no part of the text appeared on screen. `build/patches/web-apps/0007` leaves `about` at its default in both places, which changes nothing for a web build.
    - **On Linux and Windows**, the item is `Help ▸ About Libera Suite`, since the menu bar there has no standard equivalent.
    - **On macOS**, the work fell to the application menu's own About panel, which reads `NSHumanReadableCopyright` from the running process's main bundle, which outside `Libera.app` is the interpreter's, so "About Libera" used to show *"(c) 2001-2023 Python Software Foundation"*. The host now sets that key alongside the two names it already corrected.
    - **In a software centre**, through an AppStream `metainfo.xml` the Flatpak had been shipping without. It names the developer, the licence and the upstream authors; Flathub asks for it first.
- The attribution says **"includes components from Euro-Office"** where it used to say "is based on" it. The host is ours and original; what comes from upstream is the payload. It also now states that those components are modified, which it did not. `host/about.py` holds the text, and a test compares it against the theme token, the `Info.plist` line and the AppStream metadata, because four copies drift.

### Fixed

- **The second of two documents could fail to open.** `libera a.docx b.pptx` opens the first window at once and the rest once the GUI loop runs. The wait for that loop tested a list pywebview fills *before* it runs, so it returned immediately. Every later document then raced `webview.start()`, and losing meant a window never created or never initialised. It now waits for the first window to be shown, which is the condition pywebview itself uses for the same job.
- **An upgrade could leave the editor running on stale files.** Payload files went out with a `Last-Modified` and no `Cache-Control`, which lets a browser reuse them without asking, from a store kept across upgrades. They now go out with an `ETag` and revalidate every time. The editor's own service worker, which cached every payload in one shared bucket, is replaced by one that caches nothing and clears what the old one stored: a fresh install had been running on a cached font index of 188 fonts where 32 were installed, and never drew the document.
- **Help still said nothing when no browser could be opened**, which 0.2.1's notes claimed to have fixed. The fix missed the wheel: 0.2.1 went to PyPI at 09:59 UTC and the repair landed at 13:32. 0.2.1 shipped the first attempt instead, which asked `webbrowser.open()` whether it had worked. On Linux that returns true when a *process started*, not when a URL opened, so a machine with no usable handler still got silence. The host now runs the opener itself and reads what it did: a non-zero exit puts the URL on screen, while an opener that stays attached to the browser counts as success. External links clicked inside the editor take the same path.
- **The README claimed attribution appeared in `Help ▸ About` when no such item existed**, and described the editors as running "unmodified" while patches apply to them. The engine is unmodified; it now says that instead.
- **`build/macos-app.sh` deleted two lines of its own `Info.plist`.** The heredoc that writes the plist has to expand `$VERSION`, so it is unquoted, which made the backticks in an XML comment command substitution. Every build printed `com.microsoft.word.doc: command not found` and dropped two format identifiers from the comment. The plist stayed valid, so only documentation was lost, but the error read like a failure.

### Documentation

- [The install page](https://docs.liberasuite.eu/en/main/install/) now opens with a table naming the one command per platform and what it gives you, states the Python 3.12 floor that the installer enforces and the page never mentioned, says that macOS gets a command and not an icon yet, and ends with `libera --diagnose` and the output to expect. Removing it is documented in full for the first time.
- [Work with documents](https://docs.liberasuite.eu/en/guide/documents/) gained the two settings people go looking for: how to change a document's spellcheck language, and where the author name written into saved files comes from.
- [What works today](https://docs.liberasuite.eu/en/main/status/) no longer claims there is no Help menu. There is one, on every platform; what is missing is help readable with the machine offline.

## [0.2.1] - 2026-09-25

The same editors: payload **0.2** is unchanged, so an existing install is not re-downloaded. Everything here is the host.

*The Help fix below did not make this wheel; it shipped in 0.3.0, which says why.*

### Fixed

- **Help said nothing at all when no browser could be opened.** It asked the desktop to open the documentation and threw away the answer, so on a machine with none, the menu item did nothing visible. It now puts the URL on screen. The same went for external links from inside the editor, which reported success in the log whatever the desktop did with them.
- **The installer refused to run twice.** `curl … | sh` over an existing install ended in `FATAL: flatpak install failed`, because a Flatpak bundle cannot be installed over itself without `--reinstall`. Re-running it now replaces the installed copy, which is also how it upgrades.

### Changed

- The package builds with **hatchling**, where it used `uv_build`. `uv_build` ships as a platform-specific Rust binary, so anything applying `--no-binary :all:` to build dependencies (Homebrew, a distribution packager, an air-gapped install) tried to compile it and needed a Rust toolchain for a package that is pure Python. `uv build` and `uv sync` are unaffected.

## [0.2.0] - 2026-09-24

This release brings payload **0.2** and is the first that installs on Ubuntu 22.04 and Debian 12.

### Added

- `libera --version`, and `-V`. It names the application and the payload it expects, because a bug report giving only one of them does not say which of the two was in play.
- **Flatpak bundles**, one per architecture: `flatpak install ./libera-0.2.0-amd64.flatpak`. Installing one takes that file and nothing else. The editors are inside the bundle, so nothing is downloaded afterwards, though it does resolve `org.gnome.Platform` from Flathub, so a machine with no flathub remote needs one added first. This is the Linux install to prefer: it brings its own GTK and WebKit, which `pip` cannot.
- **An installer script**, for a machine where you have no root. It writes to `~/.local/bin` and `~/.local/share` and nowhere else, and on Linux it installs the Flatpak bundle when `flatpak` is present.

  ```sh
  curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
  ```

- **A Homebrew formula**: `brew install abilian/tap/libera`.

### Changed

- **Linux now needs Ubuntu 22.04, Debian 12, or newer**, where payload 0.1 needed Ubuntu 24.04. Both Linux cores are built on Ubuntu 22.04, so the converter asks for glibc 2.34 and GLIBCXX 3.4.26, where payload 0.1 wanted 2.38 and 3.4.32. Measured by unpacking the published core in a clean container of each release, then running `x2t`.
- The payload is version 0.2, so `libera --payload-install` fetches a new one over any existing install.

### Fixed

- **Installing a payload no longer risks destroying the one already there.** The download was staged in `/tmp` and moved into place. A rename cannot cross a filesystem, so where `/tmp` is its own mount, which is most Linux boxes, the move degraded to a copy. The install stopped being atomic, needed the payload's size twice, and running out of room part-way left a half-populated directory where a working payload had been. Staging now happens beside the destination, so the move is a rename. A failure puts the previous payload back.
- `libera --payload-install` refuses before downloading anything when the disk cannot hold the result. It used to fail a hundred megabytes in, with six tracebacks about individual files.

### Documentation

- [The install page](https://docs.liberasuite.eu/en/main/install/) states the Linux floor and how it was measured.
- `libera` 0.1.0 is still on PyPI and still cannot work. Ask for `libera>=0.1.1` until it is yanked.

## [0.1.1] - 2026-09-18

The first release that works, and in practice macOS (Apple Silicon) only: the same wheel installs on Linux and cannot open a window until the distribution's GTK and PyGObject packages are present.

### Fixed

- The payload manifest is found where it is, so `libera --payload-install` no longer answers every request with *"this build ships no manifest, so downloads cannot be verified."*
- The manifest describes the payload the origin is actually serving. Every hash in 0.1.0's copy named bytes that had been rebuilt after it was published, so even with the lookup repaired, every download would have failed verification.

### Changed

- Package metadata a public release should have had: an Apache-2.0 licence expression covering `src/libera/`, classifiers, and project URLs. The editor payload is AGPL-3.0 and its corresponding source is recorded in every payload manifest; see [the licence page](https://docs.liberasuite.eu/en/licence/) and `libera --payload-status`.
- The macOS bundle declares the deployment target its converter really has, read off `x2t` at build time. It had promised macOS 11 against a binary needing 14, which on Big Sur through Ventura is an application that launches and a converter that cannot load.

## [0.1.0] - 2026-09-16

Published, and broken in three independent ways: the manifest lookup above, a manifest describing artifacts that no longer existed, and a publication that preceded the payload origin itself. **0.1.1 replaces it.** Installing 0.1.0 gets you a wheel that cannot fetch its own payload.
