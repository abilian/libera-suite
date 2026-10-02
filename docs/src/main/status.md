# What works today

Libera Suite is early. This page is a status list: it says what is built, what is half-built and what has not been started.

## Works

| | |
| :--- | :--- |
| **Four editors** | Windows 10 and 11 on x64, Linux on x86_64 and arm64, macOS on Apple Silicon. Words, Tables and Slides edit; Diagrams reads Visio files. |
| **Open and save** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Export** | Save As offers a format popup per editor, PDF included. Every format offered was checked by converting to it. |
| **Images** | Preserved on open and save; Insert ▸ Image works. |
| **Print** | Renders to PDF and opens it in your PDF viewer. |
| **Spell checking** | Five languages, with suggestions. See below. |
| **Recent documents** | File ▸ Open Recent remembers the last 20. |
| **Several documents at once** | Of any kind, one window each: from File ▸ New or File ▸ Open, by double-clicking in the file manager, or as `libera *.docx`. The file's type picks the editor. |
| **In the Start menu and the launcher** | On Windows, the installer puts Libera Suite in the Start menu, on the desktop and in Explorer's *Open with*. On Linux, the Flatpak adds it to the launcher with its icon and file associations, and `libera --launcher-install` does the same for any other install. |
| **A start window** | `libera` on its own: new, open, recent, and where the payload came from. |
| **Crash recovery** | Unsaved edits are offered back the next time you open the document. |
| **Closing asks** | A window with unsaved changes offers Save, Don't Save or Cancel. |
| **A menu bar** | File, Edit, View and Help on every platform. macOS adds Window, and the usual shortcuts. |
| **About** | Who wrote the editors, and under what licence: `File ▸ About` inside the editor, and `Help ▸ About Libera Suite` on Linux and Windows. macOS puts it in the application menu. |
| **Settings persist** | Theme, units, spellcheck language and the like are still set after a restart. |
| **Payload install** | From the origin, or from a local directory of built artifacts. Either way every artifact is verified against hashes shipped in the application. |

## Known issues

**None of these needs reporting**, since they are known. The sections below have the detail.

