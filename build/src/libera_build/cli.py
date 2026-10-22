"""Build, check and release Libera Suite: everything the Makefile does not.

    lb --help                  the groups, and every command
    lb payload --help          the commands in one group
    lb payload core --help     one command: its options and examples

The scripts in build/ do the work, and each command says which one it runs
before running it. What this adds is a name for every knob: each script takes
environment variables, and every one a user may want is an option here, whose
help names the variable. The variables still work.

Each command is a pure function from its arguments to the steps it would run,
a command line and its environment each, and `main` runs them in order,
stopping at the first that fails. So what a command does is testable without
doing it.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from unittest import mock

from libera_build import (
    bench as bench_,
    buildbox,
    fidelity as fidelity_,
    flatpak,
    linux,
    matrix,
    released_gui,
    tidy,
)
from libera_build.buildbox import BoxOptions
from libera_build.containers import host_arch
from libera_build.flatpak import FlatpakOptions
from libera_build.linux import LinuxOptions
from libera_build.matrix import MatrixOptions
from libera_build.origin import verbs
from libera_build.origin.verbs import OriginOptions
from libera_build.release.on import OnOptions, on
from libera_build.release.plan import PHASES
from libera_build.release.ship import ShipOptions, ship
from libera_build.released_gui import ReleasedGuiOptions
from libera_build.repo import REPO, build_root
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from collections.abc import Callable


# --- steps -----------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """One command line, run from the repository root, with extra environment."""

    argv: tuple[str, ...]
    env: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        shown = " ".join(f"{k}={shlex.quote(v)}" for k, v in self.env.items())
        return f"{shown + ' ' if shown else ''}{shlex.join(self.argv)}"


@dataclass(frozen=True)
class Call:
    """A step done in this process: `release ship`, which says its own steps.

    With the environment its options ask for, for the length of the call, as
    a script gets it: code here reads $BUILD_ROOT where the script it replaced
    did, and --build-root was otherwise taken and dropped.
    """

    fn: Callable[..., int]
    args: tuple[object, ...] = ()
    kwargs: dict[str, object] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)

    def run(self) -> int:
        with mock.patch.dict(os.environ, self.env):
            return self.fn(*self.args, **self.kwargs)


# What a command plans: processes to run, and calls into this process.
Steps = list[Step | Call]


def run_steps(steps: Steps) -> int:
    """Run steps in order, saying each process first, stopping at the first
    that fails. A refusal (`RefusedError`) is said as a sentence: a failure."""
    try:
        for step in steps:
            if status := run_step(step):
                return status
    except RefusedError as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        return 1
    return 0


def run_step(step: Step | Call) -> int:
    if isinstance(step, Call):
        return step.run()
    print(f"+ {step}", flush=True)
    return subprocess.call(step.argv, cwd=REPO, env={**os.environ, **step.env})


def sh(script: str, *args: str, env: dict[str, str] | None = None) -> Step:
    """A script in build/, by its path from the repository root."""
    return Step(("sh", f"build/{script}", *args), env or {})


# --- options that are environment variables ------------------------------------


class Knob(NamedTuple):
    """An option that reaches a script as an environment variable. A switch
    takes no value, and is the variable set to 1."""

    flag: str
    env: str
    help: str
    metavar: str | None = None
    choices: tuple[str, ...] | None = None
    switch: bool = False

    @property
    def dest(self) -> str:
        return self.flag.lstrip("-").replace("-", "_")


ARCH = Knob(
    "--arch", "ARCH", "amd64 or arm64; default amd64", choices=("amd64", "arm64")
)
# The same variable, where the default is the machine it runs on.
ARCH_HERE = ARCH._replace(help="amd64 or arm64; default this machine's")
BUILD_ROOT = Knob(
    "--build-root",
    "BUILD_ROOT",
    "where sources and builds live; default ~/euro-office-build on Linux, "
    "the external volume on macOS",
    "DIR",
)
MIRROR = Knob(
    "--mirror", "MIRROR", "local clones to fetch from instead of GitHub", "DIR"
)
V8_JOBS = Knob("--v8-jobs", "V8_BUILD_JOBS", "parallel jobs for V8", "N")
CORE_JOBS = Knob(
    "--core-jobs", "CORE_BUILD_JOBS", "parallel jobs for core's own ninja", "N"
)
DIST = Knob(
    "--dist",
    "DIST",
    "the built artifacts to use (default: the payload version's)",
    "DIR",
)
MEMORY = Knob(
    "--memory", "DOCKER_MEMORY", "a ceiling for the container, e.g. 12g", "SIZE"
)
BUILD_DIR = Knob(
    "--build-dir",
    "BUILD_DIR",
    "the container's build tree; default $BUILD_ROOT/linux-<arch>",
    "DIR",
)
PAYLOAD = Knob(
    "--payload",
    "PAYLOAD",
    "an unpacked payload to mount as is, when no artifacts match this checkout",
    "DIR",
)
# Not LANG: every shell here has one, and it would reach every container.
LINUX_LANG = Knob(
    "--lang",
    "LINUX_LANG",
    "the container's LANG, the language the host speaks there, e.g. fr_FR.UTF-8",
    "LOCALE",
)
VOLUME = Knob(
    "--volume", "VOLUME", "a named Docker volume instead of --build-dir", "NAME"
)
DRY = Knob("--dry-run", "DRY", "say, change nothing", switch=True)
QUICK = Knob("--quick", "QUICK", "sizes only", switch=True)
WHEEL = Knob(
    "--wheel",
    "WHEEL",
    "the manifest from a wheel, or `pypi`: this version's",
    "WHEEL",
)
DISTROS = Knob("--distros", "DISTROS", "images to try", '"IMAGE ..."')
ARCHES = Knob("--arches", "ARCHES", "architectures to try", '"x86_64 arm64"')
YES = Knob("--yes", "YES", "delete; without it, a dry run", switch=True)


def add_knobs(parser: argparse.ArgumentParser, *knobs: Knob) -> None:
    for knob in knobs:
        help_ = f"{knob.help} (env {knob.env})"
        if knob.switch:
            parser.add_argument(
                knob.flag, dest=knob.dest, action="store_true", help=help_
            )
        else:
            parser.add_argument(
                knob.flag,
                dest=knob.dest,
                metavar=knob.metavar,
                choices=knob.choices,
                help=help_,
            )
    parser.set_defaults(knobs=knobs)


def env_of(args: argparse.Namespace) -> dict[str, str]:
    """The environment the options given ask for."""
    values = {k: getattr(args, k.dest) for k in args.knobs}
    return {
        k.env: "1" if k.switch else str(v)
        for k, v in values.items()
        if v is not None and v is not False
    }


# --- the commands --------------------------------------------------------------
#
# Each takes the parsed arguments and returns the steps it would run. They are
# small on purpose: the work is in the scripts.


def toolchain_first(args: argparse.Namespace, *steps: Step) -> Steps:
    """A minute's check before an hour's build: a missing package otherwise
    arrives as a compiler error forty minutes in."""
    return [sh("engine/toolchain.sh", "check", env=env_of(args)), *steps]


def payload_fetch(args: argparse.Namespace) -> Steps:
    return toolchain_first(
        args, sh("engine/build.sh", "fetch", *args.repos, env=env_of(args))
    )


def payload_configure(args: argparse.Namespace) -> Steps:
    return toolchain_first(args, sh("engine/build.sh", "configure", env=env_of(args)))


def payload_core(args: argparse.Namespace) -> Steps:
    return toolchain_first(args, sh("engine/build.sh", "build", env=env_of(args)))


def payload_assemble(args: argparse.Namespace) -> Steps:
    return toolchain_first(args, sh("engine/payload.sh", env=env_of(args)))


def payload_dist(args: argparse.Namespace) -> Steps:
    extra = ["--manifest-only"] if args.manifest_only else []
    return toolchain_first(
        args, sh("engine/dist.sh", "--fonts", args.fonts, *extra, env=env_of(args))
    )


def payload_all(args: argparse.Namespace) -> Steps:
    env = env_of(args)
    return toolchain_first(
        args, *(sh(f"engine/{name}", *rest, env=env) for name, *rest in buildbox.STEPS)
    )


def box_options(args: argparse.Namespace) -> BoxOptions:
    return BoxOptions(
        arch=given(args, ARCH) or "amd64",
        build_dir=path_given(args, BUILD_DIR),
        volume=given(args, VOLUME),
        memory=given(args, MEMORY),
        mirror=path_given(args, MIRROR),
        v8_jobs=given(args, V8_JOBS),
        core_jobs=given(args, CORE_JOBS),
    )


def payload_container(args: argparse.Namespace) -> Steps:
    box = buildbox.Box(box_options(args))
    if args.shell:
        return [Call(box.run, ("exec /bin/bash",))]
    if args.versions:
        return [Call(box.versions)]
    if args.image:
        return [Call(box.build_image)]
    if args.rest:
        return [Call(box.script, (args.rest[0], args.rest[1:]))]
    return [Call(box.all)]


def payload_export(args: argparse.Namespace) -> Steps:
    """The directory on stdout, alone, so that a caller can read it."""
    return [Call(print_exported, (box_options(args),))]


def print_exported(options: BoxOptions) -> int:
    print(buildbox.Box(options).exported())
    return 0


def payload_install(args: argparse.Namespace) -> Steps:
    if args.source:
        return [
            Step(("uv", "run", "libera", "--payload-install", "--from", args.source))
        ]
    return [Call(install_exported, (box_options(args),))]


def install_exported(options: BoxOptions) -> int:
    """The container build's artifacts, installed the way a user installs."""
    where = buildbox.Box(options).exported()
    return run_step(
        Step(("uv", "run", "libera", "--payload-install", "--from", str(where)))
    )


