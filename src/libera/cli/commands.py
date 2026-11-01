"""One function per thing `libera` can be asked to do.

Each raises what it could not do, and `run` says it: somebody who typed a
filename wrong gets a sentence saying what went wrong, never a traceback. Only
the errors named in `run` are said that way; anything else is a bug, and keeps
its traceback.

`dispatch` chooses between them; nothing here knows how the arguments were
parsed.
"""

from __future__ import annotations

import glob
import platform
import shutil
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

from libera import gui, launcher, payload as payload_mod
from libera.host import apps, convert, instance, opening, server, session
from libera.host.convert import ConversionError
from libera.host.instance import BusyError
from libera.host.session import NotReadyError
from libera.payload import PayloadError, fonts, leftovers

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable

# Where `libera --serve` listens unless told otherwise.
SERVE_PORT = 8765


def _is_interactive() -> bool:
    """Whether a terminal is there: to answer a question, and to have read what
    was printed.

    `sys.stdin` is None in the windowed Windows build -- its
    entry point gives stdout and stderr a file, which print() needs, and
    leaves stdin alone -- so `sys.stdin.isatty()` raised AttributeError there,
    which is the silent exit the window below exists to prevent.
    """
    return sys.stdin is not None and sys.stdin.isatty()


class CommandError(Exception):
    """What a command could not do, in a sentence for whoever asked."""


class CannotStartError(CommandError):
    """Opening documents failed after a window was known to be possible: said
    in one as well when there is no terminal."""


# The heading when no more particular one applies.
CANNOT_START = "Libera Suite could not start"


def run(command: Callable[[argparse.Namespace], None], args: argparse.Namespace) -> int:
    """Run a command, and the exit status: 1 having said why it failed."""
    try:
        command(args)
    except CannotStartError as e:
        _refuse(CANNOT_START, [str(e)])
        return 1
    except (CommandError, PayloadError, ConversionError, NotReadyError) as e:
        _complain(e)
        return 1
    return 0


def _complain(message: object) -> None:
    print(f"libera: {message}", file=sys.stderr)


def _refuse(heading: str, paragraphs: list[str]) -> None:
    """Say why `libera` will not start, where somebody will see it.

    On stderr, and in a window as well when there is no terminal: launched
    from an icon or a file manager, stderr goes nowhere and the icon flashes
    and vanishes. Only for what comes after `gui.explain_why_no_window`, because a
    machine that cannot open a window cannot be told in one.
    """
    _complain("\n\n".join([f"{heading}.", *paragraphs]))
    if not _is_interactive():
        gui.show_problem(heading, paragraphs)


def install_launcher(_args: argparse.Namespace) -> None:
    why = launcher.explain_unsupported()
    if why:
        raise CommandError(why)
    for path in launcher.install():
        print(f"wrote {path}")
    print("Libera Suite is among your applications, and opens what it reads.")


def remove_launcher(_args: argparse.Namespace) -> None:
    why = launcher.explain_unsupported()
    if why:
        raise CommandError(why)
    gone = launcher.remove()
    if not gone:
        print("nothing to remove: it was not among your applications")
        return
    for path in gone:
        print(f"removed {path}")


def show_payload_status(_args: argparse.Namespace) -> None:
    record = _print_payload(payload_mod.resolve())
    _print_old_payloads()
    # Corresponding source, per AGPL. A user holding this binary is entitled to
    # know exactly which revisions it was built from.
    source = record.get("source") or {}
    if not source:
        print("source:    not recorded (local build)")
        return
    print("source:")
    for url in source.get("repositories", []):
        print(f"  {url}  @ {source.get('libera_commit', '?')}")
    for repo, sha in sorted((source.get("pins") or {}).items()):
        print(f"  {source.get('upstream', 'upstream')}/{repo} @ {sha}")


def _print_old_payloads() -> None:
    """What 0.6 and earlier downloaded, which nothing reads any more."""
    old = leftovers.find()
    if not old:
        return
    print("downloaded by earlier versions, which this one does not use:")
    for root in old:
        print(f"  {root.name:<8} {leftovers.measure(root) / 1e6:4.0f} MB")
    print("  remove them with:  libera --payload-remove")


def _print_payload(p: payload_mod.Payload) -> dict:
    """Where the payload is and what it is, as --payload-status and --diagnose
    both say it. Returns its record, for what each says after.

    The first line is an interface: runtime-smoke.py, released-gui.sh and
    windows-app.sh read the root off `payload:`, and lost it once when these
    labels were respelled.
    """
    record = p.read_record()
    print(f"payload:   {p.root}")
    print(f"found via: {p.origin}")
    print(f"version:   {record.get('payload_version', 'unknown (local build)')}")
    platform_, fonts = record.get("platform", "?"), record.get("font_set", "?")
    print(f"platform:  {platform_}  fonts: {fonts}")
    print(f"built:     {record.get('built', '?')}")
    print(f"x2t:       {'present' if p.x2t.is_file() else 'MISSING'}")
    return record


