"""The argument parser, and which command each spelling reaches.

Separate from the commands themselves because the surface is the part that has
to stay still: `libera FILE...` opens documents and `libera` alone opens the
start window; everything else is a flag. There is no `libera words` --
the file picks the editor.

Not `main.py`: `cli` re-exports `main`, whose function would shadow a module
of that name.
"""

from __future__ import annotations

import argparse
import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from libera import launcher, logs, timeline
from libera.cli import commands
from libera.host import about, apps
from libera.payload import locate

if TYPE_CHECKING:
    from collections.abc import Callable


def main(argv: list[str] | None = None) -> int:
    timeline.mark("python")
    if _asks_for_convert_help(argv):
        _make_convert_help().print_help()
        return 0
    parser = _make_parser()
    args = parser.parse_args(argv)
    if args.config is not None:
        named = Path(args.config).expanduser().resolve()
        if not named.is_file():
            parser.error(f"--config: no such file: {named}")
        # Through the environment, so that every reader of the configuration,
        # and every process this one starts, reads the same file.
        os.environ["LIBERA_CONFIG"] = str(named)
    logs.setup(args.verbose, quiet=args.quiet)
    locate.make_state_dir_private()
    return _choose_command(parser, args)(args)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="libera",
        description="Libera Suite -- a desktop office suite",
        epilog=(
            "libera FILE...    open documents, one window each\n"
            "libera            the start window: new, open, recent\n"
            "libera --convert *.docx -t pdf    convert, with no window\n"
            "libera --convert --help           what converting takes\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="*", help="documents to open, one window each")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=about.format_version(),
        help="print the version and exit",
    )
    _add_common_options(parser)
    _add_payload_options(parser)
    _add_launcher_options(parser)
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="print what a bug report needs: versions, components, platform",
    )
    _add_convert_options(parser, shown=False)
    _add_serve_options(parser)
    return parser


def _asks_for_convert_help(argv: list[str] | None) -> bool:
    """`libera --convert --help`, in either order and however abbreviated.

    The converter's options are parsed by the one parser, so that `-t pdf`
    without `--convert` is still refused by name, but they are listed on a
    page of their own: in the general help they buried everything else.
    """
    probe = argparse.ArgumentParser(add_help=False)
    probe.add_argument("--convert", action="store_true")
    probe.add_argument("-h", "--help", action="store_true")
    known, _ = probe.parse_known_args(argv)
    return known.convert and known.help


def _make_convert_help() -> argparse.ArgumentParser:
    """Only ever printed, never parsed with: see `_asks_for_convert_help`."""
    parser = argparse.ArgumentParser(
        prog="libera --convert",
        description="Write each document in another format, with no window.",
        epilog=(
            "libera --convert *.docx -t pdf              a.pdf beside a.docx, ...\n"
            "libera --convert a.docx -o out/report.pdf   the format from -o\n"
            "libera --convert a.xlsx -t csv -o -         to standard output\n"
            "libera --convert *.odt -t docx --outdir converted\n"
            f"\n{_list_formats()}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="+", metavar="FILE", help="documents to convert")
    _add_convert_options(parser, shown=True)
    _add_common_options(parser)
    return parser


def _list_formats() -> str:
    """What each editor reads and writes, from the tables `--convert` checks
    against, so the page cannot offer a format the converter refuses."""
    lines = ["formats, by editor; the extension of each FILE picks the editor:"]
    for app in apps.ALL:
        writes = " ".join(sorted(app.ids_by_ext)) or "nothing: it only shows documents"
        for label, exts in (
            (f"{app.title:15} reads ", " ".join(sorted(app.opens))),
            (f"{'':15} writes", writes),
        ):
            lines.append(
                textwrap.fill(
                    exts,
                    width=79,
                    initial_indent=f"  {label} ",
                    subsequent_indent=" " * 25,
                )
            )
    return "\n".join(lines) + "\n"


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="say more: -v what it is doing, -vv how, -vvv every request",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="errors only")
    parser.add_argument(
        "-c",
        "--config",
        metavar="FILE",
        help=(
            "read FILE instead of the usual config.toml (also LIBERA_CONFIG);"
            " documents are then not handed to a Libera Suite already running"
        ),
    )


def _add_convert_options(parser: argparse.ArgumentParser, *, shown: bool) -> None:
    """Pandoc's spellings where pandoc has one: `-t` the format written, `-o`
    the file. No `-f`, which is pandoc's input format: here the extension
    decides that, as it decides the editor.

    Not `shown` in the general help, which names `--convert` and points here.
    """

    def help_(text: str) -> str:
        return text if shown else argparse.SUPPRESS

    group = (
        parser if shown else parser.add_argument_group("converting without a window")
    )
    if not shown:
        group.add_argument(
            "--convert",
            action="store_true",
            help="write each FILE in another format; see libera --convert --help",
        )
    group.add_argument(
        "-t",
        "--to",
        metavar="FORMAT",
        help=help_("the format, by extension: pdf, odt, docx, xlsx, csv, ..."),
    )
    group.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help=help_("for one document: where to write it, - for standard output"),
    )
    group.add_argument(
        "--outdir",
        metavar="DIR",
        help=help_("write into DIR rather than beside each document"),
    )


