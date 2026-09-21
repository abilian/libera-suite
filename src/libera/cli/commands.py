"""One function per thing `libera` can be asked to do.

Each returns the process exit status, and each prints its own failure: a
command line's job is to say what went wrong in a sentence, not to hand a
traceback to somebody who typed a filename wrong.

`dispatch` chooses between them; nothing here knows how the arguments were
parsed.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

from libera import gui, launcher, payload as payload_mod
from libera.host import app, opening, server, session
from libera.host.session import NotReadyError
from libera.payload import PayloadError


def cmd_payload_install(args) -> int:
    try:
        p = payload_mod.install(source=args.source, trust_manifest=args.trust_manifest)
    except PayloadError as e:
        print(f"libera: {e}", file=sys.stderr)
        return 1
    print(f"installed payload {payload_mod.PAYLOAD_VERSION} in {p.root}")
    # The one moment a Linux user is looking at this program in a terminal and
    # has just finished setting it up. Said here rather than done here: the
    # command is called payload-install, and writing to the desktop's own
    # directories is not what that name promises.
    if launcher.why() is None and not launcher.is_installed():
        print("  for an icon in the launcher, and Open With: libera --launcher-install")
    return 0


def cmd_launcher_install(_args) -> int:
    why = launcher.why()
    if why:
        print(f"libera: {why}", file=sys.stderr)
        return 1
    for path in launcher.install():
        print(f"wrote {path}")
    print("Libera Suite is in the launcher, and offers to open the formats it reads.")
    return 0


def cmd_launcher_remove(_args) -> int:
    why = launcher.why()
    if why:
        print(f"libera: {why}", file=sys.stderr)
        return 1
    gone = launcher.remove()
    if not gone:
        print("no desktop entry installed")
        return 0
    for path in gone:
        print(f"removed {path}")
    return 0


def cmd_payload_status(_args) -> int:
    try:
        p = payload_mod.resolve()
    except PayloadError as e:
        print(f"libera: {e}", file=sys.stderr)
        return 1

    info = p.info()
    print(f"payload:   {p.root}")
    print(f"found via: {p.origin}")
    print(f"version:   {info.get('payload_version', 'unknown (local build)')}")
    if info.get("platform"):
        print(f"platform:  {info['platform']}  fonts: {info.get('font_set', '?')}")
    print(f"x2t:       {'present' if p.x2t.is_file() else 'MISSING'}")

    # Corresponding source, per AGPL. A user holding this binary is entitled to
    # know exactly which revisions it was built from.
    source = info.get("source") or {}
    if source:
        print("source:")
        for url in source.get("repositories", []):
            print(f"  {url}  @ {source.get('libera_commit', '?')}")
        for repo, sha in sorted((source.get("pins") or {}).items()):
            print(f"  {source.get('upstream', 'upstream')}/{repo} @ {sha}")
    else:
        print("source:    not recorded (local build)")
    return 0


def cmd_payload_remove(_args) -> int:
    root = payload_mod.data_dir() / payload_mod.PAYLOAD_VERSION
    if not root.exists():
        print(f"nothing installed at {root}")
        return 0
    shutil.rmtree(root)
    print(f"removed {root}")
    return 0


def _payload_or_offer() -> payload_mod.Payload | None:
    """Resolve the payload, offering to install it when there is none.

    Nothing downloads behind the user's back: an interactive run asks, and a
    non-interactive one prints the command and stops.
    """
    try:
        return payload_mod.resolve()
    except PayloadError as e:
        if "no editor payload found" not in str(e):
            print(f"libera: {e}", file=sys.stderr)
            return None

    if not payload_mod.can_fetch():
        _say_there_is_nothing_to_fetch()
        return None

    if not _agreed_to_install():
        return None
    try:
        return payload_mod.install()
    except PayloadError as e:
        print(f"libera: {e}", file=sys.stderr)
        return None


def _say_there_is_nothing_to_fetch() -> None:
    """No payload, and no way for this build to get one.

    Only a released wheel carries the hashes a download is checked against, so
    reaching here means a checkout or a build that was never stamped. Three
    ways out, cheapest first, and the last one takes an afternoon.
    """
    heading = "Libera Suite has no editor payload, and this build cannot fetch one"
    why = (
        "A release carries the hashes it checks downloads against. This copy "
        "was built from a checkout and has none, so there is nothing to verify "
        "a download against and nothing to offer."
    )
    lines = (
        "  point at a local build:     export LIBERA_PAYLOAD=/path/to/out/payload\n"
        "  install built artifacts:    libera --payload-install --from DIR\n"
        "  or build one (an afternoon; V8 alone is ~30 minutes):   make payload-all"
    )
    print(f"libera: {heading}.\n\n{why}\n\n{lines}", file=sys.stderr)
    if not sys.stdin.isatty():
        # Same reason as in _agreed_to_install: a launcher has no terminal, so
        # stderr went nowhere and the icon just vanished.
        gui.show_problem(heading, [why], lines)


def _install_command() -> str:
    """The exact line to type, which is not the same inside the sandbox.

    `libera` is not on the host's PATH when the application is a Flatpak, so
    telling a Flatpak user to run it sends them nowhere. FLATPAK_ID is set for
    every process inside the sandbox and is the app id the command needs.
    """
    app_id = os.environ.get("FLATPAK_ID")
    if app_id:
        return f"flatpak run {app_id} --payload-install"
    return "libera --payload-install"


def _agreed_to_install() -> bool:
    """Ask before downloading. A non-interactive run never does."""
    print(
        "Libera Suite needs its editor payload (about 120 MB), "
        "and does not have it yet."
    )
    command = _install_command()
    if not sys.stdin.isatty():
        print(f"  run: {command}", file=sys.stderr)
        # And on screen, because there may be no terminal to have read that.
        # Reached only from cmd_open, which has already been past
        # gui.why_no_window(), so a window can be opened here.
        gui.show_problem(
            "Libera Suite has no editor payload yet",
            [
                (
                    "The application is installed; the editors are not. "
                    "They are about 120 MB and are fetched once."
                ),
                "Run this, then start Libera Suite again:",
            ],
            command,
        )
        return False
    try:
        answer = input("Download and install it now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if answer not in {"", "y", "yes"}:
        print("  run `libera --payload-install` when you are ready.")
        return False
    return True


def cmd_serve(args) -> int:
    """Serve the editor without a window. Used by the regression harness."""
    try:
        p = payload_mod.resolve()
    except PayloadError as e:
        print(f"libera: {e}", file=sys.stderr)
        return 1

    document = Path(args.file[0]).expanduser().resolve()
    if not document.is_file():
        print(f"libera: no such file: {document}", file=sys.stderr)
        return 1

    # Beside the windowed application's sessions, not in a directory of its
    # own: sharing the parent is what makes them share a Recent list.
    work = (
        Path(args.work).expanduser()
        if args.work
        else payload_mod.sessions_dir() / "serve"
    )
    session.configure(
        session.Host(
            payload=p.root,
            work=work,
            document=document,
            shot=Path(args.shot).expanduser() if args.shot else None,
        )
    )
    try:
        opening.open_document(document)
        httpd = server.make_server(args.port)
    except NotReadyError as e:
        print(f"libera: {e}", file=sys.stderr)
        return 1
    print(server.editor_url(args.port, document.name), flush=True)
    httpd.serve_forever()
    return 0


def cmd_diagnose(_args) -> int:
    """Everything worth pasting into a bug report, in one place.

    `-v` covers what is happening now; this covers "it did something odd an
    hour ago", which is most of what a beta tester has to tell us. Deliberately
    one screen, and deliberately not automatic: nothing here leaves the machine
    unless somebody copies it.
    """
    print(f"libera    {version('libera')}")
    print(f"python     {sys.version.split()[0]}")
    print(f"platform   {platform.platform()}  {platform.machine()}")

    window = gui.why_no_window()
    print(f"window     {'ok' if window is None else 'NOT AVAILABLE'}")

    if launcher.why() is None:
        # Inline rather than a local: `state` further down is the state
        # directory, and this had taken the name first.
        print(
            f"launcher   {'installed' if launcher.is_installed() else 'not installed'}"
            f"  ({launcher.entry_path()})"
        )

    try:
        p = payload_mod.resolve()
    except PayloadError as e:
        print(f"payload    MISSING\n  {e}")
        return 0

    info = p.info()
    print(f"payload    {info.get('payload_version', 'local build')}  ({p.origin})")
    print(f"  at       {p.root}")
    print(f"  platform {info.get('platform', '?')}  fonts: {info.get('font_set', '?')}")
    print(f"  built    {info.get('built', '?')}")
    print(f"  x2t      {'present' if p.x2t.is_file() else 'MISSING'}")

    editors = sorted(d.name for d in (p.root / "web-apps" / "apps").glob("*editor"))
    print(f"  editors  {', '.join(editors) or 'none'}")

    state = payload_mod.state_dir()
    sessions = sorted(payload_mod.sessions_dir().glob("*/unsaved.json"))
    print(f"state      {state}")
    print(f"  unsaved  {len(sessions)} session(s) holding edits that were never saved")
    return 0


def cmd_open(args) -> int:
    """Open documents, or the start window when none are named.

    Which editor a file gets is decided by the file, not by a command: see
    host/apps.py. There is no `libera words` any more for the same reason
    there is no `open -a TextEdit` in most people's muscle memory -- you open
    the document.
    """
    # The arguments first: a name that is not a file is the cheapest thing to
    # be wrong about, and the only one of the three that is fixed by retyping.
    # Answering `libera reprot.docx` with a paragraph about GTK -- which is
    # what checking the window first did on any Linux box whose virtualenv
    # cannot see PyGObject -- buries the typo under the environment.
    documents = []
    for name in args.file:
        document = Path(name).expanduser()
        if not document.is_file():
            print(f"libera: no such file: {document}", file=sys.stderr)
            return 1
        documents.append(document.resolve())

    # Then the window, and only then the payload: a machine that cannot open
    # one has no use for 116 MB of editor.
    cannot = gui.why_no_window()
    if cannot:
        print(f"libera: {cannot}", file=sys.stderr)
        return 1

    p = _payload_or_offer()
    if p is None:
        return 1

    try:
        app.run(p.root, payload_mod.sessions_dir(), documents)
    except NotReadyError as e:
        print(f"libera: {e}", file=sys.stderr)
        return 1
    return 0
