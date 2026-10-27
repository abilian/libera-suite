"""`lb components`: the components as Python packages, from a build's artifacts.

Two packages, workspace members of the repository (notes/plans/pypi-components.md):
libera-core, the converter, a wheel per platform, and libera-web, the editors
with their fonts, dictionaries and blanks, one wheel for all. Their files are
a build's and never git's. `fill` puts this machine's into the workspace's two,
which `uv sync` installs editable; `wheels` builds every platform's from a
copy, so the workspace never holds another platform's binaries.
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


def fill(repo: Path, dist: Path, platform: str) -> int:
    """Put the artifacts in `dist` into the workspace's two packages, the core
    for `platform`. The configuration names the editors where they are in
    the workspace, which is not where a wheel puts them."""
    core, web = package_dir(repo, CORE), package_dir(repo, WEB)
    fill_core(core, dist, platform, web)
    fill_web(web, dist)
    say(f"    filled {core.parent.parent} and {web.parent.parent} from {dist}")
    return 0


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
        env = {**os.environ, "LIBERA_CORE_TAG": TAGS[platform]}
        _uv_build(stage_root / "core", out, env)
    step("libera-web")
    fill_web(stage(repo, WEB, stage_root / "web"), dist)
    _uv_build(stage_root / "web", out, None)
    say(f"\n    the wheels are in {out}")
    return 0


def _uv_build(project: Path, out: Path, env: dict[str, str] | None) -> None:
    argv = ["uv", "build", "--wheel", "--out-dir", str(out), str(project)]
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