def _add_payload_options(parser: argparse.ArgumentParser) -> None:
    """The payload: the Euro-Office components, fetched, verified and installed
    separately from the wheel, because they are ~90 MB of JavaScript and native
    binaries. The help says components, which is what a user installs; the
    options keep the name the code and the scripts use. The start window shows
    the same information; these are for scripts and for a machine with no
    window system."""
    group = parser.add_argument_group("components (the payload)")
    group.add_argument(
        "--payload-status",
        action="store_true",
        help="where they are installed, and which version",
    )
    group.add_argument(
        "--payload-install",
        action="store_true",
        help="download them, check them and install them",
    )
    group.add_argument("--payload-remove", action="store_true", help="delete them")
    group.add_argument(
        "--from",
        dest="source",
        metavar="DIR_OR_URL",
        help="install from a directory of built files, or download from this URL",
    )
    group.add_argument(
        "--trust-manifest",
        action="store_true",
        help=(
            "in a copy installed from source, which has no checksums of its own:"
            " download without asking, checked against the download site's"
        ),
    )


def _add_launcher_options(parser: argparse.ArgumentParser) -> None:
    """Linux has no application bundle to hold this, so it is a command. The
    Flatpak installs the same entry itself. Where it makes no sense the options
    stay, so that they still answer with why, but the help leaves them out."""
    shown = launcher.explain_unsupported() is None

    def help_(text: str) -> str:
        return text if shown else argparse.SUPPRESS

    group = parser.add_argument_group("the Linux launcher")
    group.add_argument(
        "--launcher-install",
        action="store_true",
        help=help_("put Libera Suite in the launcher, with an icon and Open With"),
    )
    group.add_argument(
        "--launcher-remove",
        action="store_true",
        help=help_("take the desktop entry and its icon away"),
    )


def _add_serve_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("serving without a window")
    group.add_argument(
        "--serve",
        action="store_true",
        help="serve the editor over HTTP and print its URL; used by the tests",
    )
    group.add_argument("--port", type=int, help=f"default: {commands.SERVE_PORT}")
    group.add_argument("--work", help="session state directory")

    # Not part of that group: a window arms it too. The page photographs its
    # own canvas either way (host/server/bridge-page.js), which is the only
    # way to measure what the *shipped* web engine drew -- Chromium, which
    # --serve and the e2e tier use, is not WKWebView, WebKitGTK or WebView2.
    group = parser.add_argument_group("checking what was drawn")
    group.add_argument(
        "--shot",
        help="where each window's page posts its own render (--serve: the one page's)",
    )


def _choose_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> Callable[[argparse.Namespace], int]:
    """The one command this run asked for: a flag, or opening documents.

    Checked here rather than made impossible by argparse, because
    mutually_exclusive_group cannot span argument groups and the error it
    gives is worse than these.
    """
    chosen = _find_command_flags(args)
    if len(chosen) > 1:
        names = " and ".join(flag for flag, _ in chosen)
        parser.error(f"{names} cannot be used together")
    flag, run = chosen[0] if chosen else (None, commands.open_documents)

    # Options that belong to one command, which every other ignored without a
    # word: `libera --from ./dist` opened the start window, and offered to
    # download from the default origin.
    owned = (
        ("--from", "--payload-install", args.source is not None),
        ("--trust-manifest", "--payload-install", args.trust_manifest),
        ("--port", "--serve", args.port is not None),
        ("--work", "--serve", args.work is not None),
        ("--to", "--convert", args.to is not None),
        ("--output", "--convert", args.output is not None),
        ("--outdir", "--convert", args.outdir is not None),
    )
    for option, owner, given in owned:
        if given and owner != flag:
            parser.error(f"{option} goes with {owner}")

    # The one command whose arity the parser cannot express: `file` is
    # variadic because opening documents is the default.
    if flag == "--serve" and len(args.file) != 1:
        parser.error("--serve takes exactly one document")
    if flag == "--convert":
        _check_convert(parser, args)
    return run


def _check_convert(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """What `--convert` needs, which is mostly what to call the result."""
    args.file = commands.expand_wildcards(args.file)
    if not args.file:
        parser.error("--convert needs at least one document")
    if args.output is None and args.to is None:
        parser.error("--convert needs -t FORMAT, or -o FILE")
    if args.output is None:
        return
    if len(args.file) > 1:
        parser.error("-o names one file; for several documents, use -t and --outdir")
    if args.outdir is not None:
        parser.error("-o and --outdir cannot be used together")
    if args.to is None and not Path(args.output).suffix:
        parser.error(f"no format in {args.output!r}: add -t FORMAT")


def _find_command_flags(
    args: argparse.Namespace,
) -> list[tuple[str, Callable[[argparse.Namespace], int]]]:
    """Every command flag given, with the command it runs.

    One table saying which spellings are commands, read by both the
    exclusivity check and the dispatch: they were two lists of the same names
    with nothing to make them agree. Built at the call, so a command replaced in
    `commands` is the one that runs.
    """
    table = (
        ("--diagnose", args.diagnose, commands.diagnose),
        ("--payload-status", args.payload_status, commands.show_payload_status),
        ("--payload-install", args.payload_install, commands.install_payload),
        ("--payload-remove", args.payload_remove, commands.remove_payload),
        ("--launcher-install", args.launcher_install, commands.install_launcher),
        ("--launcher-remove", args.launcher_remove, commands.remove_launcher),
        ("--serve", args.serve, commands.serve),
        ("--convert", args.convert, commands.convert_documents),
    )
    return [(flag, run) for flag, on, run in table if on]
