# What works today

Libera Suite is early. This page is a status list: it says what is built, what is half-built and what has not been started.

## Works

| | |
| :--- | :--- |
| **Four applications** | Windows 10 and 11 on x64, Linux on x86_64 (arm64 on 0.4.1), macOS on Apple Silicon. Words, Tables and Slides edit; Diagrams reads Visio files. |
| **Open and save** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Export** | Save As offers a format popup per application, PDF included. Every format offered is checked by converting a document to it and reading its text back. |
| **Images** | Preserved on open and save; Insert ▸ Image works. |
| **Print** | Renders to PDF, asks where to keep it, and opens it in your PDF viewer. |
| **Spell checking** | Five languages, with suggestions. See below. |
| **In your language** | The applications follow your system's language, and a new document starts from your region's blank: A4 paper everywhere but the US, and spell-checked in your language. In French, German, Italian and Spanish, the menu bar, the start window and the dialogs follow too; in any other language they are in English. |
| **Recent documents** | File ▸ Open Recent remembers the last 20. |
| **Several documents at once** | Of any kind, one window each, or on macOS one tab each when the system prefers tabs: from File ▸ New or File ▸ Open, by double-clicking in the file manager, or as `libera *.docx`. The file's type picks the application. |
| **In the Start menu and the launcher** | On Windows, the installer puts Libera Suite in the Start menu, on the desktop and in Explorer's *Open with*. On Linux, the Flatpak adds it to the launcher with its icon and file associations, and `libera --launcher-install` does the same for any other install. |
| **A start window** | `libera` on its own: new, open, recent, and where the components came from. |
| **Crash recovery** | Unsaved edits are offered back the next time you open the document. |
| **A document open elsewhere** | Opened while LibreOffice or another copy of Libera Suite has it, it is marked *locked for editing*: you can read and change it, and saving asks where, so the other copy's file is never written over. Opening a document a window already shows brings that window forward. Neither Microsoft Office nor Libera Suite sees the other's locks, so a document open in Word is not protected. |
| **Closing asks** | A window with unsaved changes offers Save, Don't Save or Cancel. |
| **A menu bar** | File, Edit, View and Help on every platform. macOS adds Window, and the usual shortcuts. |
| **About** | Who wrote the components, and under what licence: `File ▸ About` inside the document window, and `Help ▸ About Libera Suite` on Linux and Windows. macOS puts it in the application menu. |
| **Settings persist** | Theme, units, spellcheck language and the like are still set after a restart. |
| **Component install** | From the origin, or from a local directory of built artifacts. Either way every artifact is verified against hashes shipped in the application. |

## Known issues

**None of these needs reporting**, since they are known. The sections below have the detail.