def remove_payload(_args: argparse.Namespace) -> None:
    """Delete the payloads 0.6 and earlier downloaded: this version installs
    its components as packages, and reads none of them."""
    old = leftovers.find()
    if not old:
        print("nothing to remove: no earlier version left a payload here")
        return
    names = ", ".join(root.name for root in old)
    print(f"removed {names} ({leftovers.remove() / 1e6:.0f} MB)")


def _resolve_payload() -> payload_mod.Payload:
    try:
        return payload_mod.resolve()
    except PayloadError as e:
        raise CannotStartError(e) from e


def serve(args: argparse.Namespace) -> None:
    """Serve the editor without a window. Used by the regression harness."""
    p = payload_mod.resolve()
    font_index = fonts.choose(p)

    document = Path(args.file[0]).expanduser().resolve()
    if not document.is_file():
        msg = f"no such file: {document}"
        raise CommandError(msg)

    # Beside the windowed application's sessions: sharing the parent makes
    # them share a Recent list.
    work = (
        Path(args.work).expanduser()
        if args.work
        else payload_mod.get_sessions_dir() / "serve"
    )
    served = session.Session(
        payload=p.root,
        work=work,
        document=document,
        fonts=font_index,
        shot=Path(args.shot).expanduser() if args.shot else None,
    )
    session.configure(served)
    port = SERVE_PORT if args.port is None else args.port
    opening.open_document(served, document)
    try:
        httpd = server.make_server(port, served)
    except OSError as e:
        msg = f"cannot listen on port {port}: {e.strerror}"
        raise CommandError(msg) from e
    print(server.make_editor_url(port, served, document.name), flush=True)
    httpd.serve_forever()


def expand_wildcards(names: list[str]) -> list[str]:
    """`*.docx` as a POSIX shell would have expanded it, on Windows only.

    cmd.exe and PowerShell pass it on as typed. Anywhere else the shell has
    expanded it already, and expanding again would misread a file whose name
    has a `*` in it. A pattern that matches nothing stays as typed, so it is
    reported as a missing file.
    """
    if sys.platform != "win32":
        return names
    return [found for name in names for found in sorted(glob.glob(name)) or [name]]


# One conversion: (the document, where it goes or None for standard output,
# the extension of the format it is written in).
Conversion = tuple[Path, Path | None, str]


def plan_conversions(args: argparse.Namespace) -> list[Conversion]:
    """Every conversion `--convert` was asked for, or the first reason not to.

    All checked before any is made: a typo in the format, or two documents
    that would land on one file, is cheaper to say before a hundred
    conversions than after.
    """
    plan: list[Conversion] = []
    for name in args.file:
        src = Path(name).expanduser()
        if not src.is_file():
            msg = f"no such file: {src}"
            raise CommandError(msg)
        ext = (args.to or Path(args.output).suffix).lstrip(".").lower()
        _check_writes(apps.choose_for(src), src, ext)
        plan.append((src, _choose_target(args, src, ext), ext))

    targets = [t.resolve() for _, t, _ in plan if t is not None]
    for src, target, _ in plan:
        if target is None:
            continue
        if target.exists() and target.samefile(src):
            msg = f"{src} would be written over itself"
            raise CommandError(msg)
        if targets.count(target.resolve()) > 1:
            msg = f"several documents would be written to {target}"
            raise CommandError(msg)
    return plan


def _check_writes(app: apps.App, src: Path, ext: str) -> None:
    if not app.editable:
        msg = f"{src.name}: {app.title} only shows documents, and writes none"
        raise CommandError(msg)
    if ext not in app.ids_by_ext:
        writes = ", ".join(e for _, e in app.save_formats)
        msg = f"{src.name}: {app.title} cannot write .{ext}; it writes {writes}"
        raise CommandError(msg)


def _choose_target(args: argparse.Namespace, src: Path, ext: str) -> Path | None:
    if args.output == "-":
        return None
    if args.output is not None:
        return Path(args.output).expanduser()
    folder = Path(args.outdir).expanduser() if args.outdir else src.parent
    return folder / f"{src.stem}.{ext}"


