"""`lb app flatpak`: the Flatpak, built in a container.

All of it runs in a container, Mac included: flatpak-builder is an ordinary
Linux program, and what it needs is user namespaces and /dev/fuse, which Docker
grants. The bundle is built, installed and run in there: `check` asks the
application whether it could open a window, `smoke` has it convert a document
with the payload it carries. The window itself is `lb linux gui`'s job.

Bundles cannot be cross-built: flatpak-builder runs every module inside
bubblewrap, whose seccomp filter is built for the architecture it runs on. So
each is built on a machine of its own architecture (notes/15-builders.md).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libera_build import buildbox, repo, versions
from libera_build.artifacts import bundle_name, core_name
from libera_build.containers import Engine, Mount, Run, interactive, linux_platform
from libera_build.process import run_quietly
from libera_build.repo import REPO
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from pathlib import Path

APP_ID = "eu.liberasuite.Libera"
WORK = REPO / "build" / "flatpak"
# Beside the .app, in build/out, not in the payload's dist directory: that is a
# *payload* version namespace, and the Flatpak carries the application.
DEST = REPO / "build" / "out"
# What a built bundle must contain. On content, not on an exit code: a bundle
# with no /app/bin/libera is the kind of thing a green build has shipped.
MUST_HAVE = (
    "files/bin/libera",
    f"files/share/applications/{APP_ID}.desktop",
    f"files/share/icons/hicolor/scalable/apps/{APP_ID}.svg",
)


@dataclass(frozen=True)
class FlatpakOptions:
    action: str  # build, wheels, check, smoke, shell, versions, clean
    arch: str = "amd64"
    dist: Path | None = None  # the payload artifacts to bundle


def dockerfile_sum() -> str:
    """The Dockerfile's hash, as a label on the image. The name carries the
    architecture and nothing else, so an image under it is not necessarily the
    one the Dockerfile now describes: the builders kept a flatpak-builder 1.2.3
    image after the Dockerfile moved to 1.4, and would have built every bundle
    to its last step and died there."""
    return hashlib.sha256((WORK / "Dockerfile").read_bytes()).hexdigest()[:16]


def impure_wheels(names: list[str]) -> list[str]:
    """The wheels that are not pure Python. The set is resolved on the builder
    image's Python, not the runtime's, which is safe only while every wheel is
    platform-independent: resolving on the wrong interpreter cannot then have
    picked something different."""
    return [n for n in names if not re.search(r"-(py2\.)?py3-none-any\.whl$", n)]


def diagnose_problems(report: str) -> list[str]:
    """What `libera --diagnose` in the bundle says is wrong. It exits 0 whatever
    it finds, by design: it is a report, not a test, so it is read."""
    found = []
    if not re.search(r"^window *ok", report, re.MULTILINE):
        found.append(
            "--diagnose says no window can be opened in the runtime. The GNOME\n"
            "  runtime supplies GTK and WebKit here, so the runtime-version in\n"
            "  the manifest moved under us."
        )
    if not re.search(r"^found via: *bundled$", report, re.MULTILINE):
        found.append(
            "the bundle does not carry its payload: --diagnose should say\n"
            "  'found via: bundled'. Either the manifest's install step did not\n"
            "  run, or resolve() no longer looks beside the application\n"
            "  (locate.find_bundled_dir())."
        )
    return found


def staged_names(arch: str, fonts: list[str]) -> list[str]:
    """Only what this architecture needs: the other cores are 70 MB each of
    something this bundle can never run, and would live in the build cache.
    The fonts by what is there, but at least one set of them."""
    core = core_name(linux_platform(arch))
    return ["manifest.json", core, "editors.tar.gz", *(fonts or ["fonts-core.tar.gz"])]


class Builder:
    def __init__(self, options: FlatpakOptions, engine: Engine | None = None) -> None:
        self.options = options
        self.engine = engine or Engine.here()
        self.arch = options.arch
        self.image = self.engine.image(f"libera-flatpak-{self.arch}")
        # The GNOME runtime and SDK are several gigabytes, so /var/lib/flatpak
        # lives in a volume. A named one and not a directory on $BUILD_ROOT:
        # flatpak's store is an ostree repo, ostree keeps metadata in user
        # xattrs, and a macOS volume through virtiofs has none ("user xattr:
        # NO"). `lb app flatpak-clean` drops it: about 4 GB per architecture.
        self.volume = f"libera-flatpak-{self.arch}"
        self.app = versions.app_version(REPO)
        self.bundle = bundle_name(self.app, self.arch)
        # The container build's artifacts first, as `lb linux` takes them: a
        # Linux builder builds its payload in the container, so its own
        # out/dist is empty, and `ship` passes --dist where a hand run did not.
        self.dist = (
            options.dist
            or buildbox.exported_dist(self.arch)
            or repo.dist(versions.payload_version(REPO))
        )

    # --- the container ---------------------------------------------------------

    def run_argv(
        self, script: str, *, bundles: bool = False, extra: tuple[str, ...] = ()
    ) -> list[str]:
        """--privileged and /dev/fuse, because flatpak-builder runs each module
        in a bubblewrap user namespace and flatpak's installer mounts revokefs,
        and Docker Desktop's VM will not hand either to an unprivileged
        container. Nothing is trusted less for it: the repository is mounted
        read-write already."""
        mounts = [Mount(self.volume, "/var/lib/flatpak"), Mount(REPO, "/repo")]
        if bundles:
            mounts.append(Mount(DEST, "/bundles", read_only=True))
        return self.engine.run_argv(
            Run(
                self.image,
                ("-c", script),
                self.arch,
                mounts=tuple(mounts),
                workdir="/repo",
                interactive=interactive(),
                extra=("--pull=never", "--privileged", "--device", "/dev/fuse", *extra),
            )
        )

    def build_image(self) -> int:
        return subprocess.call([
            self.engine.name,
            "build",
            "--platform",
            f"linux/{self.arch}",
            "--label",
            f"libera.dockerfile={dockerfile_sum()}",
            "-t",
            self.image,
            str(WORK),
        ])

    def ensure_image(self) -> None:
        self.engine.refuse_remote()
        done = subprocess.run(
            [
                self.engine.name,
                "image",
                "inspect",
                "-f",
                '{{index .Config.Labels "libera.dockerfile"}}',
                self.image,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            step("building the builder image first")
        elif done.stdout.strip() != dockerfile_sum():
            step("the builder image predates build/flatpak/Dockerfile; rebuilding it")
        else:
            return
        if status := self.build_image():
            msg = f"building {self.image} failed ({status})"
            raise RefusedError(msg)

    def call(self, script: str, *, bundles: bool = False) -> int:
        self.ensure_image()
        return subprocess.call(self.run_argv(script, bundles=bundles))

    def owner_flags(self) -> tuple[tuple[str, ...], str]:
        """`--user` for a run, and the chown that hands files back, for docker
        only. Docker runs as real root and writes root's files into the
        repository; rootless podman already writes as you, and saying so again
        asks for a *container* uid that maps to a subordinate host one, which
        owns nothing: EACCES, or artifacts the host cannot delete."""
        if self.engine.name == "podman":
            return (), ":"
        if sys.platform != "win32":
            uid, gid = os.getuid(), os.getgid()
            owner = f"{uid}:{gid}"
            return (
                "--user",
                owner,
            ), f"chown -R {owner} /repo/build/flatpak 2>/dev/null || :"
        msg = "the Flatpak is built on Linux or macOS"
        raise RefusedError(msg)

    # --- the steps ---------------------------------------------------------------

    def wheels(self) -> int:
        """The offline wheel set, assembled aside and moved into place: a set
        that is present but half-filled is worse than one that is absent."""
        step("wheels, for a build with no network")
        versions.stamp_bundled_manifest(REPO, self.dist)
        tmp = WORK / "wheels.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        # libera itself, built here: it is pure Python. Into the scratch
        # directory with --out-dir, and never `rm -rf dist && uv build`, which
        # once deleted the sdist a release had just made.
        run_quietly(
            ["uv", "build", "--wheel", "--out-dir", str(tmp)], "the wheel", cwd=REPO
        )
        # `pip wheel`, not `pip download`: proxy-tools publishes an sdist only,
        # and installing an sdist offline would need its build backend after
        # flatpak-builder has taken the network away. Resolved inside Linux,
        # so pywebview's pyobjc half does not follow. --ignore-requires-python:
        # this image's python3 is 3.11 and libera wants 3.12, and nothing is
        # installed here, only a graph walked -- safe because of the purity
        # check below.
        user, _ = self.owner_flags()
        self.ensure_image()
        status = subprocess.call(
            self.run_argv(
                "set -eu\npip3 wheel --no-cache-dir --ignore-requires-python \\\n"
                "    --wheel-dir build/flatpak/wheels.tmp \\\n"
                "    build/flatpak/wheels.tmp/libera-*.whl",
                extra=("-e", "HOME=/tmp", *user),
            )
        )
        if status:
            return status
        if impure := impure_wheels([p.name for p in tmp.glob("*.whl")]):
            msg = (
                f"not pure-Python: {', '.join(impure)}. Resolving on this image's\n"
                "  3.11 no longer stands in for the runtime's; resolve inside\n"
                "  org.gnome.Sdk instead."
            )
            raise RefusedError(msg)
        shutil.rmtree(WORK / "wheels", ignore_errors=True)
        tmp.rename(WORK / "wheels")
        for wheel in sorted((WORK / "wheels").iterdir()):
            say(f"    {wheel.name}")
        return 0

    def stage_payload(self) -> None:
        """The payload beside the manifest, before flatpak-builder runs: it gives
        the build no network, which is what makes the result reproducible.
        Staged rather than mounted, because flatpak-builder resolves a source
        against the manifest's own directory."""
        step(f"payload, for {linux_platform(self.arch)}")
        fonts = sorted(p.name for p in self.dist.glob("fonts-*.tar.gz"))
        names = staged_names(self.arch, fonts)
        if missing := [n for n in names if not (self.dist / n).is_file()]:
            msg = (
                f"no {', '.join(missing)} in {self.dist}. The bundle carries the\n"
                "  editors, so it needs them built:\n"
                f"    lb payload container --arch {self.arch}\n"
                "  or point at a directory of artifacts: --dist DIR"
            )
            raise RefusedError(msg)
        tmp = WORK / "payload.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        for name in names:
            shutil.copyfile(self.dist / name, tmp / name)
        shutil.rmtree(WORK / "payload", ignore_errors=True)
        tmp.rename(WORK / "payload")

    def build(self) -> int:
        # Always, not "unless wheels/ is there": the wheel carries the manifest
        # the application verifies its payload against, so a wheel built before
        # the manifest was last written ships a bundle that cannot install its
        # payload. Twenty seconds, against shipping that.
        if status := self.wheels():
            return status
        self.stage_payload()
        # The icon and the desktop entry, from the one place each lives:
        # flatpak-builder needs them beside the manifest, and each has a second
        # consumer, so they are copied rather than committed twice.
        shutil.copyfile(REPO / "src" / "libera" / "icon.svg", WORK / f"{APP_ID}.svg")
        shutil.copyfile(
            REPO / "src" / "libera" / "launcher.desktop", WORK / f"{APP_ID}.desktop"
        )
        _, chown_back = self.owner_flags()
        step("flatpak-builder")
        # The runtime version is read out of the manifest rather than repeated
        # here: two places to bump it is one place to forget it. And the files
        # flatpak-builder writes as root are handed back, or the next run stops
        # to ask "mv: replace ...?" in the middle of a release nobody watches.
        script = f"""set -eu
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
rt=$(sed -n "s/^runtime-version: *'\\(.*\\)'$/\\1/p" build/flatpak/{APP_ID}.yml)
[ -n "$rt" ] || {{ echo 'FATAL: no runtime-version in the manifest' >&2; exit 1; }}
flatpak install -y --noninteractive flathub org.gnome.Platform//$rt org.gnome.Sdk//$rt
cd build/flatpak
rm -rf builddir repo
flatpak-builder --force-clean --repo=repo builddir {APP_ID}.yml
flatpak build-bundle repo {self.bundle} {APP_ID}
{chown_back}"""
        if status := self.call(script):
            return status
        step("what came out")
        made = WORK / self.bundle
        if not made.is_file() or made.stat().st_size == 0:
            msg = f"no bundle at {made}"
            raise RefusedError(msg)
        for path in MUST_HAVE:
            if self.call(f"[ -e build/flatpak/builddir/{path} ]"):
                msg = f"the build produced no {path}"
                raise RefusedError(msg)
            say(f"    {path}")
        DEST.mkdir(parents=True, exist_ok=True)
        shipped = DEST / self.bundle
        made.replace(shipped)
        say(f"    {shipped}  {shipped.stat().st_size / 1e6:.0f} MB")
        self.check()
        say(f"\n    install:  flatpak install --user {DEST / self.bundle}")
        say(f"    run:      flatpak run {APP_ID}")
        return 0

    def installed(self, then: str) -> str:
        """Install the bundle, then `then`. The flatpak volume keeps the previous
        build of this version installed, and `install --reinstall` does not
        cover a bundle, so it is uninstalled first."""
        return f"""set -eu
flatpak uninstall -y --noninteractive {APP_ID} >/dev/null 2>&1 || :
flatpak install -y --noninteractive /bundles/{self.bundle} >/dev/null
{then}"""

    def check(self) -> int:
        """Install the bundle and ask it whether it could open a window, which is
        as far as a container goes: no display in here. `--diagnose` already
        answers the half that has ever been wrong: whether the wheels import
        under the runtime's Python, and whether gi finds GTK and WebKit."""
        step("run it, as far as a machine with no display can")
        if not (DEST / self.bundle).is_file():
            msg = f"no bundle at {DEST / self.bundle}"
            raise RefusedError(msg)
        self.ensure_image()
        done = subprocess.run(
            self.run_argv(
                self.installed(f"flatpak run {APP_ID} --diagnose 2>&1"), bundles=True
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        for line in done.stdout.splitlines():
            say(f"    {line}")
        if done.returncode:
            msg = f"the bundle did not run ({done.returncode})\n{done.stderr}"
            raise RefusedError(msg)
        if found := diagnose_problems(done.stdout):
            raise RefusedError("\n".join(found))
        return 0

    def smoke(self) -> int:
        """The payload under the runtime, a different userland from the one that
        compiled it; build/flatpak/runtime-smoke.py says what it checks."""
        if not (DEST / self.bundle).is_file():
            msg = f"no bundle at {DEST / self.bundle}"
            raise RefusedError(msg)
        step("the payload, under the runtime")
        return self.call(
            self.installed("python3 build/flatpak/runtime-smoke.py"), bundles=True
        )

    def clean(self) -> int:
        done = subprocess.run(
            [self.engine.name, "volume", "rm", self.volume],
            capture_output=True,
            check=False,
        )
        say(
            f"removed {self.volume}"
            if done.returncode == 0
            else f"{self.volume} was not there"
        )
        return 0


def run(options: FlatpakOptions) -> int:
    builder = Builder(options)
    actions = {
        "build": builder.build,
        "wheels": builder.wheels,
        "check": builder.check,
        "smoke": builder.smoke,
        "clean": builder.clean,
        "versions": lambda: builder.call("cat /etc/libera-flatpak-image.txt"),
        "shell": lambda: builder.call("exec /bin/bash"),
    }
    return actions[options.action]()