def payload_smoke(args: argparse.Namespace) -> Steps:
    return [sh("engine/smoke.sh", env=env_of(args))]


def payload_patches(_args: argparse.Namespace) -> Steps:
    return [sh("engine/check-patches.sh")]


def payload_status(_args: argparse.Namespace) -> Steps:
    return [Step(("uv", "run", "libera", "--payload-status"))]


def toolchain(args: argparse.Namespace) -> Steps:
    return toolchain_steps(args.action, sys.platform, dry=args.dry_run)


def toolchain_steps(action: str, platform: str, *, dry: bool = False) -> Steps:
    """On Windows, `install` is build/windows/windows-setup.ps1: Visual Studio's
    C++ tools and SDK, Strawberry Perl, NASM, Inno Setup, each checked on the
    file the build uses rather than on an installer's exit code, which
    toolchain.sh's list of winget ids cannot do. It wants an elevated
    PowerShell, which an administrator's ssh session is (measured).

    --dry-run says what would be installed and changes nothing: the setup
    script's -DryRun on Windows, `list` elsewhere. For a machine another tool
    has set up, so that nothing is installed twice.
    """
    if platform == "win32" and action == "install":
        script = "build/windows/windows-setup.ps1"
        argv = ("powershell", "-ExecutionPolicy", "Bypass", "-File", script)
        return [Step((*argv, "-DryRun") if dry else argv)]
    if action == "install" and dry:
        return [sh("engine/toolchain.sh", "list")]
    return [sh("engine/toolchain.sh", action)]


