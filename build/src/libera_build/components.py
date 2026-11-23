"""The components as Python packages: libera-core, the converter, a wheel
per platform, and libera-web, the editors with their fonts, dictionaries and
blanks, one wheel for all (notes/plans/pypi-components.md).

Their projects are workspace members, whose build hooks call `build_core` and
`build_web`: `uv sync` builds them from the pinned sources, as pip does where
PyPI has no wheel, and `lb components build` makes this machine's wheels the
same way.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path

from libera.manifest import Manifest
from libera.payload import generate, locate
from libera_build import buildbox, versions
from libera_build.artifacts import core_wheel_name, web_wheel_name
from libera_build.containers import host_arch
from libera_build.process import run_here
from libera_build.relabel import relabel
from libera_build.repo import build_root, git
from libera_build.report import RefusedError, say, step
from libera_build.sources import source_problems

CORE = Path("components", "core")
WEB = Path("components", "web")

# The tag each platform's core wheel gets. glibc 2.34, the newest symbol
# version a Linux core asks for since core 0032, which is RHEL 9: the 0.7 core
# converts on AlmaLinux 9 in the distros check, and tagged 2.35 pip there
# took the sdist and its hour of build instead. macOS 14, the minos of every
# binary in the macOS core, read with otool: tagged 11, as the spike did, pip
# would install it on macOS 11 to 13, where it cannot load.
TAGS = {
    "linux-x86_64": "manylinux_2_34_x86_64",
    "linux-arm64": "manylinux_2_34_aarch64",
    "macos-arm64": "macosx_14_0_arm64",
    "windows-x86_64": "win_amd64",
}


# The sources the converter is built from.
CORE_SOURCES = ("core",)

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
    unpack_web(into, dist)


def build_core(repo: Path, into: Path) -> str:
    """libera-core's bin/, built into `into` from the pinned sources for this
    machine's platform, which it returns.

    Here on macOS and Windows; on Linux in the build container, because V8 8.9
    wants a clang no current distribution has. The tree is fetched only when
    it is not at its pin with the patch queue applied, as `build_web` does,
    and configure and ninja redo only what changed: an hour the first time,
    minutes after.
    """
    platform = locate.get_current_platform()
    if platform not in TAGS:
        msg = f"libera-core builds on {', '.join(TAGS)}, not on {platform}"
        raise RefusedError(msg)
    box = None
    if platform.startswith("linux-"):
        box = buildbox.Box(buildbox.BoxOptions(arch=host_arch()))
    tree = box.options.tree if box else build_root()
    # The Mac's default is an external volume, which another Mac has not got.
    if not box and not tree.parent.is_dir():
        msg = (
            f"the build folder {tree} has no parent folder here: set BUILD_ROOT"
            " (on macOS, to a folder on a case-sensitive volume)"
        )
        raise RefusedError(msg)
    dist = Path("out", "core-dist")
    root = "/build" if box else tree.as_posix()
    steps = [
        "build/engine/build.sh configure",
        "build/engine/build.sh build",
        f"DIST={root}/{dist.as_posix()} build/engine/dist.sh --only core",
    ]
    if source_problems(repo, tree / "src", only=CORE_SOURCES):
        steps.insert(0, f"build/engine/build.sh fetch {' '.join(CORE_SOURCES)}")
    # Here, what is missing is said before the fetch, not after it; in the
    # container, the image has it all.
    if not box:
        steps.insert(0, "build/engine/toolchain.sh check")
    script = "\n".join(["set -e", *steps])
    if not box:
        run_here(["sh", "-c", script], "the core", cwd=repo)
    elif status := box.run(script):
        msg = f"the core: the build container failed ({status})"
        raise RefusedError(msg)
    unpack_core(into, tree / dist, platform)
    generate.write_config(locate.Layout(into.parent / "libera_web", into))
    return platform


def unpack_core(into: Path, dist: Path, platform: str) -> None:
    _unpack(dist / f"core-{platform}.tar.gz", into)
    if not any((into / "bin").glob("x2t*")):
        msg = f"no x2t in core-{platform}.tar.gz, in {dist}"
        raise RefusedError(msg)
    _replace_links(into / "bin")


def unpack_web(into: Path, dist: Path) -> None:
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
        "font_set": manifest.font_set,
        "built": manifest.built,
        "source": manifest.source,
    }
    (into / "payload.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )


# What the two wheels are built from, as paths in the repository, and what
# under them is not: the release's own tooling, the install scripts, the
# bundles' recipes and the tests. Generous on purpose: a change that cannot
# affect the wheels costs one build, a change missed here ships a stale one.
CACHE_INPUTS = (
    "build",
    "components",
    "src/libera/__init__.py",
    "src/libera/manifest.py",
    "src/libera/payload",
)
CACHE_OUTSIDE = (
    "build/src/libera_build/release",
    "build/src/libera_build/origin",
    "build/install",
    "build/flatpak",
    "build/tests",
    "build/test-linux",
)


def _is_input(path: str) -> bool:
    return not path.startswith(tuple(f"{outside}/" for outside in CACHE_OUTSIDE))


def cache_key(repo: Path) -> str | None:
    """What this machine's two wheels are built from, as one hash: the
    commit's blobs under CACHE_INPUTS, and the platform. None when one of
    them has uncommitted changes, which the commit does not describe.

    The version is left out, where it is written in a file that is an input:
    it is a label (relabel), and a release bump would otherwise build both
    again for nothing.
    """
    changed = git(repo, "status", "--porcelain", "--", *CACHE_INPUTS).splitlines()
    if any(_is_input(line[3:]) for line in changed):
        say("    uncommitted changes to what the components are built from: no cache")
        return None
    version = versions.payload_version(repo)
    labelled = {path for path, _ in versions.PLACES}
    key = hashlib.sha256(locate.get_current_platform().encode())
    listing = git(repo, "ls-tree", "-r", "HEAD", "--", *CACHE_INPUTS).splitlines()
    for blob, path in (line.split("\t", 1) for line in listing):
        if not _is_input(path):
            continue
        said = blob
        if path in labelled:
            text = (repo / path).read_text(encoding="utf-8")
            said = hashlib.sha256(text.replace(version, "{}").encode()).hexdigest()
        key.update(f"{said}\t{path}\n".encode())
    return key.hexdigest()[:16]


def wheels(repo: Path, out: Path) -> int:
    """This machine's core wheel, and the editors': `uv build` of the two
    projects, whose hooks build them from the pinned sources. The core's sdist
    too, which is what builds the wheel, so that every run tests it: it is
    what pip builds where PyPI has no wheel. The editors' build takes the core
    wheel just made, not the workspace's, which uv would build a second time.

    Unless they were built before from the same inputs (cache_key): then the
    two wheels kept from that build, labelled with this tree's version, in
    seconds. They are under $BUILD_ROOT/cache/components/, which is safe to
    delete.
    """
    key = cache_key(repo)
    platform = locate.get_current_platform()
    cached = build_root() / "cache" / "components" / f"{platform}-{key}"
    version = versions.payload_version(repo)
    if key and cached.is_dir():
        step(f"libera-core and libera-web, as built before from these inputs ({key})")
        for wheel in sorted(cached.glob("*.whl")):
            say(f"    {relabel(wheel, version, out).name}")
        return 0
    step("libera-core")
    run_here(_uv_build(repo / CORE, out), "building libera-core", cwd=repo)
    step("libera-web")
    argv = _uv_build(
        repo / WEB, out, "--wheel", "--no-sources", "--find-links", str(out)
    )
    run_here(argv, "building libera-web", cwd=repo)
    if key:
        keep = cached.with_name(cached.name + ".tmp")
        shutil.rmtree(keep, ignore_errors=True)
        keep.mkdir(parents=True)
        for name in (core_wheel_name(version, TAGS[platform]), web_wheel_name(version)):
            shutil.copy2(out / name, keep / name)
        keep.rename(cached)
    say(f"\n    the wheels are in {out}")
    return 0


def _uv_build(project: Path, out: Path, *extra: str) -> list[str]:
    return ["uv", "build", "--out-dir", str(out), *extra, str(project)]


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
