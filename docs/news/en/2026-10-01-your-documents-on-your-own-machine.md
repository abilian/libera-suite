---
date: 2026-10-01
description: Libera Suite, a free office suite for Windows, macOS and Linux, is in beta. It opens Word, Excel and PowerPoint files, needs no account, and keeps your documents on your own computer.
---

# Libera Suite: your documents, on your own machine

Today we are opening the beta of **Libera Suite**, a free office suite for Windows, macOS and Linux. Write letters and reports, keep your figures in a spreadsheet, prepare a presentation, all on your own computer, with your own files. There is no account to create and no subscription to pay.

[Install Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words, with a document open: the editor's toolbar in the Libera Words purple, and a laid-out page below it.](../assets/words.png)

## It opens what people send you

Everybody sends `.docx`. Libera Suite opens it, and the `.xlsx` and `.pptx` that come with it, and lays them out the way their authors saw them: fonts, images, tables and tracked changes included. When you save, you get a file in the same format, which your colleagues open in Microsoft Office or LibreOffice like any other.

The credit goes to a document engine that has spent twenty years being handed other people's files. Libera Suite runs that engine on your computer.

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Text documents | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Spreadsheets | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentations | `.pptx` `.odp` |
| **Libera Diagrams** | A viewer for Visio drawings | `.vsdx` |

You also get the rest of an office suite: a start window with your recent documents, spell checking in five languages, PDF export, printing, and a recovery that offers your work back if the computer stops under you.

## Free, and yours to keep

There is no licence fee and no monthly bill. Install it on as many computers as you like, and keep it as long as you like. No server has to stay paid for it to keep working, and nobody can switch it off from a distance.

Libera Suite is free software: anyone may read its source code, change it and share it. The application is under the Apache License 2.0 and the editors under the GNU AGPL v3. [Licence and attribution](../licence.md) says how to get the exact source of any release.

## Your documents stay on your computer

Libera Suite reads and writes your documents on your disk, with software on your disk, and never uploads them. There is no account and no cloud behind it, and no telemetry, analytics or crash reporting: it sends us nothing about you, your documents or the way you use it.

It goes online to download its editors when you install it. [The documentation lists](../index.md#what-leaves-your-machine) every connection it makes, and the source is public, so you can check.

## A beta, with its gaps in plain view

Libera Suite runs on **Windows 10 and 11 (x64)**, **macOS (Apple Silicon)** and **Linux (x86_64 and arm64)**. Windows gets an installer, Linux a single Flatpak file with the editors inside it, and macOS one command in the terminal.

The known gaps are [published in full](../main/status.md) and kept current. Each document has its own window, as there are no tabs yet. Nothing stops two windows from editing the same document, and one of them will lose its changes. Diagrams reads Visio files and cannot save them. Windows warns about the installer until it is signed.

## Tell us what breaks

The most useful thing you can send us is **a document that comes out wrong, attached**. The engine is mature, so when a file looks wrong the cause is far more likely to be on our side: a font we did not ship, a resource we failed to serve. We fix those quickly, once somebody shows us one.

If you choose software for an organisation, tell us **what it would need** to switch. Today is the cheapest moment to shape the answer.

[Install](../main/install.md) takes a minute, and [Feedback](../feedback.md) says how to reach us.

## Who makes it

Libera Suite is made by [Abilian](https://abilian.com), a French company that builds free software. Its editors come from [Euro-Office](https://github.com/Euro-Office), itself a fork of [ONLYOFFICE](https://www.onlyoffice.com/) by Ascensio System SIA. The document engine and the format support, the hard part of an office suite, are theirs, and we reimplemented none of it. We built the desktop application around them: the windows, the menus, opening and saving, and the packaging.

The engine stays upstream's, built from source at exact revisions with [a short patch queue](../develop/patches.md) of our own. The part we maintain is small, and a small team can commit to it for the long run.

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio and Windows are trademarks of the Microsoft group of companies. LibreOffice is a trademark of The Document Foundation. ONLYOFFICE is a trademark of Ascensio System SIA. Other names are trademarks of their respective owners. Libera Suite is not affiliated with or endorsed by any of them.