def app_macos(args: argparse.Namespace) -> Steps:
    return [
        sh("macos/macos-app.sh", env={"STANDALONE": "1"} if args.standalone else {})
    ]


def app_flatpak(args: argparse.Namespace) -> Steps:
    options = FlatpakOptions(
        args.action, arch=given(args, ARCH) or host_arch(), dist=path_given(args, DIST)
    )
    return [Call(flatpak.run, (options,))]


def app_windows(_args: argparse.Namespace) -> Steps:
    return [sh("windows/windows-app.sh")]


def app_windows_gui_test(_args: argparse.Namespace) -> Steps:
    return [sh("windows/gui-test.sh")]


def given(args: argparse.Namespace, knob: Knob) -> str | None:
    """A knob's value: the option, else its environment variable, which keeps
    working for a command done in this process as it did for a script."""
    # A knob the command does not take is not given: `payload install` reads
    # the container's options without offering all of them.
    return getattr(args, knob.dest, None) or os.environ.get(knob.env) or None


def path_given(args: argparse.Namespace, knob: Knob) -> Path | None:
    value = given(args, knob)
    return Path(value).expanduser() if value else None


def switched(args: argparse.Namespace, knob: Knob) -> bool:
    """A switch: given, or its variable set to 1."""
    return bool(getattr(args, knob.dest, False)) or os.environ.get(knob.env) == "1"


