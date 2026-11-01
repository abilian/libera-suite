"""`lb payload container`: the Linux payload, built in a pinned Ubuntu container.

The reproducible way to build a Linux payload, and the only way to build one
from the Mac. On an Apple Silicon Mac, linux/amd64 runs under Rosetta rather
than qemu, so an x86_64 build is slow-ish but perfectly usable. The builders
run it for their own architecture.

The build engine inside is build/'s shell scripts (build.sh, payload.sh,
dist.sh, smoke.sh); this is everything around them.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from libera_build import repo, versions
from libera_build.containers import Engine, Mount, Run, interactive
from libera_build.repo import REPO, build_root
from libera_build.report import RefusedError, say, step

# One base for both architectures, and a compiler that still differs.
#
# V8 is why the compiler differs: nc-build.py demands clang exactly 13 on Linux
# arm64, and Ubuntu has none after 22.04. See the head of build/docker/Dockerfile.
#
# The base stopped differing because of the other end of the same problem.
# amd64 built on noble, which put the shipped binaries at GLIBC 2.38 and
# GLIBCXX 3.4.32, and the x2t in core-linux-x86_64.tar.gz then refused to load
# on Ubuntu 22.04 and on Debian 12 -- most of the Linux desktop. arm64 had been
# on jammy all along, for V8's sake, so the constraint arm64 was stuck with is
# the portable choice, and taking it for amd64 costs a compiler version nobody
# was attached to.
UBUNTU_RELEASE = "22.04"
UBUNTU_CODENAME = "jammy"
# One digest for both: an OCI image index carrying linux/amd64 and
# linux/arm64/v8, checked with `docker buildx imagetools inspect`.
BASE_DIGEST = "sha256:829f6df217bcbae2b371026e81711d1a787c61b2967ad09d015063663ebafbf7"
CLANG = {"arm64": "13", "amd64": "14"}

# A full build wants about this much room on the build tree's filesystem.
ROOM_GB = 30

# A checkout to a payload, each step a script in build/engine and its
# arguments: what `payload all` runs here and `payload container` in there.
STEPS = (
    ("build.sh", "fetch"),
    ("build.sh", "configure"),
    ("build.sh", "build"),
    ("payload.sh",),
    ("dist.sh", "--fonts", "core"),
    ("smoke.sh",),
)
ALL = "set -e\n" + "\n".join(
    shlex.join([f"build/engine/{name}", *args]) for name, *args in STEPS
)


@dataclass(frozen=True)
class BoxOptions:
    arch: str = "amd64"
    # The build tree, on a real disk beside the native one, and not in a named
    # Docker volume: a volume lives on the VM's disk -- on a Mac the internal
    # one -- and a full build is around 30 GB. The first attempt died with "No
    # space left on device" while $BUILD_ROOT had 295 GB free. Each
    # architecture gets its own directory, so the two never share object trees.
    build_dir: Path | None = None
    volume: str | None = None  # a named volume instead, on the VM's own disk
    memory: str | None = None
    mirror: Path | None = None
    v8_jobs: str | None = None
    core_jobs: str | None = None

    @property
    def tree(self) -> Path:
        return self.build_dir or build_root() / f"linux-{self.arch}"


def base() -> str:
    return f"ubuntu:{UBUNTU_RELEASE}@{BASE_DIGEST}"


def build_args(arch: str) -> list[str]:
    args = {
        "UBUNTU_RELEASE": UBUNTU_RELEASE,
        "UBUNTU_CODENAME": UBUNTU_CODENAME,
        "BASE_DIGEST": BASE_DIGEST,
        "CLANG_VERSION": CLANG[arch],
    }
    return [flag for k, v in args.items() for flag in ("--build-arg", f"{k}={v}")]


def stale(had: str) -> str | None:
    """Why an image under the right name is the wrong image, or None.

    The name carries the architecture and nothing else, so moving the base --
    which is what happened when amd64 left noble for jammy -- leaves a stale
    image under the right name. A build against it succeeds, takes its hours,
    and produces binaries with the old glibc floor, and nothing downstream says
    a word. The image records its base, so it is asked.
    """
    if had == base():
        return None
    return f"it has: {had or 'an image too old to say'}\n    wanted: {base()}"


def mirror_of(options: BoxOptions) -> Path | None:
    """The upstream mirror, when it is there. Optional, and mounted read-only:
    it exists so a re-fetch copies objects from a local clone instead of pulling
    1.5 GB, and a container must never rewrite the host's copy of upstream.
    Docker creates a missing mount source as an empty root-owned directory
    rather than complaining, so an absent mirror is left out, not mounted."""
    found = options.mirror or Path(
        os.environ.get("MIRROR") or Path.home() / "ghorg" / "euro-office"
    )
    return found if found.is_dir() else None


def run_spec(options: BoxOptions, image: str, script: str) -> Run:
    """The container a build step runs in, every flag with its reason."""
    mounts = [Mount(REPO, "/repo")]
    env = {
        "BUILD_ROOT": "/build",
        # Temporaries onto the build tree's filesystem. In the container's own
        # /tmp they go to the VM's disk, and boost's bootstrap alone fills it:
        # "fatal error: error writing to /tmp/ccYezS3O.s: No space left on
        # device", ten minutes in, with the build tree full of room.
        "TMPDIR": "/build/tmp",
        # tar must not restore ownership. Chromium's sysroot tarballs record the
        # uid of whoever rolled them in 2019 (376730), and V8 untars one as root.
        # Under rootless podman that uid is outside the mapped range, chown
        # fails on every entry, and tar exits 2 under a traceback that names
        # neither uids nor engines. GNU tar reads TAR_OPTIONS, so no patch.
        "TAR_OPTIONS": "--no-same-owner",
    }
    mounts.append(
        Mount(options.volume, "/build")
        if options.volume
        else Mount(options.tree, "/build")
    )
    # build.sh computes its jobs from the memory it can see, which is the
    # container's view; the machine running the container is the one that runs
    # out. Six clang processes under Rosetta on a 16 GB Mac had the build
    # killed from outside, with nothing in the log.
    if options.v8_jobs:
        env["V8_BUILD_JOBS"] = options.v8_jobs
    if options.core_jobs:
        env["CORE_BUILD_JOBS"] = options.core_jobs
    if mirror := mirror_of(options):
        mounts.append(Mount(mirror, "/mirror", read_only=True))
        env["MIRROR"] = "/mirror"
        if (mirror / "core-fonts").is_dir():
            env["CORE_FONTS"] = "/mirror/core-fonts"
    extra = ["--pull=never"]
    # A ceiling, because without one the VM takes what the build asks for and
    # the *host* runs out. A cgroup limit turns that into an OOM inside the
    # container, which names the compile that died.
    if options.memory:
        extra += ["-m", options.memory]
    return Run(
        image,
        ("-c", script),
        options.arch,
        mounts=tuple(mounts),
        env=env,
        workdir="/repo",
        # -t on a pipe makes docker fail outright, and -i without a terminal
        # leaves the build waiting on a stdin nobody is attached to.
        interactive=interactive(),
        extra=tuple(extra),
    )


def guarded(script: str) -> str:
    """The script, after a write probe and the temporary directory it needs.

    The probe because the host cannot see this: whether /build is writable
    depends on how the engine maps uids into the mount, and a tree another
    engine wrote gets past every outer check and fails at the first real write,
    forty lines into a fetch.
    """
    return f"""touch /build/.writable 2>/dev/null || {{
    echo "FATAL: /build is not writable from inside the container," >&2
    echo "       as $(id -un) (uid $(id -u)). A tree another engine wrote is" >&2
    echo "       owned by a uid this one does not map to: remove it." >&2
    ls -ld /build >&2
    exit 1
}}
rm -f /build/.writable
mkdir -p /build/tmp && {{ {script}
}}"""


class Box:
    """The build container for one architecture, on this machine's engine."""

    def __init__(self, options: BoxOptions, engine: Engine | None = None) -> None:
        self.options = options
        self.engine = engine or Engine.here()
        self.image = self.engine.image(f"libera-build-linux-{options.arch}")

    def build_image(self) -> int:
        argv = [
            self.engine.name,
            "build",
            "--platform",
            f"linux/{self.options.arch}",
            "-t",
            self.image,
            *build_args(self.options.arch),
            "-f",
            str(REPO / "build" / "docker" / "Dockerfile"),
            str(REPO / "build"),
        ]
        return subprocess.call(argv)

    def recorded_base(self) -> str:
        done = subprocess.run(
            self.engine.run_argv(
                Run(
                    self.image,
                    ("-c", "sed -n 's/^base: *//p' /etc/libera-build-image.txt"),
                    self.options.arch,
                    extra=("--pull=never",),
                )
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        return done.stdout.strip()

    def ensure_image(self) -> None:
        self.engine.refuse_remote()
        if not self.engine.has_image(self.image):
            clang = CLANG[self.options.arch]
            step(f"building the image first ({UBUNTU_CODENAME}, clang {clang})")
        elif why := stale(self.recorded_base()):
            arch = self.options.arch
            step(f"the {arch} image was built on a different base; rebuilding it")
            say(f"    {why}")
        else:
            return
        if status := self.build_image():
            msg = f"building {self.image} failed ({status})"
            raise RefusedError(msg)

    def run(self, script: str) -> int:
        """A shell script in the container, from the repository's root."""
        self.ensure_image()
        if not self.options.volume:
            tree = self.options.tree
            tree.mkdir(parents=True, exist_ok=True)
            # A tree docker left behind is owned by real root on Linux, and
            # rootless podman writes as you: switching engines turns the build
            # into "Permission denied" forty lines in, after the whole fetch.
            if not os.access(tree, os.W_OK):
                msg = (
                    f"{tree} is not writable by you. A build tree docker wrote\n"
                    "  is owned by root, and rootless podman writes as you. Remove\n"
                    f"  it and let this make it again:  sudo rm -rf {tree}"
                )
                raise RefusedError(msg)
        if not mirror_of(self.options):
            say("==> no upstream mirror: cloning from upstream, fonts from the fetched")
            say("    core-fonts. --mirror DIR (or MIRROR=) uses a local clone.")
        argv = self.engine.run_argv(run_spec(self.options, self.image, guarded(script)))
        return subprocess.call(argv)

    def free_gb(self) -> int | None:
        """Room on the build filesystem, asked from inside, where it counts."""
        spec = run_spec(
            self.options, self.image, "df -BG /build | awk 'NR==2 {print $4+0}'"
        )
        done = subprocess.run(
            self.engine.run_argv(spec), capture_output=True, text=True, check=False
        )
        digits = "".join(c for c in done.stdout if c.isdigit())
        return int(digits) if digits else None

    def all(self) -> int:
        """The whole payload: fetch, configure, core, payload, dist, smoke.

        Says the room first and does not stop on it: "enough" depends on what
        is already built, and saying the number is the useful part.
        """
        self.ensure_image()
        if (free := self.free_gb()) is not None:
            say(f"==> {free} GB free on the build filesystem")
            if free < ROOM_GB:
                say(
                    f"    A full build wants ~{ROOM_GB} GB. --build-dir moves the tree."
                )
                say(
                    f"    Volumes from before that default are dead: {self.engine.name}"
                )
                say("    system df, then volume prune -f and builder prune -f.")
        return self.run(ALL)

    def script(self, name: str, args: list[str]) -> int:
        """One build/ script in the container: `dist.sh --fonts core`."""
        return self.run(shlex.join([f"build/engine/{name}", *args]))

    def versions(self) -> int:
        return subprocess.call(
            self.engine.run_argv(
                Run(
                    self.image,
                    ("-c", "cat /etc/libera-build-image.txt"),
                    self.options.arch,
                    extra=("--pull=never",),
                )
            )
        )

    def exported(self) -> Path:
        """Where the built artifacts are on this machine, checked by content.

        A bind-mounted build tree is already here; a volume's is copied out.
        """
        version = versions.payload_version(REPO)
        if not self.options.volume:
            return checked(self.options.tree / "out" / "dist" / version)
        dest = repo.dist(version)
        dest.mkdir(parents=True, exist_ok=True)
        # Into a fresh directory, checked there, and only then beside what is
        # already in dest -- this machine's own artifacts, and an earlier
        # export's, whose manifest.json and tarballs would otherwise pass the
        # check for a copy that brought nothing.
        with tempfile.TemporaryDirectory(dir=dest.parent) as scratch:
            fresh = checked(self.copy_out(version, Path(scratch)))
            for f in fresh.iterdir():
                f.replace(dest / f.name)
        return dest

    def copy_out(self, version: str, into: Path) -> Path:
        """One version's artifacts out of the volume, through a tar pipe, so
        that extraction runs as you and nothing lands owned by root. Both ends'
        statuses, since a pipeline's own is only the last one's."""
        script = f"tar -C /build/out/dist -cf - {shlex.quote(version)}"
        reader = subprocess.Popen(
            self.engine.run_argv(run_spec(self.options, self.image, script)),
            stdout=subprocess.PIPE,
        )
        assert reader.stdout is not None  # ken: PIPE was asked for, so it is there
        written = subprocess.run(
            ["tar", "-C", str(into), "-xf", "-"], stdin=reader.stdout, check=False
        )
        # Our copy of the read end closed: while this process holds it, a
        # writer whose reader stopped early blocks for ever instead of meeting
        # EPIPE.
        reader.stdout.close()
        if reader.wait() or written.returncode:
            msg = (
                f"copying {version} out of the volume {self.options.volume} failed "
                f"({reader.returncode}, then {written.returncode}): "
                "build it first, lb payload container"
            )
            raise RefusedError(msg)
        return into / version


def checked(out: Path) -> Path:
    """A version's artifacts, believed by their content."""
    if not (out / "manifest.json").is_file():
        msg = f"no manifest.json in {out}: build it first, lb payload container"
        raise RefusedError(msg)
    if not list(out.glob("*.tar.gz")):
        msg = f"no tarballs in {out}"
        raise RefusedError(msg)
    return out


def exported_dist(arch: str) -> Path | None:
    """The container build's artifacts for `arch` on this machine, or None:
    what `lb linux` and `lb release matrix` look for when given no directory."""
    out = (
        build_root() / f"linux-{arch}" / "out" / "dist" / versions.payload_version(REPO)
    )
    return out if (out / "manifest.json").is_file() else None
