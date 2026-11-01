---
date: 2026-10-01
description: Libera Suite, a free office suite for Linux, Windows and macOS, enters public beta. It opens and saves the Microsoft Office and OpenDocument formats, with no account and no online service.
---

# Libera Suite enters public beta

**Libera Suite** is a free office suite for Linux, Windows and macOS. It includes a word processor, a spreadsheet, a presentation program and a viewer for Visio files. It runs on your computer, with no account, no online service and no telemetry. It opens and saves the Microsoft Office and OpenDocument formats. Its public beta starts today.

[Install Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words, with a document open: the editor's toolbar in the Libera Words purple, and a laid-out page below it.](../assets/words.png)

## Four applications

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Text documents | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Spreadsheets | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentations | `.pptx` `.odp` |
| **Libera Diagrams** | A viewer for Visio drawings | `.vsdx` |

A Word, Excel or PowerPoint file opens with its layout: fonts, images, tables and tracked changes included. Saving produces a file in the same format, which Microsoft Office and LibreOffice open like any other.

The four applications share a start window with your recent documents, spell checking in five languages, PDF export, printing, and recovery of your work after a crash.

## Free software, at no cost

Libera Suite asks for no licence and no subscription. You can install it on as many computers as you like and keep it for as long as you like. It depends on no server of ours to work.

It is free software: anyone can read its source code, change it and share it. The application is under the Apache License 2.0 and the Euro-Office components under the GNU AGPL v3. [Licence and attribution](../licence.md) explains how to get the exact source code of each version.

## Your documents stay on your computer

Libera Suite reads and writes your documents on your disk and sends them nowhere. It sends us no information about you, your documents or the way you use it.

It goes online to download the Euro-Office components when you install it. [The documentation lists](../index.md#what-leaves-your-machine) every connection it makes, and the source code lets you check.

## How to install it

- **Linux** (x86_64 and arm64): one command in the terminal, which installs a Flatpak package when Flatpak is present.
- **macOS** (Apple Silicon): one command in the terminal, with Homebrew or without it.
- **Windows** 10 and 11 (x64): an installer, with no administrator rights needed.

The [install page](../main/install.md) gives the commands.

## The limits of the beta

Each document has its own window, with no tabs. Nothing yet stops two windows from editing the same document: the last one to save overwrites the other's work. Diagrams reads Visio files but cannot save them. The Windows installer is not signed yet, so Windows shows a warning when you open it. [The status page](../main/status.md) gives the full list and is kept up to date.

## Your feedback

The layout engine is well proven: when a document looks wrong in Libera Suite, the cause is most often in our packaging, a missing font or resource. Those defects are quick to fix, once we see them. The most useful feedback is therefore a document that looks wrong, attached to your message.

If you choose software for an organisation, tell us which features it would need to adopt Libera Suite.

[Feedback](../feedback.md) explains how to write to us.

## Who develops it

Libera Suite is developed by [Abilian](https://abilian.com), a French free software company. It is built on the components of [Euro-Office](https://github.com/Euro-Office), a fork of [ONLYOFFICE](https://www.onlyoffice.com/), the software of Ascensio System SIA. Those components provide the document engine and the format support. Abilian wrote the desktop application that hosts them: the windows, the menus, opening and saving files, and the packaging.

We build the Euro-Office components from their source, at fixed revisions. The fixes we apply to them are [published and explained](../develop/patches.md).

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio and Windows are trademarks of the Microsoft group of companies. LibreOffice is a trademark of The Document Foundation. ONLYOFFICE is a trademark of Ascensio System SIA. Other names are trademarks of their respective owners. Libera Suite is not affiliated with or endorsed by any of them.
