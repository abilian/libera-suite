# Using Libera Suite

Libera Suite opens a document in a window and lets you edit and save it. Words, Tables and Slides all work that way; Diagrams opens Visio files to read.

Start at [Install](../main/install.md). These three pages are meant to be read in order:

1. [Install](../main/install.md): getting it onto your machine, in one command.
2. [Work with documents](documents.md): opening, saving, exporting, printing.
3. [What works today](../main/status.md): what is built, plus the problems we already know about.

Each editor has its own colour. Everything else about the window is the same:

![Libera Tables holds an empty spreadsheet, and its toolbar is the Libera Tables teal.](../assets/tables.png)

![Libera Slides holds a title slide, and its toolbar is the Libera Slides gold.](../assets/slides.png)

## The shape of it

Libera Suite is two pieces that arrive separately.

**The application** is a small Python package. It is a few hundred kilobytes: the window, the command line, and the host that the editor talks to.

**The editors** are everything else: the document engine, the editors themselves, the fonts. The application calls this the *payload*. It is about 110 MB compressed on macOS and 120 MB on Linux. You fetch or install it once; the Python package does not include it.

They are versioned separately. The application checks that the payload it finds is the one it expects. A fix to the application therefore does not mean downloading the editors again.

The Windows installer and the Linux Flatpak contain both pieces. Every other way of installing puts the application in place first, then downloads the editors once.

## What it is not

Libera Suite talks to no server, needs no account and never uploads your documents. The editor runs as local web content served over `127.0.0.1` to a window on your own machine. There is no collaboration, cloud storage or telemetry, because none of it is built.