| | |
| :--- | :--- |
| **macOS calls it an unidentified developer** | Only for a `Libera.app` you built yourself; it is not signed with a Developer ID, so Gatekeeper objects the first time. [Other ways to install](alt-install.md#a-double-clickable-application-on-macos) has the way past it. A `pip`, `pipx` or Homebrew install never meets it. |
| **Run from a terminal, the Dock says "Python"** | Only when you start `libera` from a `pipx` or virtualenv install. A Dock tile is named after the bundle it was launched from: here, the Python interpreter's, which nothing in the application can change. The icon and the menu bar are ours either way; `Libera.app` says Libera. |
| **Diagrams cannot save** | It opens `.vsdx` and shows it. The converter cannot write any Visio format, so there is nothing to save and no blank to start from. |
| **A CSV or `.txt` with an emoji cannot be saved as one** | On macOS and Linux, the converter garbles plain text holding a character beyond Unicode's first 65,536, such as an emoji. Libera Suite refuses that save and leaves the file as it was. Save As `.xlsx` or `.docx` keeps everything. A fix to the converter is planned for the next payload. |
| **In a CSV over about 500 KB, a row can be read wrongly** | The converter skips one character in every 500,000. When that character is a quote, a comma or a line break, a cell is split in two, or two cells or two rows run together. Libera Suite names the rows it affects when the file opens: check them before saving, because a save writes what the sheet shows. A fix to the converter is planned for the next payload. |
| **No PDF editing** | PDFs are written only. Opening one for editing is not wired up. |
| **A shallow menu bar, with no shortcuts on Linux or Windows** | Linux and Windows get File, Edit, View and Help, drawn in the window, with no key equivalents on any of them; the editor's own Ctrl-S, Ctrl-P and Ctrl-Z still work inside the page. macOS gets those plus Window, with the usual shortcuts. |
| **No tabs** | One window per document. |
| **No file locking** | Editing the same document in two windows will lose one set of changes. |
| **Windows warns about the installer** | The downloaded installer is not yet code-signed, so SmartScreen says *"Windows protected your PC"* the first time. [Install](install.md#windows) has the way past it. The one-line PowerShell install never meets it. |

If you hit something that is *not* on this list, [tell us about it](../feedback.md).

## Half-built

**The menu bar on Linux and Windows.** It is drawn inside the window, with File, Edit, View and Help, and every item works. None has a keyboard shortcut of its own, so the keys you already use go to the editor: Ctrl-S, Ctrl-P and Ctrl-Z work inside the page. Ctrl-N does nothing on Linux; on Windows it has not been checked. File ▸ New ▸ Document, Spreadsheet or Presentation works, as do the New tiles in the start window and the editor's own File tab.

**`Libera.app` on macOS.** `build/macos-app.sh` builds it. It opens a document on a double-click, appears in *Open With*, and shows the Libera mark in the Dock. But it is a launcher around the interpreter it was built with (nothing is embedded, signed or notarised), so it is not something you can hand to somebody else yet.

## Not started

### In the editor

- **Password-protected documents.** Neither opening nor saving one.
- **Digital signatures.**
- **Mail merge.**
- **Plugins.** Disabled upstream in this fork, so the panel never appears.

### In the application

- **Tabs.** Windows exist and the Window menu lists them, but they cannot be merged into one window.
- **File locking.** Two copies of Libera Suite editing the same file will not notice each other.
- **A redistributable application on macOS.** `Libera.app` runs from your own checkout and embeds no interpreter and no payload. Windows has one: its installer brings everything.
- **Drag and drop** onto the window or the Dock icon.
- **Automatic updates**, and **code signing**. macOS treats a `Libera.app` you have built as software from an unidentified developer. Windows warns about the downloaded installer.
- **Offline help**, readable without a browser or a network. The Help menu opens this site; About works offline. See below.

### Elsewhere

- **Editing diagrams.** Diagrams opens `.vsdx` and shows it. The converter cannot write any Visio format, so there is nothing to save and no blank to start from.
- **PDF editing.** The payload has an editor for it. Nothing routes to it yet.
- **Collaboration, cloud storage, accounts, telemetry.** None of it is built. None of it is being worked on. [The roadmap](../develop/roadmap.md) says what each would look like if it arrived. [What leaves your machine](../index.md#what-leaves-your-machine) lists the application's entire network use.

## Notes on specific gaps

### Help

There is a **Help** menu, on every platform, and it opens this site in your browser. No help lives *inside* the application, where it would be readable with the machine offline. Upstream ships a full manual. Libera Suite leaves it out: it documents ONLYOFFICE, and it weighs 84 MB in eight languages. Offline help comes back once there is enough documentation of our own to ship.

### Spell checking

Libera Suite ships dictionaries for **English (US and UK), French, German, Spanish and Italian**: 9.5 MB, chosen because the full set is 327 MB. Adding a language is one line in `build/dictionaries.txt` and a payload rebuild.

A language with no dictionary is not an error: its words are simply treated as correct, which is what upstream's own desktop application does. Personal dictionaries (*Add to dictionary*) are not stored yet, so a word you add comes back next session.

How to set a document's language is in [Work with documents](../guide/documents.md#spell-checking).

### Your name in documents

Tracked changes and comments are attributed to a person, whose name is written into the saved file. Libera Suite takes it from your account: the full name macOS knows you by, the display name of your Windows account, or the full-name field of your Unix account on Linux. There is no way to change it yet. [Work with documents](../guide/documents.md#your-name-in-documents) has the detail.

### Fonts

Libera Suite ships a core font set: Liberation, Carlito, Caladea, Open Sans and a few others, enough to render ordinary documents faithfully at 7 MB. The full set is 248 MB. A document that asks for a font outside that set, and outside the fonts installed on your machine, gets a substitute. Widening the set, particularly for CJK, is an open decision.

### Rendering fidelity

The layout engine is upstream's and is mature. Where you see something wrong, the likelier cause is our packaging (a missing font, a missing resource). That makes such reports especially useful; please send [feedback](../feedback.md) with the file.
