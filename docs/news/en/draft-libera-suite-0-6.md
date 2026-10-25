---
date: 2026-10-26
description: Libera Suite 0.6 speaks every language its applications do, lays out documents the way Word does when a font is missing, keeps Markdown headings, and spell-checks Dutch.
---

# Libera Suite 0.6: every language, and pages that break where Word breaks them

Libera Suite 0.6 is out. Its menus and windows now speak all 44 languages of its applications, and a document whose fonts you don't have lays out the way it does in Word.

Libera Suite is a free and open-source office suite for Windows, macOS and Linux: Libera Words for text, Libera Tables for spreadsheets, Libera Slides for presentations, and Libera Diagrams, a viewer for Visio drawings. It opens and saves the formats of Microsoft Office and LibreOffice, on your own computer, with no account or cloud service.

[Install Libera Suite](../main/install.md){ .md-button .md-button--primary }

Already using it? Quit Libera Suite if it's running, then run the installer or the install command again, or `brew upgrade libera` if you are using Homebrew. This version installs new components, a one-time download of about 90 MB.

## Every language

Since 0.5 the applications follow your system's language, but the menu bar, the start window and the dialogs did so only in French, German, Italian and Spanish. They now follow in all 44 languages, from Arabic to Vietnamese, and in Arabic, Hebrew and Urdu the start window reads right to left.

Only the French, German, Italian and Spanish translations have been reviewed by a native speaker. The others are drafts: if a word in your language is wrong or awkward, [tell us](../feedback.md), and your correction goes into the next version.

## Pages that break where Word breaks them

When a document asks for a font your computer doesn't have, Libera Suite now replaces it the way Word does:

- **Calibri, Cambria, Arial, Times New Roman and Courier New** get Carlito, Caladea and Liberation, which have the same widths, so the lines and pages break where they do in Word. On a Mac, Calibri used to go to whichever installed font looked closest, so the same document could lay out differently from one computer to the next.
- **A font Word would not know either** is set in Calibri's stand-in, as Word sets it in Calibri, where it used to get Liberation Sans. Two documents of our test set now have Word's page count.
- **Wingdings, Webdings and Symbol** characters are drawn as the symbols they stand for: a star, a check mark, a smiley, where a missing Wingdings used to show letters.

## Other changes

- **Markdown keeps its headings.** A Markdown file opened, edited and saved used to turn every heading into a bold paragraph.
- **Dutch spell-checking**, with the OpenTaal dictionary. Each dictionary now comes with its licence.
- **On Linux, the File menu shows its keys:** New, Open and Close show Ctrl-N, Ctrl-O and Ctrl-W.
- **An OpenDocument file without master styles keeps its styles**, where every paragraph used to open in the default style.

## What stays the same

- **Linux on arm64** still installs 0.4.1: there is no arm64 build of 0.6 yet.

[What works today](../main/status.md) lists what is built, what is half-built and what is not started yet.

## Tell us

Libera Suite is young, and every report counts. The most useful one is a document that comes out wrong, attached to your message with the output of `libera --diagnose`. [Feedback](../feedback.md) says how to reach us.

*Abilian*
