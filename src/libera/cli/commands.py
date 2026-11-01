"""One function per thing `libera` can be asked to do.

Each returns the process exit status, and each prints its own failure:
somebody who typed a filename wrong gets a sentence saying what went wrong,
never a traceback.

`dispatch` chooses between them; nothing here knows how the arguments were
parsed.
"""

from __future__ import annotations

import glob
import os
import platform
import shutil
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

from libera import gui, launcher, payload as payload_mod
from libera.host import apps, convert, instance, opening, server, session
from libera.host.convert import ConversionError
from libera.host.session import NotReadyError
from libera.payload import NoPayloadError, PayloadError, fonts, prune

if TYPE_CHECKING:
    import argparse

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


def _fail(message: object) -> int:
    """Say what went wrong, on stderr, and return the status that goes with it."""
    print(f"libera: {message}", file=sys.stderr)
    return 1


# The heading when no more particular one applies.
CANNOT_START = "Libera Suite could not start"


def _refuse(heading: str, paragraphs: list[str], command: str = "") -> None:
    """Say why `libera` will not start, where somebody will see it.

    On stderr, and in a window as well when there is no terminal: launched
    from an icon or a file manager, stderr goes nowhere and the icon flashes
    and vanishes. Only for what comes after `gui.explain_why_no_window`, because a
    machine that cannot open a window cannot be told in one.
    """
    said = [f"{heading}.", *paragraphs, *([command] if command else [])]
    print("libera: " + "\n\n".join(said), file=sys.stderr)
    if not _is_interactive():
        gui.show_problem(heading, paragraphs, command)


def install_payload(args: argparse.Namespace) -> int:
    trust = args.trust_manifest
    # A copy installed from source asks, in a terminal, rather than wanting
    # an option nobody would guess; a script still says --trust-manifest.
    if (
        args.source is None
        and not trust
        and not payload_mod.can_fetch()
        and _is_interactive()
    ):
        print(FROM_SOURCE)
        if not _confirm("Download them now?"):
            return 1
        trust = True
    try:
        p = payload_mod.install(source=args.source, trust_manifest=trust)
    except PayloadError as e:
        return _fail(e)
    print(f"Installed in {p.root}")
    # The one moment a user is looking at this program in a terminal and has
    # just finished setting it up. Only said here: the
    # command is called payload-install, and writing to the desktop's own
    # directories is not what that name promises.
    if launcher.explain_unsupported() is None and not launcher.is_installed():
        print("  for an icon and Open With: libera --launcher-install")
    return 0


def install_launcher(_args: argparse.Namespace) -> int:
    why = launcher.explain_unsupported()
    if why:
        return _fail(why)
    for path in launcher.install():
        print(f"wrote {path}")
    print("Libera Suite is among your applications, and opens what it reads.")
    return 0


def remove_launcher(_args: argparse.Namespace) -> int:
    why = launcher.explain_unsupported()
    if why:
        return _fail(why)
    gone = launcher.remove()
    if not gone:
        print("nothing to remove: it was not among your applications")
        return 0
    for path in gone:
        print(f"removed {path}")
    return 0


def show_payload_status(_args: argparse.Namespace) -> int:
    try:
        p = payload_mod.resolve()
    except PayloadError as e:
        return _fail(e)

    record = _print_payload(p)
    _print_installed_versions()
    # Corresponding source, per AGPL. A user holding this binary is entitled to
    # know exactly which revisions it was built from.
    source = record.get("source") or {}
    if not source:
        print("source:    not recorded (local build)")
        return 0
    print("source:")
    for url in source.get("repositories", []):
        print(f"  {url}  @ {source.get('libera_commit', '?')}")
    for repo, sha in sorted((source.get("pins") or {}).items()):
        print(f"  {source.get('upstream', 'upstream')}/{repo} @ {sha}")
    return 0


def _print_installed_versions() -> None:
    """Every version in the payload folder, with when a copy last used it:
    what a launch removes once nobody has, for prune.UNUSED_FOR."""
    versions = prune.list_versions(payload_mod.get_data_dir())
    if not versions:
        return
    weeks = prune.UNUSED_FOR // (7 * prune.DAY)
    print(f"installed: (each removed once unused for {weeks} weeks)")
    for v in reversed(versions):
        used = time.strftime("%Y-%m-%d", time.localtime(v.last_used))
        size = prune.measure(v.root) / 1e6
        this = "  (this version)" if v.name == payload_mod.PAYLOAD_VERSION else ""
        print(f"  {v.name:<8} last used {used}  {size:4.0f} MB{this}")


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


