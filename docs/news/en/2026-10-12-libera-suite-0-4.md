---
date: 2026-10-12
description: Libera Suite 0.4 marks a document already open elsewhere, in Libera Suite or in LibreOffice, renders OpenDocument files more faithfully, and adds drag and drop, a personal dictionary and conversion from the command line.
---

# Libera Suite 0.4: safer in a shared folder, more faithful to OpenDocument

Libera Suite 0.4 is out. It protects a document someone else has open, in Libera Suite or in LibreOffice. Its editors read and write the OpenDocument formats more accurately.

[Update Libera Suite](../main/install.md#update){ .md-button .md-button--primary }

Quit Libera Suite, then run the installer or the install command again, or `brew upgrade libera`. This version installs new editors, a one-time download of about 100 MB.

## Document locking

Until now, nothing stopped two windows from editing the same document: the last one to save wrote over the other's work. The beta listed this among its limits. Version 0.4 removes it between two windows of Libera Suite, and between Libera Suite and LibreOffice. Microsoft Office does not see these locks yet, so a document open in Word is still exposed.

- **Libera Suite sets a lock in LibreOffice's format.** When it opens a document, it creates beside it the small lock file LibreOffice uses. It also respects the locks LibreOffice sets. A document already open elsewhere opens *locked for editing*: you can read it and change it, but saving asks for another place. The original stays untouched.
- **Opening a document again brings its window forward**, without opening a second one.
- **A window shows unsaved changes**: a dot in the close button on macOS, a `*` before the title on Linux and Windows.

## Better fidelity to the OpenDocument formats

The editors in 0.4 include **68 fixes for the OpenDocument formats** (`.odt`, `.ods`, `.odp`), each found with LibreOffice's own test documents. Two CSV defects are gone as well. An emoji prevented a CSV from being saved; a large CSV lost one character in 500,000 when read.

## Notice of new versions

New in 0.4: at most once a day, Libera Suite reads the number of the latest version from our download server. If it is newer than yours, it tells you once, with the steps for the way you installed it. It downloads nothing and sends nothing about you or your documents; offline, it does nothing. The line `check_updates = false` in the [configuration file](../guide/documents.md#your-name-in-documents) turns it off.

## Other changes

- **Drag and drop.** A document dropped on a window opens; a picture dropped on a document is inserted.
- **The personal dictionary.** A word added with *Add to dictionary* is kept, for every document and every language.
- **Your name in tracked changes and comments**, set with `user_name` in the configuration file.
- **Ctrl-N, Ctrl-O and Ctrl-W** on Linux and Windows.
- **Print** asks where to save the PDF, starting in the document's folder.
- **Conversion from the command line**: `libera --convert *.docx -t pdf` writes a PDF beside each document, without opening a window.
- **The About window** shows the installed version, the first thing to give in a bug report.

The remaining limits, among them the lack of tabs and a Windows installer that is not yet signed, are listed on [the status page](../main/status.md).

## Report problems

The most useful report is still a document that comes out wrong, attached to your message with the output of `libera --diagnose`. [Feedback](../feedback.md) says how to reach us.

*Abilian*
