# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two versions move here and they move independently. The **application** is this package, `libera`. The **editor payload** is the Euro-Office build it fetches on first use, versioned separately so that a fix to the host does not force a 120 MB re-download. `libera --version` prints both.

## [0.6.0] - Unreleased

### Fixed

- **An OpenDocument file without master styles keeps its styles.** Every paragraph of such a file opened in the default style, with no heading larger or bolder than the text, where LibreOffice shows them as written. The file is valid, and programs that write OpenDocument often leave master styles out.

## [0.5.0] - 2026-10-20

The first with payload **0.5**, so the editors are downloaded again once.

### Added

- **The fonts installed on your machine.** A document set in a font you have installed shows in it, on screen and in its PDF, where it used to get a substitute. The fonts are listed as the editors are installed, and again in the background whenever one is installed or removed; the windows opened after that use the new list. Nothing is copied. `installed_fonts = false` in the configuration file keeps to the fonts Libera Suite ships.
- **The editors in your language.** Words, Tables, Slides and Diagrams follow your system's language, where they were always in English, and `ui_language` in the configuration file chooses another. A new document starts from the blank for your language and region: A4 paper everywhere but the US, where every one used to be US Letter, and spell-checked in your language. In French, German, Italian and Spanish the menu bar, the start window and the dialogs follow, and Help opens the documentation in that language; in any other they are in English. In French, Italian, Spanish and Portuguese the editors needed strings the translations lacked, and Words never became editable; the missing strings are now in English.

### Changed

- **The editor's page can reach nothing but Libera Suite itself.** A security policy stops it loading or sending anything elsewhere, whatever its code would like: upstream's bundles still carry an analytics loader, which therefore cannot run. The exception is a picture a document links to by its web address, which is fetched as in any office suite.
- **Macros are turned off.** The editor's own macros are JavaScript against its API and run none of the VBA a document from Microsoft Office carries; the buttons are gone and a document's macros are not run. The payload leaves out Monaco, the macro dialogs' code editor, 22 MB.
- **Old versions of the editors are removed.** Each update used to leave the previous version on disk, about 400 MB each. One that nothing has used for four weeks is now removed, at launch or after an install; Libera Suite installed another way on the same account keeps the one it runs. `libera --payload-status` lists the versions installed, with when each was last used.

- **A document is on screen sooner.** Its window opens at once and the editor loads while the document is converted, where the window used to wait for the conversion: on our Mac, about a second sooner for a small Words document. A document the converter cannot read now opens its window, says so, and closes it again, the first one of a launch included, which used to say so in the terminal.
- **The editors follow Euro-Office's own desktop release.** They are built from the revisions behind Euro-Office's Desktop Editors 9.3.5-2, of 2026-10-08, where they were from August's. A bug Euro-Office has fixed in its desktop editors is fixed here too.

### Removed

- **Linux on arm64 stays on 0.4.1.** There is no arm64 build of 0.5: the install script installs 0.4.1 on those machines, and `libera --payload-install` from a 0.5 wheel there says to install 0.4.1. A later version builds arm64 again.
- **Tables no longer saves as `.xlsb`**, Excel's binary workbook. The converter crashed writing one on Linux, with payload 0.5 as with 0.4.1. Save as `.xlsx` instead; Excel opens both.

### Fixed

- **A save keeps a document's VBA.** Saving a `.docm`, `.xlsm` or `.pptm` leaves its macros byte for byte as they were, after an edit too. Words now opens and saves `.docm` and `.dotm`, where a plain save of one asked for a new file in a format with nowhere to keep them, and Slides saves `.ppsm`.
- **On Windows, the start window's Recent list shows each document's name**, with its folder beneath, where it showed the whole path as the name.
- **The font menu draws each name whole.** Each name was squeezed into a row two pixels shorter than its picture, and thin white lines ran through some names.
- **An `.xlsb` file opens.** It used to open as an empty presentation, Excel's own files included.
- **On macOS, quitting with Cmd-Q leaves no document locked.** The lock beside each open document stayed behind, so LibreOffice, or Libera Suite under another account, took the document for one still being edited. Closing the windows first did release it.
- **On Windows, the Recent list could lose its entries.** Windows refuses to replace a file another window is reading at that instant, and to read one being replaced. A read that failed was taken for an empty list, which the next document opened then saved over everyone's entries; the other state files, such as the document a window has open, failed the same way. Both sides now try again for a moment.