def remove_payload(_args: argparse.Namespace) -> int:
    root = payload_mod.get_installed_dir()
    if not root.exists():
        print(f"nothing installed at {root}")
        return 0
    shutil.rmtree(root)
    print(f"removed {root}")
    return 0


def _resolve_payload_or_offer() -> payload_mod.Payload | None:
    """Resolve the payload, offering to install it when there is none.

    Nothing downloads behind the user's back: an interactive run asks, and a
    non-interactive one prints the command and stops.
    """
    try:
        return payload_mod.resolve()
    except NoPayloadError:
        return _offer_to_install()
    except PayloadError as e:
        _refuse(CANNOT_START, [str(e)])
        return None


def _offer_to_install() -> payload_mod.Payload | None:
    """There are no components: fetch them if the user agrees.

    A release checks the download against the checksums in its wheel. A copy
    installed from source has none, and checks it against the download site's
    own, which the question says before it is answered.
    """
    verified = payload_mod.can_fetch()
    if not _ask_to_install(verified=verified):
        return None
    try:
        return payload_mod.install(trust_manifest=not verified)
    except PayloadError as e:
        _refuse(CANNOT_START, [str(e)])
        return None


# Said before the question, in a copy that has no checksums of its own.
FROM_SOURCE = (
    "This copy of Libera Suite was installed from source, not from a release,"
    " so it has no checksums of its own: the download will be checked against"
    " the download site's."
)


def _format_install_command() -> str:
    """The exact line to type, which is not the same inside the sandbox.

    `libera` is not on the host's PATH when the application is a Flatpak, so
    telling a Flatpak user to run it sends them nowhere. FLATPAK_ID is set for
    every process inside the sandbox and is the app id the command needs.
    """
    app_id = os.environ.get("FLATPAK_ID")
    if app_id:
        return f"flatpak run {app_id} --payload-install"
    return "libera --payload-install"


def _ask_to_install(*, verified: bool = True) -> bool:
    """Ask before downloading. A non-interactive run never does."""
    command = _format_install_command()
    if not _is_interactive():
        # Reached only from open_documents, which has already been past
        # gui.explain_why_no_window(), so a window can be opened here.
        _refuse(
            "Libera Suite needs its components",
            [
                (
                    "The application is installed; its components "
                    "are not. They are about 90 MB, downloaded once."
                ),
                "Run this, then start Libera Suite again:",
            ],
            command,
        )
        return False
    print(
        "Libera Suite needs its components (about 90 MB, downloaded"
        " once), and does not have them yet."
    )
    if not verified:
        print(FROM_SOURCE)
    if not _confirm("Download them now?"):
        print(f"  run `{command}` when you are ready.")
        return False
    return True