def linux_(args: argparse.Namespace) -> Steps:
    options = LinuxOptions(
        action=args.action,
        arch=given(args, ARCH),
        dist=path_given(args, DIST),
        payload=path_given(args, PAYLOAD),
        lang=given(args, LINUX_LANG),
        pytest_args=tuple(args.rest),
    )
    return [Call(linux.run, (options,))]


def release_ship(args: argparse.Namespace) -> Steps:
    options = ShipOptions(
        phases=tuple(args.phases),
        only=tuple(args.only or ()),
        yes=args.yes,
        dry_run=args.dry_run,
    )
    return [Call(ship, (options,))]


def release_plan(args: argparse.Namespace) -> Steps:
    args.dry_run, args.yes = True, False
    return release_ship(args)


def release_origin(args: argparse.Namespace) -> Steps:
    options = OriginOptions(
        args.action,
        dry_run=switched(args, DRY),
        quick=switched(args, QUICK),
        wheel=given(args, WHEEL),
    )
    return [Call(verbs.run, (options,))]


def release_matrix(args: argparse.Namespace) -> Steps:
    options = MatrixOptions(
        dist=path_given(args, DIST),
        distros=tuple((given(args, DISTROS) or "").split()),
        arches=tuple((given(args, ARCHES) or "").split()),
    )
    return [Call(matrix.run, (options,))]


def release_released_gui(args: argparse.Namespace) -> Steps:
    options = ReleasedGuiOptions(on=args.on, doc=args.doc)
    return [Call(released_gui.run, (options,))]


def on_(args: argparse.Namespace) -> Steps:
    if not args.rest:
        msg = "lb on PLATFORM COMMAND: which lb command to run there?"
        raise SystemExit(msg)
    options = OnOptions(args.platform, tuple(args.rest), update=args.update)
    return [Call(on, (options,))]


def tidy_(args: argparse.Namespace) -> Steps:
    root = path_given(args, BUILD_ROOT) or build_root()
    return [Call(tidy.tidy, (REPO, root), {"yes": switched(args, YES)})]


def bench(args: argparse.Namespace) -> Steps:
    return [Call(bench_.main, (list(args.rest),))]


def fidelity(args: argparse.Namespace) -> Steps:
    return [Call(fidelity_.main, (list(args.rest),))]


# --- the parser ----------------------------------------------------------------


def examples(*lines: str) -> str:
    return "examples:\n" + "\n".join(f"  lb {line}" for line in lines)