## [0.4.2] - Unreleased

### Fixed

- **File > Reload could lose the edits since the previous reload.** It folds the edits into the document through a file of the same name every time: a conversion that wrote nothing found the previous reload's file there and read it back instead. An edit made while the fold ran was also lost.
- **A save can no longer leave half a document behind.** The saved file was copied over the old one in place, so a crash or a full disk part way through left it truncated. It is now written beside it and put in its place in one step, the way each system's own applications save: the document keeps its permissions, its Finder tags and its other attributes, and a symbolic link stays one.
- **Reload no longer freezes every window** while it converts the document.
- **A conversion that never ends is a failed one** after ten minutes, where it used to leave the save waiting for good and, after a few such documents, every conversion.
- **Save As and questions no longer hang when their dialog cannot be shown.** The failure is reported on macOS and Linux.
- **Two copies of Libera Suite running at once no longer lock each other's windows out.** Each one's key went into a cookie of the same name, and the second replaced the first's.

## [0.4.1] - 2026-10-14

### Security

- **Another account on the same computer could read the open document.** The editor's server, on `127.0.0.1`, checked the headers a web browser sends, which stop a web page and nothing else: `curl` read the open document and the recent list. Nothing in those checks depends on which account runs it. Every request now needs a key made at each launch: the windows have it in their address, and on disk only your account can read it. Measured on 0.4.0; fixed for every route, the editor's own files included.
- **Libera Suite's own folder is now private to your account.** It holds a copy of each open document, the Recent list and the server's key, and was created readable by every account, so the home folder's permissions alone kept others out. Those are private by default on the distributions the install page names, but a home folder made before Ubuntu 21.04 is not. Each launch now makes the folder `700`, one an earlier version made included.

### Fixed

- **Save As RTF wrote no text** from a document opened from a `.txt` file, and from a `.docx` file that ends without section properties, until something in it was edited. A `.docx` file with a section break lost everything after the break. The converter read paragraphs into sections and made sections only from section properties. It is patch 0033 in the converter, so it comes with a new payload. Measured on payloads 0.2 to 0.4.

## [0.4.0] - 2026-10-12

The first with payload **0.4**, so the editors are downloaded again once, about 100 MB on macOS. It fixes the converter where 0.3's host could only refuse a save or warn.

### Added

- **Convert from the command line.** `libera --convert *.docx -t pdf` writes each document in another format beside it, with no window; `-o FILE` names the result of one document (`-` for standard output), and `--outdir DIR` puts them elsewhere. The spellings are pandoc's. The conversion is the one Save As makes.
- **A window shows when its document has unsaved edits.** On macOS, the dot in the close button and "Edited" after the title, as in Pages and Keynote; on Linux and Windows, a `*` before the title.
- **A document open somewhere else says so.** Libera Suite now writes a lock file beside each document it opens, in LibreOffice's format, so each sees the other's. A document LibreOffice, or another copy of Libera Suite, already has open is marked *locked for editing*: you can read and change it, and saving asks where, so the other copy's file is never written over. Save As onto a file someone else has open is refused, and says who has it. A lock left by a crash of Libera Suite is taken over on the next open.
- **Libera Suite says when a newer version is out.** At most once a day it reads the latest release's version number from the CDN, and mentions a newer one once, with how to update for the way it was installed. It downloads nothing; offline, it says nothing. The home page's list of connections has the row. `check_updates = false` in `config.toml` turns it off.
- **Drag and drop.** A document dropped on any window, the start window included, opens in a window of its own. An image dropped on a document is inserted into it. A dropped file can no longer replace the editor with the file itself.
- **Your name in documents can be set.** `user_name` in `config.toml` replaces your account's name in tracked changes, in comments and in the lock file. The user guide says where the file is on each platform.

### Changed

- **The editors are smaller**, by about 38 MB once installed on macOS. The native libraries lose their symbol tables. The fallbacks for browsers without WebAssembly are gone too, since the webviews and the converter all have it.
- **Print asks where to keep the PDF.** It starts in the document's folder; another folder is a click away. The PDF used to go into Libera Suite's own working folder, which is hard to find and is cleared when the window closes.
- **Ctrl-N, Ctrl-O and Ctrl-W work on Linux and Windows.** They make a new document of the same kind, open one, and close the window, asking first about unsaved changes. Ctrl-N did nothing there. The menus still show no shortcuts.
- **Installing the payload says which one first.** `--payload-install` and the download a first start offers both begin with "Downloading payload version 0.4". The last line says where it went.
- **The host's web server is Bottle**, which pywebview already brings, running on the standard library's server as before. Nothing changes for the editor; the host's endpoints are now plain functions, which the framework never reaches.