def _confirm(question: str) -> bool:
    """Yes unless told no; no when nobody can answer."""
    try:
        answer = input(f"{question} [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in {"", "y", "yes"}


def serve(args: argparse.Namespace) -> int:
    """Serve the editor without a window. Used by the regression harness."""
    try:
        p = payload_mod.resolve()
        font_index = fonts.choose(p)
        prune.note_use(p.root)
    except PayloadError as e:
        return _fail(e)

    document = Path(args.file[0]).expanduser().resolve()
    if not document.is_file():
        return _fail(f"no such file: {document}")

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
    try:
        opening.open_document(served, document)
        httpd = server.make_server(port, served)
    except (NotReadyError, ConversionError) as e:
        return _fail(e)
    except OSError as e:
        return _fail(f"cannot listen on port {port}: {e.strerror}")
    print(server.make_editor_url(port, served, document.name), flush=True)
    httpd.serve_forever()
    return 0


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


class CannotConvertError(ValueError):
    """A `--convert` that cannot be done as asked, found before converting."""


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
            raise CannotConvertError(msg)
        ext = (args.to or Path(args.output).suffix).lstrip(".").lower()
        _check_writes(apps.choose_for(src), src, ext)
        plan.append((src, _choose_target(args, src, ext), ext))

    targets = [t.resolve() for _, t, _ in plan if t is not None]
    for src, target, _ in plan:
        if target is None:
            continue
        if target.exists() and target.samefile(src):
            msg = f"{src} would be written over itself"
            raise CannotConvertError(msg)
        if targets.count(target.resolve()) > 1:
            msg = f"several documents would be written to {target}"
            raise CannotConvertError(msg)
    return plan


def _check_writes(app: apps.App, src: Path, ext: str) -> None:
    if not app.editable:
        msg = f"{src.name}: {app.title} only shows documents, and writes none"
        raise CannotConvertError(msg)
    if ext not in app.ids_by_ext:
        writes = ", ".join(e for _, e in app.save_formats)
        msg = f"{src.name}: {app.title} cannot write .{ext}; it writes {writes}"
        raise CannotConvertError(msg)


def _choose_target(args: argparse.Namespace, src: Path, ext: str) -> Path | None:
    if args.output == "-":
        return None
    if args.output is not None:
        return Path(args.output).expanduser()
    folder = Path(args.outdir).expanduser() if args.outdir else src.parent
    return folder / f"{src.stem}.{ext}"


def convert_documents(args: argparse.Namespace) -> int:
    """Write each document in another format, with no window: `--convert`.

    The conversions a Save makes -- x2t into Editor.bin, then out to the
    format asked for -- so the file is the one Save As would have written.
    Each document has a session of its own in a scratch directory, registered
    nowhere: no Recent list, no lock file, nothing left behind. A document
    that fails is reported and the others go on; the exit status is 1 if
    any failed.
    """
    try:
        plan = plan_conversions(args)
        p = payload_mod.resolve()
        font_index = fonts.choose(p)
        prune.note_use(p.root)
    except (CannotConvertError, PayloadError) as e:
        return _fail(e)
    if args.outdir:
        Path(args.outdir).expanduser().mkdir(parents=True, exist_ok=True)

    failed = 0
    with tempfile.TemporaryDirectory(prefix="libera-convert-") as scratch:
        for index, (src, target, ext) in enumerate(plan):
            try:
                work = Path(scratch) / str(index)
                staged = _convert_one(p.root, font_index, work, src, ext)
            except ConversionError as e:
                failed += _fail(f"{src}: {e}")
                continue
            except NotReadyError as e:
                return _fail(e)
            if target is None:
                sys.stdout.buffer.write(staged.read_bytes())
                sys.stdout.flush()
            else:
                # Converted aside, then moved: a failure never leaves half a
                # file where the old one was.
                shutil.move(staged, target)
    return 1 if failed else 0


def _convert_one(
    payload: Path, font_index: Path | None, work: Path, src: Path, ext: str
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


def diagnose(_args: argparse.Namespace) -> int:
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
        return 0

    _print_payload(p)
    editors = sorted(d.name for d in (p.root / "web-apps" / "apps").glob("*editor"))
    print(f"  editors  {', '.join(editors) or 'none'}")

    state = payload_mod.get_state_dir()
    sessions = sorted(payload_mod.get_sessions_dir().glob("*/unsaved.json"))
    print(f"state      {state}")
    print(f"  unsaved  {len(sessions)} session(s) holding edits that were never saved")
    return 0


def open_documents(args: argparse.Namespace) -> int:
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
            return _fail(f"no such file: {document}")
        documents.append(document.resolve())

    # A Libera Suite already running takes them, in a window of its own, and
    # this process is done: see `host/instance.py` for why there is only ever
    # one. Before the window and the payload checks, which the running one has
    # already passed.
    # Only to one running with this launch's configuration.
    if instance.hand_off(documents):
        return 0

    # Then the window, and only then the payload: a machine that cannot open
    # one has no use for 116 MB of editor.
    cannot = gui.explain_why_no_window()
    if cannot:
        return _fail(cannot)

    p = _resolve_payload_or_offer()
    if p is None:
        return 1
    return _run(p, documents, Path(args.shot).expanduser() if args.shot else None)


def _run(
    p: payload_mod.Payload, documents: list[Path], shot: Path | None = None
) -> int:
    """The application, as the one instance; or the documents handed to the
    instance another launch has just become."""
    # The one place the GUI is imported: pywebview and, on a Mac, AppKit cost
    # a third of a second, and only this command opens a window.
    from libera.host import app

    try:
        held = instance.become(documents)
        if held is None:
            return 0
        with held:
            app.run(p.root, payload_mod.get_sessions_dir(), documents, shot=shot)
    except (NotReadyError, instance.BusyError) as e:
        _refuse(CANNOT_START, [str(e)])
        return 1
    # A first document the converter refuses is said in its window, which
    # opens before the conversion ends, as a later document's is.
    return 0
