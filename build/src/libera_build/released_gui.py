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
from libera_build.artifacts import bundle_name, installer_name
from libera_build.hosts import MARK, SshHost, facts_from
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from libera_build.hosts import Host

SCRIPT = "~/released-gui.sh"
SHOT = "~/released-gui.png"
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
    # A release's staged files here (`stage`), sent to each machine and
    # installed from there, instead of what the CDN serves.
    staged: Path | None = None
    root: Path = REPO
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
    install = options.root / "build" / "install"
    windows = is_windows(uname)
    if windows:
        script, shot_there = WINDOWS_SCRIPT, WINDOWS_SHOT
        command = WINDOWS_RUN
    else:
        script, shot_there = SCRIPT, SHOT
        command = f"sh {SCRIPT} --out {SHOT}"
    if options.staged:
        sent = send_staged(host, name, options.staged, options.root, windows=windows)
        if sent is None:
            return False
        command += (
            f' -Installer "$(cygpath -w "$HOME/{sent}")"'
            if windows
            else f' --bundle "$HOME/{sent}"'
        )
    if host.send(install / script.removeprefix("~/"), script)[0]:
        say("    could not copy the script there")
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
    return True


def staged_files(staged: Path, platform: str, app: str) -> list[Path]:
    """What a machine of `platform` installs from the staged release of `app`:
    its Flatpak bundle, or the Windows installer and its checksum."""
    if platform.startswith("windows-"):
        setup = staged / installer_name(app)
        return [setup, setup.with_name(setup.name + ".sha256")]
    return [staged / bundle_name(app, inventory.arch_of(platform))]


def send_staged(
    host: Host, platform: str, staged: Path, root: Path, *, windows: bool
) -> str | None:
    """Copy this machine's staged file there; its path from home, or None."""
    files = staged_files(staged, platform, versions.app_version(root))
    if not all(f.is_file() for f in files):
        say(f"    nothing staged for {platform} in {staged}")
        return None
    for f in files:
        # scp's relative paths are the home directory, on Windows too.
        there = f.name if windows else f"~/{f.name}"
        if host.send(f, there)[0]:
            say(f"    could not copy {f.name} there")
            return None
    return files[0].name


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
