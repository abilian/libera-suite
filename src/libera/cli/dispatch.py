"""The argument parser, and which command each spelling reaches.

Separate from the commands themselves because the surface is the part that has
to stay still: `libera FILE...` opens documents, `libera` alone opens the
start window, and everything else is a flag. There is no `libera words` --
the file picks the editor.

Not `main.py`: `cli` re-exports `main`, and a module of that name would be
shadowed by the function.
"""

from __future__ import annotations

import argparse

from libera import logs
from libera.cli import commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="libera",
        description="Libera Suite -- a desktop office suite",
        epilog=(
            "libera FILE...    open documents, one window each\n"
            "libera            the start window: new, open, recent\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="*", help="documents to open, one window each")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="say more: -v what it is doing, -vv how, -vvv every request",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="errors only")

    # The payload: fetched, verified and installed separately from the wheel,
    # because it is ~120 MB of editor and native binaries. The start window
    # shows the same information; these are for scripts and for a machine with
    # no window system.
    payload_group = parser.add_argument_group("the editor payload")
    payload_group.add_argument(
        "--payload-status", action="store_true", help="where the payload resolved from"
    )
    payload_group.add_argument(
        "--payload-install",
        action="store_true",
        help="fetch, verify and install the payload",
    )
    payload_group.add_argument(
        "--payload-remove", action="store_true", help="delete the installed payload"
    )

    # Linux has no application bundle to carry this, so it is a command. The
    # Flatpak installs the same entry itself and says so rather than doing it
    # twice.
    launcher_group = parser.add_argument_group("the Linux launcher")
    launcher_group.add_argument(
        "--launcher-install",
        action="store_true",
        help="put Libera Suite in the launcher, with an icon and Open With",
    )
    launcher_group.add_argument(
        "--launcher-remove",
        action="store_true",
        help="take the desktop entry and its icon away",
    )
    payload_group.add_argument(
        "--from",
        dest="source",
        metavar="DIR_OR_URL",
        help="local directory of artifacts, or a base URL (default: the public origin)",
    )
    payload_group.add_argument(
        "--trust-manifest",
        action="store_true",
        help="accept the origin's manifest when the wheel ships none (unverified)",
    )

    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="print what a bug report needs: versions, payload, platform",
    )

    serve_group = parser.add_argument_group("serving without a window")
    serve_group.add_argument(
        "--serve",
        action="store_true",
        help="serve the editor over HTTP and print its URL; used by the tests",
    )
    serve_group.add_argument("--port", type=int, default=8765)
    serve_group.add_argument("--work", help="session state directory")
    serve_group.add_argument("--shot", help="where the page posts its own render")

    args = parser.parse_args(argv)
    logs.setup(args.verbose, quiet=args.quiet)

    # One command per run, and one table saying which spellings are commands.
    # The exclusivity check and the dispatch read the same rows, because they
    # were two lists of the same names and nothing made them agree.
    #
    # Checked here rather than made impossible by argparse, because
    # mutually_exclusive_group cannot span argument groups and the error it
    # gives is worse than this one.
    table = (
        ("--diagnose", args.diagnose, commands.cmd_diagnose),
        ("--payload-status", args.payload_status, commands.cmd_payload_status),
        ("--payload-install", args.payload_install, commands.cmd_payload_install),
        ("--payload-remove", args.payload_remove, commands.cmd_payload_remove),
        ("--launcher-install", args.launcher_install, commands.cmd_launcher_install),
        ("--launcher-remove", args.launcher_remove, commands.cmd_launcher_remove),
        ("--serve", args.serve, commands.cmd_serve),
    )
    chosen = [(flag, run) for flag, on, run in table if on]
    if len(chosen) > 1:
        names = " and ".join(flag for flag, _ in chosen)
        parser.error(f"{names} cannot be used together")
    if not chosen:
        return commands.cmd_open(args)

    flag, run = chosen[0]
    # The one command whose arity the parser cannot express: `file` is
    # variadic because opening documents is the default.
    if flag == "--serve" and len(args.file) != 1:
        parser.error("--serve takes exactly one document")
    return run(args)
