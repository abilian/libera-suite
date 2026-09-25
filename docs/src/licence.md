# Licence and attribution

## Two licences, because it is two artifacts

| | |
| :--- | :--- |
| **The host**: the `libera` package, everything in `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **The editor payload**: Euro-Office, and our patch queue against it | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

They arrive separately and stay separate. The host is a few hundred kilobytes of Python and JavaScript on PyPI; the payload is a download of about 120 MB, or the contents of a Flatpak bundle. Nothing of the payload is vendored into the wheel.

Run `libera --payload-status` to see the payload in use and the upstream revisions it was built from.

## What it is built from

Libera Suite is a desktop host around [**Euro-Office**](https://github.com/Euro-Office), an AGPL fork of **ONLYOFFICE**, which is developed by Ascensio System SIA. The editors, the document engine and the format support are theirs; the host, the packaging and the desktop integration are ours.

We are grateful for both. An office suite's hard part is the twenty years of reading other people's `.docx` files correctly. That part is inherited.

## Corresponding source

The payload is AGPL, which requires that you can get the source for what you are running, and that includes our modifications to it.

Every Libera Suite release writes three things into its payload manifest:

- the exact upstream revision of each repository it was built from, pinned by commit hash;
- the commit of Libera Suite itself;
- the repositories where both can be fetched.

Our changes to upstream are kept as a patch series against those pinned revisions, so "what did Libera Suite change?" has a short and checkable answer. See [The patch queue](develop/patches.md).

We point at public repositories; we do not serve tarballs.
