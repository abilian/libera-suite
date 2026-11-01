---
date: 2026-10-20
description: Libera Suite 0.5 speaks your language, shows documents in the fonts installed on your computer, opens them sooner, and cleans up after its own updates.
---

# Libera Suite 0.5: in your language, with your fonts

Libera Suite 0.5 is out. It now follows your system's language, and shows a document in the fonts installed on your computer.

Libera Suite is a free and open-source office suite for Windows, macOS and Linux: Libera Words for text, Libera Tables for spreadsheets, Libera Slides for presentations, and Libera Diagrams, a viewer for Visio drawings. It opens and saves the formats of Microsoft Office and LibreOffice, on your own computer, with no account or cloud service.

[Install Libera Suite](../main/install.md){ .md-button .md-button--primary }

Already using it? Quit Libera Suite if it's running, then run the installer or the install command again, or `brew upgrade libera` if you are using Homebrew. This version installs new components, a one-time download of about 90 MB.

## In your language

Until now, Libera Suite's UI spoke only English. Its four applications now follow your system's language, and the line `ui_language` in the [configuration file](../guide/documents.md#your-name-in-documents) lets you choose another. In French, German, Italian and Spanish, the menu bar, the start window and the dialogs follow too, and Help opens this documentation in that language.

A new document starts from a blank page for your language and region: A4 paper everywhere but the United States, where it used to be US Letter for everyone, and spell-checked in your language.

## With your fonts

A document set in a font you have installed now shows in it, on screen and in its PDF, where it used to get a substitute. Libera Suite lists your fonts when it installs its components, and again whenever you install or remove one; nothing is copied. The line `installed_fonts = false` keeps to the fonts Libera Suite ships.

## Sooner on screen

A document's window now opens at once, while the document is still being prepared. On our Mac, a small text document is on screen about a second sooner. A file Libera Suite cannot read now opens a window that says so, then closes it.

## Other changes

- **Updated components**, from October, with the upstream fixes made since the previous version.
- **A stricter security policy.** The components can load or send nothing anywhere but Libera Suite itself. The exception is a picture a document links to by its web address, which is fetched as in any office suite.
- **Macros are off, and kept.** The components' macros are JavaScript and run none of the VBA in documents from Microsoft Office, so they are turned off. A document's macros are kept: saving a `.docm`, `.xlsm` or `.pptm` leaves its VBA as it was, and Libera Words now opens and saves `.docm`.
- **Old components are removed.** Each update used to leave the previous version on disk, about 400 MB each. One that nothing has used for four weeks is now removed.
- **Fixes.** The font menu draws each name whole. An `.xlsb` workbook opens, where it used to open as an empty presentation. On macOS, quitting with Cmd-Q no longer leaves documents locked. On Windows, the Recent list shows each document's name, and no longer loses its entries.

## What goes away

- **Saving as `.xlsb`.** Writing one crashed on Linux. Save as `.xlsx` instead; Excel opens both.
- **Linux on arm64, for now.** There is no arm64 build of 0.5. The install script installs 0.4.1 on those machines; a later version builds arm64 again.

[What works today](../main/status.md) lists what is built, what is half-built and what is not started yet.

## Tell us

Libera Suite is young, and every report counts. The most useful one is a document that comes out wrong, attached to your message with the output of `libera --diagnose`. [Feedback](../feedback.md) says how to reach us.

*Abilian*