### Fixed

- **A CSV or `.txt` holding an emoji saves as one.** On macOS and Linux, the converter wrote plain text holding a character beyond Unicode's first 65,536 in Latin-1 where UTF-8 was asked for, so Libera Suite refused the save. It now writes UTF-8.
- **A large CSV is read whole.** The converter skipped one character in every 500,000. Where that character was a quote, a comma or a line break, a cell split in two, or two cells or two rows ran together; Libera Suite named the rows when the file opened. It now reads them as written.
- **Without Flatpak, Linux runs on RHEL 9 and its rebuilds.** One function in the converter asked for glibc 2.35, where RHEL 9 has 2.34. The converter now asks for 2.34.
- **OpenDocument files are written and read more faithfully**: 68 fixes to the converter for `.odt`, `.ods` and `.odp`, each found against LibreOffice's own test documents.
- **Cmd-W and Cmd-Q work again after a slideshow** on macOS. Once the show had ended, the editor took both keys and the menu never saw them.
- **A document dropped on `Libera.app`'s Dock icon opens.** macOS refused it, saying Python could not open that format: the launcher handed over to Python, and from then on macOS took the running application for Python. The launcher now runs Python inside itself.
- **Add to dictionary keeps the word.** It was handed to the spell checker, which only checks and suggests and dropped it, so the word was flagged again in the next session. The words are kept beside the Recent list, for every document and every language.
- **Several documents opened at once are all in the Recent list.** Opened together, most of them were dropped. A window reading the list while another wrote it could also empty it altogether.
- **A dozen documents opened at once no longer start a dozen converters.** Each takes tens to hundreds of MB; the rest now wait their turn.
- **The editor's File ▸ Close closes the window.** It only hid the menu, as Back does. It now closes the window as its close button does, asking first about unsaved changes.
- **Opening a document twice brings its window forward.** It opened a second window on the same file. Each window saved over the other, so the last save won and the other window's edits were lost.
- **The first document's lock goes when its window closes.** The window a launch opens first was the one that never let go: after Libera Suite quit, LibreOffice still saw the document as open, and edits left by "Don't Save" were not offered back when it was opened again. Every lock Libera Suite holds is also released when it quits.
- **Opening several documents at once starts one Libera Suite.** Explorer starts a copy per file of a multi-selection. A document handed to a running copy that took more than three seconds to open started a second one too. Two copies shared one working folder, where each could delete the working files of the other's open documents. A launch now waits for the copy that is starting and hands its documents over.
- **A first document that cannot be opened says so.** `libera damaged.docx` ended in a traceback, and from Finder or a file manager in nothing at all; a document opened later already got a dialog.
- **A save that writes nothing is a failed save.** Every save went through one staging file, so a conversion that wrote nothing found the previous save's file there and reported success. Each save now has its own. An empty result counts as a failure.
- **A problem on a background thread is shown.** Opening, menu actions and drops run on threads of their own. A failure there went only to a terminal, which a launch from the desktop does not have.
- **Installing the payload checks every font thumbnail.** The install accepted a font run that stopped partway; the font menu then showed blank names. It now checks the thumbnails and the number of fonts, as the build does.
- **Cancelling File ▸ Open leaves the window as it was.** It reloaded the document.
- **The editor can only copy in an image you chose.** Inserting a picture copies it into the document's working folder. The host took any path the page named, which would have let a script in the editor read any of your files. It now copies only what you picked in a dialog or dropped.
- **Another web page cannot read Libera Suite's scripts.** A site open in your browser could load them from the local server Libera Suite runs, and read the name of whoever has a document locked; such requests are now refused.
- **A failure to note unsaved edits is no longer silent.** The editor tells the host when a document has unsaved edits, which is what recovery after a crash relies on; a refused report went unnoticed. It is now logged.
- **An idle window stops polling.** Each window checked forty times a second, for as long as it was open, for an editor its outer frame never has.
- **About says which versions are running**, the application's and the editors', as `libera -V` does. It named who wrote what, and on macOS, outside `Libera.app`, showed Python's version.

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