| | |
| :--- | :--- |
| **macOS calls it an unidentified developer** | Only for a `Libera.app` you built yourself; it is not signed with a Developer ID, so Gatekeeper objects the first time. [Other ways to install](alt-install.md#a-double-clickable-application-on-macos) has the way past it. A `pip`, `pipx` or Homebrew install never meets it. |
| **Run from a terminal, the Dock says "Python"** | Only when you start `libera` from a `pipx` or virtualenv install. A Dock tile is named after the bundle it was launched from: here, the Python interpreter's, which nothing in the application can change. The icon and the menu bar are ours either way; `Libera.app` says Libera. A document dropped on that Python tile is refused in Python's name; `Libera.app`'s tile takes it. |
| **Diagrams cannot save** | It opens `.vsdx` and shows it. The converter cannot write any Visio format, so there is nothing to save and no blank to start from. |
| **No PDF editing** | PDFs are written only. Opening one for editing is not wired up. |
| **A shallow menu bar, with few shortcuts shown on Linux and none on Windows** | Linux and Windows get File, Edit, View and Help, drawn in the window. On Linux, New, Open and Close show Ctrl-N, Ctrl-O and Ctrl-W, and no other item shows its key; on Windows none does. The keys work all the same: Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Shift-S, Ctrl-P and Ctrl-Z. macOS gets those menus plus Window, with the usual shortcuts. |
| **No tabs on Linux or Windows** | One window per document there. macOS has tabs. |
| **Windows warns about the installer** | The downloaded installer is not yet code-signed, so SmartScreen says *"Windows protected your PC"* the first time. [Install](install.md#windows) has the way past it. The one-line PowerShell install never meets it. |

If you hit something that is *not* on this list, [tell us about it](../feedback.md).

## Half-built

**The menu bar on Linux and Windows.** It is drawn inside the window, with File, Edit, View and Help, and every item works. On Linux, New, Open and Close show their keys, and no other item does; on Windows none does. The usual keys work all the same. Ctrl-N makes a new document of the same kind and Ctrl-O opens one. Ctrl-W closes the window, asking first about unsaved changes. The components' own Ctrl-S, Ctrl-Shift-S (Save As), Ctrl-P and Ctrl-Z work as well. On Windows, Ctrl-N, Ctrl-O and Ctrl-W have not yet been checked on a real machine. File ▸ New ▸ Document, Spreadsheet or Presentation works, as do the New tiles in the start window and the document's own File tab.

**`Libera.app` on macOS.** `build/macos/macos-app.sh` builds it. It opens a document on a double-click or dropped on its Dock icon, appears in *Open With*, and shows the Libera mark in the Dock. But it is a launcher around the interpreter it was built with (nothing is embedded, signed or notarised), so it is not something you can hand to somebody else yet.

## Not started

### In the document window

- **Password-protected documents.** Neither opening nor saving one.
- **Digital signatures.**
- **Mail merge.**
- **Plugins.** Disabled upstream in this fork, so the panel never appears.
- **Macros.** Turned off. The components' own macros are JavaScript, and run none of the VBA in documents from Microsoft Office, so a document's macros are not run. They are kept: saving a `.docm`, `.xlsm` or `.pptm` leaves its VBA as it was. [The roadmap](../develop/roadmap.md) says what comes instead.

### In the application

- **Tabs on Linux and Windows.** One window per document there, which the taskbar groups.
- **A redistributable application on macOS.** `Libera.app` runs from your own checkout and embeds no interpreter and no components. Windows has one: its installer brings everything.
- **Automatic updates**, and **code signing**. macOS treats a `Libera.app` you have built as software from an unidentified developer. Windows warns about the downloaded installer.
- **Offline help**, readable without a browser or a network. The Help menu opens this site; About works offline. See below.

### Elsewhere

- **Editing diagrams.** Diagrams opens `.vsdx` and shows it. The converter cannot write any Visio format, so there is nothing to save and no blank to start from.
- **PDF editing.** Upstream has a PDF editor. Libera Suite does not install it yet, since the host has no way to open a PDF in it.
- **Collaboration, cloud storage, accounts, telemetry.** None of it is built. None of it is being worked on. [The roadmap](../develop/roadmap.md) says what each would look like if it arrived. [What leaves your machine](../index.md#what-leaves-your-machine) lists the application's entire network use.

## Notes on specific gaps

### Help

There is a **Help** menu, on every platform, and it opens this site in your browser. No help lives *inside* the application, where it would be readable with the machine offline. Upstream ships a full manual. Libera Suite leaves it out: it documents ONLYOFFICE, and it weighs 84 MB in eight languages. Offline help comes back once there is enough documentation of our own to ship.

### Spell checking

Libera Suite ships dictionaries for **English (US and UK), French, German, Spanish and Italian**: 9.5 MB, chosen because the full set is 327 MB. Adding a language is one line in `build/payload/dictionaries.txt` and a rebuild of the components.

A language with no dictionary is not an error: its words are simply treated as correct, which is what upstream's own desktop application does. Words added through *Add to dictionary* are kept, for every document and every language.

How to set a document's language is in [Work with documents](../guide/documents.md#spell-checking).

### Your name in documents

Tracked changes and comments are attributed to a person, whose name is written into the saved file. Libera Suite takes it from your account: the full name macOS knows you by, the display name of your Windows account, or the full-name field of your Unix account on Linux. Another can be set in the configuration file; there is no menu item for it yet. [Work with documents](../guide/documents.md#your-name-in-documents) has the detail.

### Fonts

Libera Suite ships a core font set: Liberation, Carlito, Caladea, Open Sans and a few others, enough to render ordinary documents faithfully at 7 MB. The full set is 248 MB. A document that asks for a font outside that set uses the one installed on your machine, on screen and in its PDF, and gets a substitute only when your machine does not have it either. Libera Suite lists your fonts when it first starts, and again in the background whenever you install or remove one; the windows you open after that use the new list. Widening the set, particularly for CJK, is an open decision.

### Rendering fidelity

The layout engine is upstream's and is mature. Where you see something wrong, the likelier cause is our packaging (a missing font, a missing resource). That makes such reports especially useful; please send [feedback](../feedback.md) with the file.
