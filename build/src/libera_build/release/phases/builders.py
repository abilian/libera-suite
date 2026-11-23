"""`bundles`: what users download, made by `lb` on the remote builders, in
parallel.

Every remote builder alike: each is sent this run's wheels for its platform
(libera, its core, the editors, labelled with the run's version), told what
its platform makes of them, and the result is looked for there and then
brought here. A Linux builder bundles a Flatpak, the Windows one makes the
installer. Packaging only: neither builds a component, so each ships the very
files the stage installs, and a release makes its bundles again from its own
labelled files in minutes. Windows used to be built and published by hand,
from the Windows machine, as a release of its own.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera.manifest import hash_file
from libera_build.artifacts import (
    BUNDLES_DIR,
    MIN_BUNDLE_BYTES,
    bundle_name,
    installer_name,
)
from libera_build.hosts import remote_path
from libera_build.release.builds import check_remote_file, run_builds
from libera_build.release.phases import staging
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


def wheels_there(app: str) -> str:
    """Where a builder is sent the wheels it packages, under its home."""
    return f"{staging.remote_stage(app)}/wheels"


def bundle_of(b: Builder, app: str) -> Bundle | None:
    """A Flatpak per Linux architecture; the installer on Windows, with the
    SHA-256 that install.ps1 checks the download against. None for a Mac:
    macOS ships through Homebrew, which builds from source."""
    wheels = f' --wheels "$HOME/{wheels_there(app)}"'
    if b.os == "linux":
        return Bundle(
            f"app build flatpak{arch_suffix(b)}{wheels}",
            (f"build/out/{bundle_name(app, b.arch)}",),
        )
    if b.os == "windows":
        setup = f"{BUNDLES_DIR}/{installer_name(app)}"
        return Bundle(f"app build windows{wheels}", (setup, f"{setup}.sha256"))
    return None


def bundles(ctx: Context) -> None:
    """What users download, each made on a machine of its platform. A Flatpak
    cannot be cross-built: flatpak-builder runs every module inside bubblewrap,
    whose seccomp filter is built for the architecture it runs on, and
    qemu-user does not carry one across. See notes/15-builders.md.
    """
    app = ctx.version
    dest = ctx.files / "bundles"
    made = {b: bundle for b in ctx.remotes if (bundle := bundle_of(b, app))}
    sources = {b: made_from(ctx.files / "pypi", app, b) for b in made}
    for b in list(made):
        if already_made(dest, made[b], sources[b]):
            say(f"    {b.platform:<14} made before from these very wheels")
            del made[b]
    if not made:
        say("    no bundle to make")
        return
    step(f"sending the {app} wheels to the builders")
    found = []
    for b in made:
        host = ctx.host_for(b)
        # Only this version's, so nothing else can be packaged; and every
        # other candidate's goes, which a check a day would otherwise pile
        # up there, 160 MB each (the arm64 builder's /tmp filled once).
        there = wheels_there(app)
        host.capture(
            f'find "$HOME/{staging.STAGE_ROOT}" -mindepth 1 -maxdepth 1'
            f" -name '*+*' ! -name '{app}' -exec rm -rf {{}} + 2>/dev/null;"
            f' rm -rf "$HOME/{there}"'
        )
        if problem := staging.send_wheels(host, b, ctx.files / "pypi", app, there):
            found.append(problem)
        else:
            say(f"    {b.platform:<14} {there}")
    problems(found, "no bundle was started.")

    def verify_bundle(b: Builder, host: Host) -> str | None:
        path = f"{remote_path(b.repo)}/{made[b].files[0]}"
        return check_remote_file(b, host, path, MIN_BUNDLE_BYTES)

    run_builds(ctx, list(made), lambda b: made[b].command, verify_bundle, "bundling")
    fetch_bundles(ctx, made, dest, sources)


def made_from(pypi: Path, app: str, b: Builder) -> str:
    """What `b` packages, as one hash: the wheels it is sent."""
    digest = hashlib.sha256()
    for name in staging.wheels_for(pypi, app, b):
        digest.update(hash_file(pypi / name).encode())
    return digest.hexdigest()


def from_file(dest: Path, bundle: Bundle) -> Path:
    """Beside a bundle here, the hash of the wheels it was made from."""
    return dest / (bundle.files[0].rsplit("/", 1)[-1] + ".from")


def already_made(dest: Path, bundle: Bundle, source: str) -> bool:
    """A check run again at the same commit packages the same wheels: what it
    made then is what it would make now."""
    here = [dest / path.rsplit("/", 1)[-1] for path in bundle.files]
    said = from_file(dest, bundle)
    return (
        all(f.is_file() for f in here)
        and said.is_file()
        and (said.read_text(encoding="utf-8").strip() == source)
    )


def fetch_bundles(
    ctx: Context, made: dict[Builder, Bundle], dest: Path, sources: dict[Builder, str]
) -> None:
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
                continue
            if first:
                from_file(dest, bundle).write_text(sources[b] + "\n", encoding="utf-8")
                size = landed.stat().st_size // 1048576
                say(f"    {b.platform:<14} {landed.name}  {size} MB")
            # Here now, so gone from there: a bundle per check would
            # otherwise pile up on the builder.
            ctx.host_for(b).capture(f"rm -f {remote_path(b.repo)}/{path}")
    problems(found, "the bundles are not all here.")
