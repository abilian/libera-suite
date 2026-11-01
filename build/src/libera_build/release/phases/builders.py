"""`build` and `bundles`: `lb` on the remote builders, in parallel.

Every remote builder alike: each is told what its platform builds, each result
is looked for there and then brought here. A Linux builder builds its core in
the container and bundles a Flatpak; the Windows one builds with its own
toolchain and makes the installer. Windows used to be built and published by
hand, from the Windows machine, as a release of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera_build import versions
from libera_build.artifacts import (
    MIN_BUNDLE_BYTES,
    MIN_CORE_BYTES,
    bundle_name,
    core_name,
    installer_name,
)
from libera_build.hosts import remote_path
from libera_build.inventory import dist_of
from libera_build.release.builds import check_remote_file, run_builds
from libera_build.report import problems, say, step

if TYPE_CHECKING:
    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context


def arch_suffix(b: Builder) -> str:
    return f" --arch {b.arch}" if b.arch else ""


def version_dist(b: Builder, version: str) -> str:
    """That version's directory on the builder, for a command line there."""
    return remote_path(f"{dist_of(b)}/{version}")


def build_command(b: Builder) -> str:
    """What a builder runs to leave its core, and the shared pair, in its dist
    directory. On Linux, the container, whose glibc decides the oldest
    distribution the core loads on. Elsewhere, the machine's own toolchain,
    which `payload all` checks before its hours of building."""
    if b.platform.startswith("linux-"):
        return f"payload container{arch_suffix(b)}"
    return "payload all"


@dataclass(frozen=True)
class Bundle:
    """What users download from a builder: the `lb` command that makes it, and
    the files it leaves under the checkout there, the bundle itself first."""

    command: str
    files: tuple[str, ...]


def bundle_of(b: Builder, app: str, payload_dist: str) -> Bundle | None:
    """A Flatpak per Linux architecture; the installer on Windows, with the
    SHA-256 that install.ps1 checks the download against. None for a Mac:
    macOS ships through Homebrew, which builds from source."""
    if b.platform.startswith("linux-"):
        return Bundle(
            f"app flatpak --dist {payload_dist}{arch_suffix(b)}",
            (f"build/out/{bundle_name(app, b.arch or '')}",),
        )
    if b.platform.startswith("windows-"):
        setup = f"build/out/bundles/{installer_name(app)}"
        return Bundle("app windows", (setup, f"{setup}.sha256"))
    return None


def build(ctx: Context) -> None:
    """Every remote builder's core, each on its own machine."""
    if not ctx.remotes:
        say("    no remote builders; nothing to do")
        return
    version = versions.payload_version(ctx.root)

    def verify_core(b: Builder, host: Host) -> str | None:
        path = remote_path(f"{dist_of(b)}/{version}/{core_name(b.platform)}")
        return check_remote_file(b, host, path, MIN_CORE_BYTES)

    run_builds(ctx, ctx.remotes, build_command, verify_core, "building")


def bundles(ctx: Context) -> None:
    """What users download, each made on a machine of its platform. A Flatpak
    cannot be cross-built: flatpak-builder runs every module inside bubblewrap,
    whose seccomp filter is built for the architecture it runs on, and
    qemu-user does not carry one across. See notes/15-builders.md.
    """
    version = versions.payload_version(ctx.root)
    app = versions.app_version(ctx.root)
    made = {
        b: bundle
        for b in ctx.remotes
        if (bundle := bundle_of(b, app, version_dist(b, version)))
    }
    if not made:
        say("    no remote builders that make a bundle; nothing to do")
        return

    def verify_bundle(b: Builder, host: Host) -> str | None:
        path = f"{remote_path(b.repo)}/{made[b].files[0]}"
        return check_remote_file(b, host, path, MIN_BUNDLE_BYTES)

    run_builds(ctx, list(made), lambda b: made[b].command, verify_bundle, "bundling")
    fetch_bundles(ctx, made)


def fetch_bundles(ctx: Context, made: dict[Builder, Bundle]) -> None:
    """Bring every bundle here, where `publish` uploads them from, so that one
    directory holds the whole release."""
    step("collecting the bundles")
    dest = ctx.root / "build" / "out" / "bundles"
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
