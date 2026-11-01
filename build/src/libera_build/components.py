"""The components as Python packages: libera-core, the converter, a wheel
per platform, and libera-web, the editors with their fonts, dictionaries and
blanks, one wheel for all (notes/plans/pypi-components.md).

Their projects are workspace members, whose build hooks call `build_core` and
`build_web`: `uv sync` builds them from the pinned sources, as pip does where
PyPI has no wheel. `lb components wheels` builds every platform's from a
build's artifacts, in copies, so the workspace never holds a platform's
binaries.
"""

from __future__ import annotations

import json
import os
import shutil
import tarfile
from pathlib import Path

from libera.manifest import Manifest
from libera.payload import generate, locate
from libera_build.process import run_here
from libera_build.release.phases.here import source_problems
from libera_build.repo import build_root
from libera_build.report import RefusedError, say, step
from libera_build.versions import check_dist

CORE = Path("components", "core")
WEB = Path("components", "web")

# The tag each platform's core wheel gets. glibc 2.35, which a Linux core needs
# (`lb release matrix` found that out); macOS 14, the minos of every binary in
# the macOS core, read with otool: tagged 11, as the spike did, pip would
# install it on macOS 11 to 13, where it cannot load.
TAGS = {
    "linux-x86_64": "manylinux_2_35_x86_64",
    "linux-arm64": "manylinux_2_35_aarch64",
    "macos-arm64": "macosx_14_0_arm64",
    "windows-x86_64": "win_amd64",
}


def package_dir(repo: Path, project: Path) -> Path:
    """The package folder of a component's project: src/libera_core..."""
    return repo / project / "src" / f"libera_{project.name}"


def fill_core(package: Path, dist: Path, platform: str, web: Path) -> None:
    """The core for `platform`, with DoctRenderer.config written for the
    editors at `web`."""
    _empty(package)
    _unpack_core(package, dist, platform)
    generate.write_config(locate.Layout(web, package))


def fill_web(package: Path, dist: Path) -> None:
    """The editors, and the payload.json an installed payload has. No
    platform in it: this wheel is every platform's."""
    _empty(package)
    _unpack_web(package, dist, {})


# The sources the editors are built from, and the fonts and blanks they ship.
WEB_SOURCES = ("sdkjs", "web-apps", "document-templates", "dictionaries", "core-fonts")


def build_web(repo: Path, into: Path, core_bin: Path) -> None:
    """libera-web's files, built into `into` from the pinned sources, with the
    core at `core_bin` to make the slide themes: what its wheel is made of.

    The sources are fetched only when they are not at their pins with the
    patch queue applied: fetching resets and re-patches them, and the build
    then redoes everything. The core is copied, because payload.sh writes its
    DoctRenderer.config beside the x2t it runs.
    """
    engine = repo / "build" / "engine"
    if source_problems(repo, build_root() / "src", only=WEB_SOURCES):
        run_here(
            ["sh", str(engine / "build.sh"), "fetch", *WEB_SOURCES], "fetch", cwd=repo
        )
    work = build_root() / "out" / "web"
    core, payload, dist = work / "core", work / "payload", work / "dist"
    for old in (core, dist):
        shutil.rmtree(old, ignore_errors=True)
    shutil.copytree(core_bin, core, symlinks=True)
    env = {
        **os.environ,
        "CORE_BIN": str(core),
        "PAYLOAD": str(payload),
        "DIST": str(dist),
    }
    run_here(["sh", str(engine / "payload.sh")], "the editors", cwd=repo, env=env)
    run_here(
        ["sh", str(engine / "dist.sh"), "--only", "editors"],
        "the editors",
        cwd=repo,
        env=env,
    )
    _unpack_web(into, dist, {})


def build_core(repo: Path, into: Path) -> str:
    """libera-core's bin/, into `into`, for this machine's platform, which it
    returns.

    ponytail: from the core already built in this machine's build tree, which
    it refuses without; building one here, in the container on Linux, comes
    next.
    """
    if not (build_root() / "out" / "core" / "bin").is_dir():
        msg = f"no core built in {build_root()}: lb payload all"
        raise RefusedError(msg)
    dist = build_root() / "out" / "core-dist"
    shutil.rmtree(dist, ignore_errors=True)
    env = {**os.environ, "DIST": str(dist)}
    argv = ["sh", str(repo / "build" / "engine" / "dist.sh"), "--only", "core"]
    run_here(argv, "the core", cwd=repo, env=env)
    platform = locate.get_current_platform()
    _unpack_core(into, dist, platform)
    generate.write_config(locate.Layout(into.parent / "libera_web", into))
    return platform