def convert_documents(args: argparse.Namespace) -> None:
    """Write each document in another format, with no window: `--convert`.

    The conversions a Save makes -- x2t into Editor.bin, then out to the
    format asked for -- so the file is the one Save As would have written.
    Each document has a session of its own in a scratch directory, registered
    nowhere: no Recent list, no lock file, nothing left behind. A document
    that fails is reported and the others go on, and the command fails at
    the end if any did.
    """
    plan = plan_conversions(args)
    p = payload_mod.resolve()
    font_index = fonts.choose(p)
    if args.outdir:
        Path(args.outdir).expanduser().mkdir(parents=True, exist_ok=True)

    failed = 0
    with tempfile.TemporaryDirectory(prefix="libera-convert-") as scratch:
        for index, (src, target, ext) in enumerate(plan):
            try:
                work = Path(scratch) / str(index)
                staged = _convert_one(p.root, font_index, work, src, ext)
            except ConversionError as e:
                _complain(f"{src}: {e}")
                failed += 1
                continue
            if target is None:
                sys.stdout.buffer.write(staged.read_bytes())
                sys.stdout.flush()
            else:
                # Converted aside, then moved: a failure never leaves half a
                # file where the old one was.
                shutil.move(staged, target)
    if failed:
        msg = f"{failed} of {len(plan)} documents could not be converted"
        raise CommandError(msg)


def _convert_one(
    payload: Path, font_index: Path, work: Path, src: Path, ext: str
) -> Path:
    converting = session.Session(
        payload=payload, work=work, document=src, fonts=font_index
    )
    convert.convert_to_editor_bin(converting, src)
    converting.out_dir.mkdir(parents=True)
    staged = converting.out_dir / f"{src.stem}.{ext}"
    fmt = converting.editor.ids_by_ext[ext]
    convert.export(converting, staged, fmt, src)
    return staged


def diagnose(_args: argparse.Namespace) -> None:
    """What a bug report needs, in one place.

    `-v` covers what is happening now; this covers "it did something odd an
    hour ago", which is most of what a beta tester has to tell us. It fits on
    one screen and runs only when asked: nothing here leaves the machine unless
    somebody copies it.
    """
    print(f"libera    {version('libera')}")
    print(f"python     {sys.version.split()[0]}")
    print(f"platform   {platform.platform()}  {platform.machine()}")

    window = gui.explain_why_no_window()
    print(f"window     {'ok' if window is None else 'NOT AVAILABLE'}")

    if launcher.explain_unsupported() is None:
        # Inline: a local would have taken the name `state` first, and further
        # down that is the state directory.
        print(
            f"launcher   {'installed' if launcher.is_installed() else 'not installed'}"
            f"  ({launcher.get_entry_path()})"
        )

    try:
        p = payload_mod.resolve()
    except PayloadError as e:
        print(f"payload    MISSING\n  {e}")
        return

    _print_payload(p)
    editors = sorted(d.name for d in (p.root / "web-apps" / "apps").glob("*editor"))
    print(f"  editors  {', '.join(editors) or 'none'}")

    state = payload_mod.get_state_dir()
    sessions = sorted(payload_mod.get_sessions_dir().glob("*/unsaved.json"))
    print(f"state      {state}")
    print(f"  unsaved  {len(sessions)} session(s) holding edits that were never saved")


def open_documents(args: argparse.Namespace) -> None:
    """Open documents, or the start window when none are named.

    The file decides which editor it gets: see
    host/apps.py. There is no `libera words` any more for the same reason
    there is no `open -a TextEdit` in most people's muscle memory -- you open
    the document.
    """
    # The arguments first: a name that is not a file is the cheapest thing to
    # be wrong about, the only one of the three that retyping fixes.
    # Answering `libera reprot.docx` with a paragraph about GTK -- which is
    # what checking the window first did on any Linux box whose virtualenv
    # cannot see PyGObject -- buries the typo under the environment.
    documents = []
    for name in args.file:
        document = Path(name).expanduser()
        if not document.is_file():
            msg = f"no such file: {document}"
            raise CommandError(msg)
        documents.append(document.resolve())

    # A Libera Suite already running takes them, in a window of its own, and
    # this process is done: see `host/instance.py` for why there is only ever
    # one. Before the window and the payload checks, which the running one has
    # already passed.
    # Only to one running with this launch's configuration.
    if instance.hand_off(documents):
        return

    # Then the window, and only then the payload: a machine that cannot open
    # one has no use for 116 MB of editor.
    cannot = gui.explain_why_no_window()
    if cannot:
        raise CommandError(cannot)

    p = _resolve_payload()
    _run(p, documents, Path(args.shot).expanduser() if args.shot else None)


def _run(
    p: payload_mod.Payload, documents: list[Path], shot: Path | None = None
) -> None:
    """The application, as the one instance; or the documents handed to the
    instance another launch has just become."""
    # The one place the GUI is imported: pywebview and, on a Mac, AppKit cost
    # a third of a second, and only this command opens a window.
    from libera.host import app

    try:
        held = instance.become(documents)
        if held is None:
            return
        with held:
            app.run(p.root, payload_mod.get_sessions_dir(), documents, shot=shot)
    except (NotReadyError, BusyError) as e:
        # A first document the converter refuses is said in its window, which
        # opens before the conversion ends, as a later document's is.
        raise CannotStartError(e) from e
