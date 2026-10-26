# Command line

Libera Suite is used from its windows, but a terminal reaches a few things no window offers: converting a folder of documents in one go, installing the components on a machine you reach over SSH, the report a bug needs.

The command is `libera`, on Linux and macOS. Installed as a Flatpak it is `flatpak run eu.liberasuite.Libera`, followed by the same options. On Windows it is `libera-cli.exe`, in the folder Libera Suite was installed in; it is not on the `PATH`.

## Open

| | |
| :--- | :--- |
| `libera` | the start window: new, open, recent |
| `libera FILE...` | each document in a window of its own; the file decides the application. [More](documents.md#open) |

## Convert

| | |
| :--- | :--- |
| `libera --convert FILE... -t FORMAT` | each document written in `FORMAT`, beside it, with no window. `FORMAT` is an extension: `pdf`, `odt`, `docx`, `xlsx`, `csv`... |
| `-o FILE` | for one document: the file to write, its format taken from its extension unless `-t` says otherwise. `-o -` writes to standard output |
| `--outdir DIR` | write into `DIR` instead of beside each document |

[Converting from the command line](documents.md#from-the-command-line) gives examples.

## The components

| | |
| :--- | :--- |
| `libera --payload-install` | download, check and install the components. `--from DIR` installs them from a folder instead. [More](../main/alt-install.md#the-editors) |
| `libera --payload-status` | where the components are, their version, and the [source](../licence.md#corresponding-source) they were built from |
| `libera --payload-remove` | delete them. [More](../main/install.md#uninstall) |

## Applications menu and Open With

| | |
| :--- | :--- |
| `libera --launcher-install` | put Libera Suite among your applications, with *Open With*: in the applications menu on Linux ([more](../main/alt-install.md#a-launcher-entry-on-linux)), as `Libera.app` in your Applications folder on macOS ([more](../main/alt-install.md#a-double-clickable-application-on-macos)). |
| `libera --launcher-remove` | take it out again |

The Flatpak, the Windows installer and, on macOS, the install script do this themselves.

## When something goes wrong

| | |
| :--- | :--- |
| `libera --diagnose` | everything a bug report needs, on one screen. [More](../main/install.md#if-something-goes-wrong) |
| `libera --version` | the application's version and the components' |
| `-v`, `-vv`, `-vvv` | say what it is doing; how; every request to the components |
| `-q` | errors only |

`libera --help` lists every option, and `libera --convert --help` those of the converter.