def unpack(dest: Path, dist: Path, platform: str) -> int:
    """The whole payload in one folder, the core's bin/ beside the editors, as
    a build tree has it: for LIBERA_PAYLOAD, and for the Windows installer,
    which ships it beside the frozen application. Made aside and renamed into
    place, so a folder that is there is whole."""
    tmp = dest.with_name(f".{dest.name}.tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    _unpack_core(tmp, dist, platform)
    _unpack_web(tmp, dist, {"platform": platform})
    generate.write_config(locate.Layout(tmp, tmp))
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    say(f"    unpacked the {platform} payload from {dist} into {dest}")
    return 0


def _unpack_core(into: Path, dist: Path, platform: str) -> None:
    _unpack(dist / f"core-{platform}.tar.gz", into)
    if not any((into / "bin").glob("x2t*")):
        msg = f"no x2t in core-{platform}.tar.gz, in {dist}"
        raise RefusedError(msg)
    _replace_links(into / "bin")


def _unpack_web(into: Path, dist: Path, extra: dict[str, str]) -> None:
    """The editors and their fonts, and payload.json from the build's
    manifest: what --payload-status and the start window show, the source
    among it, which the AGPL wants said."""
    if not (dist / "manifest.json").is_file():
        msg = f"no manifest.json in {dist}"
        raise RefusedError(msg)
    for name in ("editors.tar.gz", "fonts-core.tar.gz"):
        _unpack(dist / name, into)
    manifest = Manifest.read(dist / "manifest.json")
    record = {
        "payload_version": manifest.payload_version,
        **extra,
        "font_set": manifest.font_set,
        "built": manifest.built,
        "source": manifest.source,
    }
    (into / "payload.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )


def wheels(
    repo: Path,
    dist: Path,
    out: Path,
    stage_root: Path,
    platforms: list[str] | None = None,
) -> int:
    """The core wheel of each platform in `dist`, or of `platforms`, then the
    editors', from artifacts that must be this tree's payload version: the
    wheels are named for it. Staged in `stage_root`, out of the workspace,
    which uv would otherwise take a project in it for a part of."""
    check_dist(repo, dist)
    for platform in platforms or platforms_in(dist):
        step(f"libera-core for {platform}")
        package = stage(repo, CORE, stage_root / "core")
        fill_core(package, dist, platform, package.parent / "libera_web")
        env = {**PREBUILT, "LIBERA_CORE_TAG": TAGS[platform]}
        _uv_build(stage_root / "core", out, env)
    step("libera-web")
    fill_web(stage(repo, WEB, stage_root / "web"), dist)
    # Its build requires libera-core, which is in `out` now.
    _uv_build(stage_root / "web", out, PREBUILT, "--find-links", str(out))
    say(f"\n    the wheels are in {out}")
    return 0


# The copies `wheels` builds from are filled already: the hooks take them as
# they are.
PREBUILT = {**os.environ, "LIBERA_PREBUILT": "1"}


def _uv_build(project: Path, out: Path, env: dict[str, str], *extra: str) -> None:
    argv = ["uv", "build", "--wheel", "--out-dir", str(out), *extra, str(project)]
    run_here(argv, "building a wheel", cwd=project, env=env)


def stage(repo: Path, project: Path, dest: Path) -> Path:
    """A copy of a component's project without its files, to fill and build
    from: its package folder."""
    shutil.rmtree(dest, ignore_errors=True)
    package = package_dir(dest.parent, Path(dest.name))
    package.mkdir(parents=True)
    for name in ("pyproject.toml", "README.md", "hatch_build.py"):
        if (repo / project / name).is_file():
            shutil.copy2(repo / project / name, dest)
    shutil.copy2(package_dir(repo, project) / "__init__.py", package)
    return package


def platforms_in(dist: Path) -> list[str]:
    """The platforms whose core is in `dist`, refusing one with no tag."""
    found = sorted(
        p.name.removeprefix("core-").removesuffix(".tar.gz")
        for p in dist.glob("core-*.tar.gz")
    )
    if not found:
        msg = f"no core-*.tar.gz in {dist}"
        raise RefusedError(msg)
    if unknown := [p for p in found if p not in TAGS]:
        msg = f"no wheel tag for {', '.join(unknown)}: add it to TAGS"
        raise RefusedError(msg)
    return found


def _empty(package: Path) -> None:
    """Everything in a package folder goes but its __init__.py."""
    for entry in package.iterdir():
        if entry.name == "__init__.py":
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def _unpack(tarball: Path, dest: Path) -> None:
    if not tarball.is_file():
        msg = f"no {tarball.name} in {tarball.parent}"
        raise RefusedError(msg)
    with tarfile.open(tarball) as tar:
        tar.extractall(dest, filter="data")


def _replace_links(bin_dir: Path) -> None:
    """Leave no symlinks: a wheel holds none, and hatchling stores a link's
    target again under the link's name, which made the macOS core 53 MB
    rather than 45.

    The binaries ask for the versioned names only -- libicuuc.74.dylib,
    libicuuc.so.74, ooxmlsignature.framework/Versions/1/ooxmlsignature, read
    with otool on the macOS core -- so the file a versioned link names takes
    the link's place, and the other links go: libicuuc.dylib, and the
    framework's.
    """
    links = [
        Path(top, name)
        for top, dirs, files in os.walk(bin_dir)
        for name in dirs + files
        if Path(top, name).is_symlink()
    ]
    # ponytail: "versioned" is a digit in the name, which holds for the ICU
    # and framework links the cores have; read the binaries' load commands
    # if a core grows a link this misjudges.
    for link in links:
        target = link.resolve()
        if any(c.isdigit() for c in link.name) and target.is_file():
            target.replace(link)
    for link in links:
        if link.is_symlink():
            link.unlink()
