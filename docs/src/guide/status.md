# What works today

Libera Suite is early. This page is a status list: it says what is built, what is half-built and what has not been started.

## Known issues

**None of these needs reporting**, since they are known and the rest of this page has the detail.

| | |
| :--- | :--- |
| **macOS calls it an unidentified developer** | Only for a `Libera.app` you built yourself; it is not signed with a Developer ID, so Gatekeeper objects the first time. [Install](install.md#a-double-clickable-application) has the way past it. A `pip`, `pipx` or Homebrew install never meets it. |
| **Run from a terminal, the Dock says "Python"** | Only when you start `libera` from a `pipx` or virtualenv install. A Dock tile is named after the bundle it was launched from: here, the Python interpreter's, which nothing in the application can change. The icon and the menu bar are ours either way; `Libera.app` says Libera. |
| **Diagrams cannot save** | It opens `.vsdx` and shows it. The converter cannot write any Visio format, so there is nothing to save and no blank to start from. |
| **No PDF editing** | PDFs are written only. Opening one for editing is not wired up. |
| **A shallow menu bar, with no shortcuts on Linux or Windows** | Linux and Windows get File, Edit, View and Help, drawn in the window, with no key equivalents on any of them. macOS gets those plus Window, with the usual shortcuts: the editor's own Ctrl-S, Ctrl-P and Ctrl-Z still work inside the page. |
| **No tabs** | One window per document. |
| **No file locking** | Editing the same document in two windows will lose one set of changes. |
| **Windows warns about the installer** | The downloaded installer is not yet code-signed, so SmartScreen says *"Windows protected your PC"* the first time. [Install](install.md#on-windows) has the way past it. The one-line PowerShell install never meets it. |

If you hit something that is *not* on this list, [tell us about it](../feedback.md).

## Works

| | |
| :--- | :--- |
| **Four editors** | Windows 10 and 11 on x64, Linux on x86_64 and arm64, macOS on Apple Silicon. Words, Tables and Slides edit; Diagrams reads Visio files. |
| **Open and save** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Export** | Save As offers a format popup per editor, PDF included. Every format offered was checked by converting to it. |
| **Images** | Preserved on open and save; Insert ▸ Image works. |
| **Print** | Renders to PDF and opens it in your PDF viewer. |
| **Spell checking** | Six languages, with suggestions. See below. |
| **Recent documents** | File ▸ Open Recent remembers the last 20. |
| **Several documents at once** | One window each, as `libera *.docx` or from File ▸ Open. The file's type picks the editor. |
| **A start window** | `libera` on its own: new, open, recent, and where the payload came from. |
| **Crash recovery** | Unsaved edits are offered back the next time you open the document. |
| **Closing asks** | A window with unsaved changes offers Save, Don't Save or Cancel. |
| **A menu bar** | File, Edit, View, Window and Help, with the usual shortcuts. |
| **About** | Who wrote the editors, and under what licence: `File ▸ About` inside the editor, and `Help ▸ About Libera Suite` on Linux and Windows. macOS puts it in the application menu. |
| **Settings persist** | Theme, units, spellcheck language and the like are still set after a restart. |
| **Payload install** | From the origin, or from a local directory of built artifacts. Either way every artifact is verified against hashes shipped in the application. |

## Half-built

Nothing is in this state today. Every install channel is finished: the payload
origin is up, both Flatpak bundles are published, and one command installs
Libera Suite on either platform.

Linux has the same menu bar as macOS, drawn inside the window: File, Edit, View and Help. It has no keyboard shortcuts of its own, so the keys you already use go to the editor. `libera --launcher-install` puts Libera Suite in the launcher with its icon and file associations; the Flatpak does that for you.

## Not started

**No New shortcut on Linux.** Ctrl-N and Super-N do nothing. File ▸ New on the menu bar works, as does the New button in the start window you get from `libera` on its own, and the editor's own File tab.

**The application bundle is new and rough.** `build/macos-app.sh` builds `Libera.app`, which opens a document on a double-click, appears in *Open With*, and shows the Libera mark in the Dock. But the bundle is a launcher around the interpreter it was built with (nothing is embedded, signed or notarised), so it is not something you can hand to somebody else yet.

### In the editor

- **Password-protected documents.** Neither opening nor saving one.
- **Digital signatures.**
- **Mail merge.**
- **Plugins.** Disabled upstream in this fork, so the panel never appears.

### In the application

- **Tabs.** Windows exist and the Window menu lists them, but they cannot be merged into one window.
- **File locking.** Two copies of Libera Suite editing the same file will not notice each other.
- **A redistributable application.** The bundle runs from your own checkout, embeds no interpreter and no payload, and is neither signed nor notarised.
- **Drag and drop** onto the window or the Dock icon.
- **Automatic updates**, and **code signing and notarisation**. macOS will treat a Libera Suite you have built as software from an unidentified developer.
- **Offline help**, readable without a browser or a network. The Help menu opens this site; About works offline. See below.

### Elsewhere

- **Editing diagrams.** Diagrams opens `.vsdx` and shows it. The converter cannot write any Visio format, so there is nothing to save and no blank to start from.
- **PDF editing.** The payload has an editor for it. Nothing routes to it yet.
- **Collaboration, cloud storage, accounts, telemetry.** None of it is built. None of it is being worked on. [The roadmap](../develop/roadmap.md) says what each would look like if it arrived. [What leaves your machine](../index.md#what-leaves-your-machine) lists the application's entire network use.

## Notes on specific gaps

### Help

There is a **Help** menu, on every platform, and it opens this site in your
browser. No help lives *inside* the application, where it would be readable
with the machine offline. Upstream ships a full manual, and it documents ONLYOFFICE and
weighs 84 MB in eight languages, so Libera Suite does not ship it. Offline help
comes back once there is enough documentation of our own to ship.

### Spell checking

Libera Suite ships dictionaries for **English (US and UK), French, German, Spanish and Italian**: 9.5 MB, chosen because the full set is 327 MB. Adding a language is one line in `build/dictionaries.txt` and a payload rebuild.

A language with no dictionary is not an error: its words are simply treated as correct, which is what upstream's own desktop application does. Personal dictionaries (*Add to dictionary*) are not stored yet, so a word you add comes back next session.

How to set a document's language is in [Work with documents](documents.md#spell-checking).

### Your name in documents

Tracked changes and comments are attributed to a person, whose name is written
into the saved file. Libera Suite takes it from your account: the full name
macOS knows you by, the display name of your Windows account, or the full-name
field of your Unix account on Linux. There
is no way to change it yet. [Work with documents](documents.md#your-name-in-documents)
has the detail.

### Fonts

Libera Suite ships a core font set: Liberation, Carlito, Caladea, Open Sans and a few others, enough to render ordinary documents faithfully at 7 MB. The full set is 248 MB. A document that asks for a font outside that set, and outside the fonts installed on your machine, gets a substitute. Widening the set, particularly for CJK, is an open decision.

### Rendering fidelity

The layout engine is upstream's and is mature. Where you see something wrong, the likelier cause is our packaging (a missing font, a missing resource). That makes such reports especially useful; please send [feedback](../feedback.md) with the file.
