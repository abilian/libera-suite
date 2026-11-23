"""`lb release publish`'s downloads phase: does what users download open a window?

`lb linux screenshot` opens one from the build tree, in the test container: it proves
the code opens a window and says nothing about the artifact anybody downloads,
which on Linux is a Flatpak whose GTK and WebKit come from the GNOME runtime
rather than the distribution. A different WebKit, and the one users get.

This Mac has no flatpak, no Xvfb and no X server, so it asks machines that can.
build/install/released-gui.sh is what runs on a Linux one, and released-gui.ps1
on a Windows one: each installs what the CDN serves now, the way a user would,
and is copied there and run with no checkout and no payload of its own. This is
the half that drives them: which machines, the copy, the verdict, the
screenshot back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libera_build import inventory, repo, versions
from libera_build.hosts import MARK, SshHost, facts_from
from libera_build.origin import staged
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host

SCRIPT = "~/released-gui.sh"
SHOT = "~/released-gui.png"
# Beside the script, for its five minutes in each editor; the driver is the
# gui tier's, which runs a window in the installed application's Python.
FIVE = "~/five-minutes.sh"
FIVE_DRIVER = "~/released-gui-driver.py"
DRIVER = ("tests", "d_gui", "driver.py")
FIVE_WORK = "~/.cache/libera-released-gui/five"
WINDOWS_FIVE = "five-minutes-windows.py"
WINDOWS_FIVE_DRIVER = "released-gui-driver.py"
# released-gui.ps1's $env:TEMP\libera-released-gui\five, as scp reads a path:
# from the home directory.
WINDOWS_FIVE_WORK = "AppData/Local/Temp/libera-released-gui/five"
# scp's relative paths are the home directory on both systems, and Windows'
# own programs are handed theirs in its own spelling.
WINDOWS_SCRIPT = "released-gui.ps1"
WINDOWS_SHOT = "released-gui.png"
WINDOWS_RUN = (
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w '
    '"$HOME/released-gui.ps1")" -Out "$(cygpath -w "$HOME/released-gui.png")"'
)


@dataclass(frozen=True)
class ReleasedGuiOptions:
    # A release's staged origin here (`stage`, origin.staged): each machine is
    # sent its part and serves it to itself, instead of what the CDN serves.
    origin: Path | None = None
    root: Path = REPO
    # The version the staged origin holds: a release's, or a check's
    # candidate (0.7.4+69906cd), which the tree's version is not.
    version: str = ""
    host_for: Callable[[str], Host] = field(default=SshHost)


def passed(out: str) -> bool:
    """The script's verdict, read from the line it printed for it: over ssh an
    exit status describes the shell, including its logout scripts. The line and
    not a word: "PASS" turned up in a document's path and the app's own log."""
    return facts_from(out).get(MARK) == "ok"


def is_windows(out: str) -> bool:
    """Git Bash, which is what a Windows builder's ssh logs into, says MINGW64_NT.
    Any line: ssh's own warnings come back in the same stream, after it."""
    return any(
        line.startswith(("MINGW", "MSYS", "CYGWIN")) for line in out.splitlines()
    )


def on_host(host: Host, name: str, options: ReleasedGuiOptions) -> bool:
    """Copy the script there, run it, bring the screenshot back."""
    step(f"{name} on {host.name}")
    uname = host.capture("echo reachable; uname -s")
    if "reachable" not in uname:
        say("    unreachable")
        return False
    windows = is_windows(uname)
    if windows:
        script, shot_there = WINDOWS_SCRIPT, WINDOWS_SHOT
        command = WINDOWS_RUN
    else:
        script, shot_there = SCRIPT, SHOT
        command = f"sh {SCRIPT} --out {SHOT}"
    if options.origin:
        app = options.version or versions.app_version(options.root)
        if not send_origin(host, name, options.origin, app):
            return False
        command = staged.serve(f'"$HOME/{staged.remote(app)}"', app) + command
    if not send_scripts(host, options.root, script, windows=windows):
        return False
    out = host.capture(command)
    for line in out.splitlines():
        say(f"    {line}")
    if not passed(out):
        return False
    shot = options.root / "build" / "out" / f"released-gui-{name}.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    if host.fetch(shot_there, shot)[0] or not shot.is_file():
        say("    it passed and the screenshot did not come back")
        return False
    say(f"    {shot}")
    fetch_five(
        host,
        WINDOWS_FIVE_WORK if windows else FIVE_WORK,
        options.root / "build" / "out" / "five-minutes",
        name,
    )
    return True


def send_scripts(host: Host, root: Path, script: str, *, windows: bool) -> bool:
    """The script there, and beside it what its five minutes in each editor
    need: the gui tier's driver, and the script that runs it, which on
    Windows drives the frozen application from outside."""
    install = root / "build" / "install"
    five, driver = (
        (WINDOWS_FIVE, WINDOWS_FIVE_DRIVER) if windows else (FIVE, FIVE_DRIVER)
    )
    sent = [
        (install / script.removeprefix("~/"), script),
        (install / five.removeprefix("~/"), five),
        (root.joinpath(*DRIVER), driver),
    ]
    for local, there in sent:
        if host.send(local, there)[0]:
            say(f"    could not copy {local.name} there")
            return False
    return True


def fetch_five(host: Host, there: str, into: Path, name: str) -> None:
    """The pictures of the documents reopened, for a person to look at: the
    script has checked what can be checked without eyes."""
    into.mkdir(parents=True, exist_ok=True)
    for ext in ("docx", "xlsx", "pptx"):
        picture = into / f"{name}-{ext}.png"
        if host.fetch(f"{there}/five-{ext}.png", picture)[0]:
            say(f"    no picture of the .{ext} came back")
        else:
            say(f"    {picture}")


def send_origin(host: Host, platform: str, zone: Path, app: str) -> bool:
    """This machine's part of the staged origin, copied there."""
    there = staged.remote(app)
    host.capture(f'mkdir -p "$HOME/{there}/bundles"')
    for path in staged.for_platform(platform, app):
        if not (zone / path).is_file():
            say(f"    nothing staged for {platform}: no {path} in {zone}")
            return False
        # scp's relative paths are the home directory, on Windows too.
        if host.send(zone / path, f"{there}/{path}")[0]:
            say(f"    could not copy {path} there")
            return False
    return True


def run(options: ReleasedGuiOptions) -> int:
    builders = inventory.read(options.root / repo.BUILDERS)
    remotes = inventory.gui_remotes(builders)
    targets = [(b.platform, b.target) for b in remotes]
    if not targets:
        msg = "no remote Linux or Windows builders in build/builders.toml"
        raise RefusedError(msg)
    passes = sum(
        on_host(options.host_for(target), name, options) for name, target in targets
    )
    step(f"{passes} of {len(targets)} machine(s) drew a window")
    if passes < len(targets):
        msg = "a released Libera Suite did not draw a window everywhere"
        raise RefusedError(msg)
    return 0