class Groups:
    """Subcommands two deep, each with a one-line summary and its examples.

    Every command added is also kept in `listing`, which the top-level help
    prints: the list cannot fall behind the commands it lists.
    """

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        self._top = parser.add_subparsers(dest="group", metavar="GROUP", required=True)
        self.listing: list[tuple[str, str]] = []

    def group(self, name: str, summary: str, epilog: str = "") -> Group:
        parser = self._top.add_parser(
            name,
            help=summary,
            description=summary,
            epilog=epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        subparsers = parser.add_subparsers(
            dest="command", metavar="COMMAND", required=True
        )
        return Group(self, name, subparsers)

    def leaf(
        self,
        name: str,
        summary: str,
        func: Callable[[argparse.Namespace], Steps],
        *knobs: Knob,
        epilog: str = "",
    ) -> argparse.ArgumentParser:
        """A command with no group above it."""
        self.listing.append((name, summary))
        return add_command(self._top, name, summary, func, *knobs, epilog=epilog)


class Group:
    """One group's commands: `payload fetch`, `payload core`..."""

    def __init__(
        self,
        groups: Groups,
        name: str,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    ) -> None:
        self._groups, self._name, self._subparsers = groups, name, subparsers

    def command(
        self,
        name: str,
        summary: str,
        func: Callable[[argparse.Namespace], Steps],
        *knobs: Knob,
        epilog: str = "",
    ) -> argparse.ArgumentParser:
        self._groups.listing.append((f"{self._name} {name}", summary))
        return add_command(self._subparsers, name, summary, func, *knobs, epilog=epilog)


def add_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    summary: str,
    func: Callable[[argparse.Namespace], Steps],
    *knobs: Knob,
    epilog: str = "",
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        name,
        help=summary,
        description=summary,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_knobs(parser, *knobs)
    parser.set_defaults(func=func)
    return parser


def add_payload(groups: Groups) -> None:
    g = groups.group(
        "payload",
        "the editor payload: build it here or in a container, check it, install it",
        "Built here, the order is fetch, configure, core, assemble, then dist for\n"
        "the tarballs; `all` runs the five, then smoke, as `container` does in\n"
        "the container. Each checks the toolchain first.\n\n"
        + examples("payload all", "payload container --arch arm64", "payload install"),
    )
    p = g.command(
        "fetch",
        "clone or reset the sources to the pinned SHAs, and apply the patch queue",
        payload_fetch,
        BUILD_ROOT,
        MIRROR,
        epilog=examples(
            "payload fetch", "payload fetch core sdkjs --mirror ~/ghorg/euro-office"
        ),
    )
    p.add_argument("repos", nargs="*", metavar="REPO", help="only these (default: all)")
    g.command(
        "configure",
        "cmake configure only: missing tools and CMake gaps in minutes",
        payload_configure,
        BUILD_ROOT,
    )
    g.command(
        "core",
        "x2t and the native libraries (long: V8 alone is ~30 min)",
        payload_core,
        BUILD_ROOT,
        V8_JOBS,
        CORE_JOBS,
        epilog=examples("payload core", "payload core --v8-jobs 4 --core-jobs 8"),
    )
    g.command(
        "assemble",
        "sdkjs, web-apps, fonts, blanks, dictionaries, branding (~4 min)",
        payload_assemble,
        BUILD_ROOT,
    )
    p = g.command(
        "dist",
        "the tarballs and the manifest a release is made of",
        payload_dist,
        BUILD_ROOT,
        epilog=examples(
            "payload dist", "payload dist --fonts full", "payload dist --manifest-only"
        ),
    )
    p.add_argument(
        "--fonts", choices=("core", "full"), default="core", help="default: core"
    )
    p.add_argument(
        "--manifest-only", action="store_true", help="the manifest, over what is there"
    )
    g.command(
        "all",
        "fetch, configure, core, assemble, dist, then smoke: a checkout to a payload",
        payload_all,
        BUILD_ROOT,
        MIRROR,
        V8_JOBS,
        CORE_JOBS,
    )
    p = g.command(
        "container",
        "the whole Linux build in the pinned Ubuntu container, or one build/ script",
        payload_container,
        ARCH,
        BUILD_ROOT,
        BUILD_DIR,
        VOLUME,
        MEMORY,
        MIRROR,
        V8_JOBS,
        CORE_JOBS,
        epilog="Anything after the options is one build/ script and its arguments,\n"
        "run in the container instead of the whole build.\n\n"
        + examples(
            "payload container",
            "payload container --arch arm64 --memory 12g",
            "payload container --build-dir /Volumes/T7/linux-amd64",
            "payload container --arch arm64 dist.sh --fonts core",
        ),
    )
    p.set_defaults(passes_on=True)
    for flag, what in (
        ("--shell", "a shell in the build container"),
        ("--versions", "what the build image is pinned to"),
        ("--image", "build, or rebuild, the build image"),
    ):
        p.add_argument(flag, action="store_true", help=what)
    g.command(
        "export",
        "copy the container build's artifacts here, and print where",
        payload_export,
        ARCH,
        BUILD_ROOT,
        BUILD_DIR,
        VOLUME,
    )
    p = g.command(
        "install",
        "install built artifacts the way a user would, every hash checked",
        payload_install,
        ARCH,
        BUILD_ROOT,
        BUILD_DIR,
        VOLUME,
        epilog=examples(
            "payload install                  the container build's",
            "payload install --from $BUILD_ROOT/out/dist/0.4   a native build's",
        ),
    )
    p.add_argument(
        "--from", dest="source", metavar="DIR", help="default: the container build's"
    )
    g.command(
        "smoke",
        "the converter: fonts, docx -> odt -> docx, docx -> pdf",
        payload_smoke,
        BUILD_ROOT,
    )
    g.command(
        "patches",
        "does the patch queue still apply to the pinned SHAs? (~20 s)",
        payload_patches,
    )
    g.command(
        "status", "which payload this checkout runs, and where from", payload_status
    )


def add_toolchain(groups: Groups) -> None:
    g = groups.group(
        "toolchain",
        "is this machine equipped to build the payload, and what to install",
        examples("toolchain check", "toolchain list", "toolchain install"),
    )
    for action, summary in (
        ("check", "what is missing, in a second rather than an hour into a build"),
        ("list", "the packages this distribution needs, installing nothing"),
        ("install", "install them"),
    ):
        p = g.command(action, summary, toolchain)
        p.set_defaults(action=action, dry_run=False)
        if action == "install":
            p.add_argument(
                "--dry-run",
                action="store_true",
                help="say what would be installed, and install nothing",
            )


def add_app(groups: Groups) -> None:
    g = groups.group(
        "app",
        "the applications users install: the .app, the Flatpak, the Windows installer",
        examples(
            "app macos --standalone", "app flatpak --arch arm64", "app flatpak-check"
        ),
    )
    p = g.command("macos", "Libera.app, ad-hoc signed", app_macos)
    p.add_argument(
        "--standalone",
        action="store_true",
        help="with Python, libera and the payload inside; default: runs this checkout",
    )
    for name, action, summary in (
        ("flatpak", "build", "wheels, then the bundle, then the check"),
        ("flatpak-wheels", "wheels", "the offline wheel set on its own"),
        ("flatpak-check", "check", "install the built bundle and run --diagnose in it"),
        ("flatpak-smoke", "smoke", "and have it convert a document"),
        ("flatpak-clean", "clean", "drop the runtime volume (~4 GB per architecture)"),
        ("flatpak-shell", "shell", "a shell in the builder container"),
        ("flatpak-versions", "versions", "what the builder image is pinned to"),
    ):
        p = g.command(name, summary, app_flatpak, ARCH_HERE, DIST)
        p.set_defaults(action=action)
    g.command("windows", "the Windows installer, on Windows", app_windows)
    g.command(
        "windows-gui-test",
        "the suite's gui tier in a real window, on Windows, in the desktop session",
        app_windows_gui_test,
    )


def add_linux(groups: Groups) -> None:
    g = groups.group(
        "linux",
        "this repository's checks on Linux, in a container: the one place they run",
        "All need a Linux payload: `payload container`, or --dist DIR.\n\n"
        + examples(
            "linux lint",
            "linux test -k bridge",
            "linux gui --arch arm64",
            "linux gui --lang fr_FR.UTF-8",
        ),
    )
    for action, summary in (
        ("test", "the suite; anything after it goes to pytest"),
        ("lint", "the type checkers, where the Linux branches are live"),
        ("gui", "a real GTK window under Xvfb, screenshotted"),
        ("gui-test", "the same window, as the suite's gui tier (tests/d_gui)"),
        ("dialog", "the GTK question the host asks, answered"),
        ("versions", "what the test image is pinned to"),
        ("shell", "a shell in the test container"),
        ("image", "build, or rebuild, the test image"),
    ):
        p = g.command(action, summary, linux_, ARCH_HERE, DIST, PAYLOAD, LINUX_LANG)
        p.set_defaults(action=action, passes_on=action == "test")


PHASE_LIST = "\n".join(f"  {name:<9} {what}" for name, what in PHASES.items())


def add_release(groups: Groups) -> None:
    g = groups.group(
        "release",
        "a release: built on the builders, published, read back",
        "`ship` is the whole release; the others are its parts, and the checks.\n"
        "The builders are build/builders.toml.\n\n"
        + examples(
            "release status",
            "release plan",
            "release ship",
            "release ship build bundles --only linux-arm64",
        ),
    )
    for name, summary, func in (
        ("ship", "the phases, in order: all of them unless named", release_ship),
        ("plan", "what ship would do, running nothing", release_plan),
    ):
        p = g.command(
            name,
            summary,
            func,
            epilog=f"phases, always run in this order:\n{PHASE_LIST}\n\n"
            + examples(
                f"release {name}", f"release {name} build bundles --only linux-arm64"
            ),
        )
        p.add_argument(
            "phases",
            nargs="*",
            choices=[*PHASES, []],
            metavar="PHASE",
            help="the phases to run, listed below (default: all of them)",
        )
        p.add_argument(
            "--only",
            action="append",
            metavar="PLATFORM",
            help="one builder, by its platform in build/builders.toml; repeatable",
        )
        if name == "ship":
            p.add_argument(
                "--yes", action="store_true", help="do not stop to confirm PyPI"
            )
            p.add_argument("--dry-run", action="store_true", help="the same as `plan`")

    for action, summary in (
        ("status", "where this release has got to, and the next command (read-only)"),
        (
            "collect",
            "every builder's core here, the manifest restamped over all of them",
        ),
        ("push", "upload the payload to the origin"),
        ("check", "read the origin back as a stranger and verify every hash"),
        ("extras", "upload the Flatpak bundles, install.sh and install.ps1"),
        ("windows", "upload the Windows installer alone, once bundles fetched it"),
    ):
        knobs = {"status": (), "check": (DRY, QUICK, WHEEL)}.get(action, (DRY,))
        p = g.command(action, summary, release_origin, BUILD_ROOT, *knobs)
        p.set_defaults(action=action)

    g.command(
        "matrix",
        "the Linux cores, converting in each distribution the install page names",
        release_matrix,
        DIST,
        DISTROS,
        ARCHES,
    )
    p = g.command(
        "released-gui",
        "a window from the *published* Flatpak, on the builders, screenshotted",
        release_released_gui,
    )
    p.add_argument(
        "--on", metavar="HOST", help="one machine; default: every Linux builder"
    )
    p.add_argument("--doc", metavar="FILE", help="the document to open")


def add_others(groups: Groups) -> None:
    p = groups.leaf(
        "on",
        "any lb command, run on a builder from build/builders.toml",
        on_,
        epilog="The builder runs the commit its checkout is at; --update sends this\n"
        "checkout's first. The command's output streams back as it comes; it\n"
        "has no terminal there, so nothing interactive (a --shell) works.\n\n"
        + examples(
            "on linux-x86_64 app flatpak-smoke",
            "on linux-arm64 --update linux lint",
            "on linux-x86_64 release matrix",
        ),
    )
    p.add_argument("platform", metavar="PLATFORM", help="as in build/builders.toml")
    p.add_argument("--update", action="store_true", help="send this commit there first")
    p.set_defaults(passes_on=True)
    groups.leaf(
        "tidy",
        "remove every build on this machine: a list, unless --yes",
        tidy_,
        BUILD_ROOT,
        YES,
        epilog=examples("tidy", "tidy --yes"),
    )
    p = groups.leaf(
        "bench",
        "a document to the screen, stage by stage (libera_build/bench.py)",
        bench,
        epilog=examples(
            "bench",
            "bench DOC.docx --runs 5",
            "bench DOC.docx --idle 20",
            "bench --app Libera.app",
        ),
    )
    p.set_defaults(passes_on=True)
    p = groups.leaf(
        "fidelity",
        "the same pages from the same build, twice (libera_build/fidelity.py)",
        fidelity,
        epilog=examples("fidelity", "fidelity DOC.docx --runs 3"),
    )
    p.set_defaults(passes_on=True)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lb",
        description=__doc__.split("\n\n")[0],
        epilog=examples(
            "payload all",
            "payload container --arch arm64",
            "linux lint",
            "release plan",
            "release ship",
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    groups = Groups(parser)
    add_payload(groups)
    add_toolchain(groups)
    add_app(groups)
    add_linux(groups)
    add_release(groups)
    add_others(groups)
    commands = "\n".join(f"  {name:<24} {what}" for name, what in groups.listing)
    parser.epilog = (
        f"commands (each takes --help: its options, and examples):\n"
        f"{commands}\n\n{parser.epilog}"
    )
    return parser


def plan(argv: list[str]) -> Steps:
    """What a command line would run, running nothing.

    `linux test` and `bench` pass on what they do not know, to pytest and to
    bench. argparse cannot express that under a subcommand: a
    REMAINDER positional there refuses `-k bridge` as an unknown option. So
    the unknown arguments are taken here, and refused for every other command.
    """
    parser = make_parser()
    args, rest = parser.parse_known_args(argv)
    if rest and not getattr(args, "passes_on", False):
        parser.error(f"unrecognized arguments: {' '.join(rest)}")
    args.rest = rest
    # Here and not in each command, so that no call done in this process can
    # be planned without the environment its options ask for.
    env = env_of(args)
    return [
        replace(s, env={**env, **s.env}) if isinstance(s, Call) else s
        for s in args.func(args)
    ]


def main(argv: list[str] | None = None) -> int:
    return run_steps(plan(sys.argv[1:] if argv is None else argv))
