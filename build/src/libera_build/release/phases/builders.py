"""`bundles`: what users download, made by `lb` on the remote builders, in
parallel.

Every remote builder alike: each is told what its platform makes, each result
is looked for there and then brought here. A Linux builder bundles a Flatpak,
the Windows one makes the installer. Each builds the components it ships from
the pins as it goes (the Flatpak through `lb components`, the installer
through `uv sync`), so neither reads a core an earlier run left there. Windows
used to be built and published by hand, from the Windows machine, as a release
of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera_build import versions
from libera_build.artifacts import (
    BUNDLES_DIR,
    MIN_BUNDLE_BYTES,
    bundle_name,
    installer_name,
    run_bundles,
)
from libera_build.hosts import remote_path
from libera_build.release.builds import check_remote_file, run_builds
from libera_build.report import problems, say, step

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context


def arch_suffix(b: Builder) -> str:
    return f" --arch {b.arch}"


@dataclass(frozen=True)
class Bundle:
    """What users download from a builder: the `lb` command that makes it, and
    the files it leaves under the checkout there, the bundle itself first."""

    command: str
    files: tuple[str, ...]


def bundle_of(b: Builder, app: str) -> Bundle | None:
    """A Flatpak per Linux architecture; the installer on Windows, with the
    SHA-256 that install.ps1 checks the download against. None for a Mac:
    macOS ships through Homebrew, which builds from source."""
    if b.os == "linux":
        return Bundle(
            f"app build flatpak{arch_suffix(b)}",
            (f"build/out/{bundle_name(app, b.arch)}",),
        )
    if b.os == "windows":
        setup = f"{BUNDLES_DIR}/{installer_name(app)}"
        return Bundle("app build windows", (setup, f"{setup}.sha256"))
    return None


def bundles(ctx: Context) -> None:
    """What users download, each made on a machine of its platform. A Flatpak
    cannot be cross-built: flatpak-builder runs every module inside bubblewrap,
    whose seccomp filter is built for the architecture it runs on, and
    qemu-user does not carry one across. See notes/15-builders.md.
    """
    app = versions.app_version(ctx.root)
    made = {b: bundle for b in ctx.remotes if (bundle := bundle_of(b, app))}
    if not made:
        say("    no remote builders that make a bundle; nothing to do")
        return

    def verify_bundle(b: Builder, host: Host) -> str | None:
        path = f"{remote_path(b.repo)}/{made[b].files[0]}"
        return check_remote_file(b, host, path, MIN_BUNDLE_BYTES)

    # Read once, at the commit the builds start from, as components does.
    dest = run_bundles(ctx.root)
    run_builds(ctx, list(made), lambda b: made[b].command, verify_bundle, "bundling")
    fetch_bundles(ctx, made, dest)


def fetch_bundles(ctx: Context, made: dict[Builder, Bundle], dest: Path) -> None:
    """Bring every bundle here, into the run's directory, where `stage`
    gathers the whole release."""
    step("collecting the bundles")
    dest.mkdir(parents=True, exist_ok=True)
    found = []
    for b, bundle in made.items():
        for path in bundle.files:
            landed = dest / path.rsplit("/", 1)[-1]
            source = f"{b.repo}/{path}"
            status, out = ctx.host_for(b).fetch(source, landed)
            # scp reports success for a transfer that wrote nothing often
            # enough that the size is the thing to believe.
            first = path == bundle.files[0]
            minimum = MIN_BUNDLE_BYTES if first else 1
            if status != 0 or not landed.is_file() or landed.stat().st_size < minimum:
                found.append(
                    f"{b.platform}: {b.target}:{source} did not arrive\n"
                    f"       {out.strip()}"
                )
            elif first:
                size = landed.stat().st_size // 1048576
                say(f"    {b.platform:<14} {landed.name}  {size} MB")
    problems(found, "the bundles are not all here.")
