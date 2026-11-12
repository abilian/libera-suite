"""Build, check and release Libera Suite: everything the Makefile does not.

    lb                         every command, and what is usually run
    lb help payload            the commands in one group (lb payload --help)
    lb help payload core       one command: its options and examples

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
import functools
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
    components,
    fidelity as fidelity_,
    flatpak,
    linux,
    matrix,
    released_gui,
    report,
    tidy,
    versions,
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
from libera_build.versions import payload_version

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
    # Repeatable; its variable is the values separated by spaces.
    many: bool = False

    @property
    def dest(self) -> str:
        return self.flag.lstrip("-").replace("-", "_")


ARCH = Knob(
    "--arch",
    "ARCH",
    "amd64 or arm64; default this machine's",
    choices=("amd64", "arm64"),
)
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
    "distros: the staged files to use (default: what stage left for this commit)",
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
    "a payload folder to mount as is, instead of the component wheels",
    "DIR",
)
WHEELS = Knob(
    "--wheels",
    "WHEELS",
    "the component wheels to install; default $BUILD_ROOT/out/wheels/<version>",
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
DRY = Knob("--dry-run", "DRY", "say what it would do, and do nothing", switch=True)
DISTROS = Knob(
    "--distro",
    "DISTROS",
    "distros: an image to try; repeatable (default: the install page's)",
    "IMAGE",
    many=True,
)
ARCHES = Knob(
    "--arch",
    "ARCHES",
    "distros: amd64 or arm64; repeatable (default: both)",
    choices=("amd64", "arm64"),
    many=True,
)
YES = Knob("--yes", "YES", "do not ask first", switch=True)
OUT = Knob(
    "--out",
    "OUT",
    "where the wheels go; default $BUILD_ROOT/out/wheels/<version>",
    "DIR",
)


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
                action="append" if knob.many else "store",
                help=help_,
            )
    parser.set_defaults(knobs=knobs)


def env_of(args: argparse.Namespace) -> dict[str, str]:
    """The environment the options given ask for."""
    values = {k: getattr(args, k.dest) for k in args.knobs}
    return {
        k.env: "1" if k.switch else " ".join(v) if k.many else str(v)
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


# The payload's stages, in the one order they work in, each a build/engine
# script. `payload build` with none named runs them all, then the smoke test,
# which is buildbox.STEPS: what the container runs.
STAGES = {
    "fetch": ("build.sh", "fetch"),
    "configure": ("build.sh", "configure"),
    "core": ("build.sh", "build"),
    "assemble": ("payload.sh",),
    "dist": ("dist.sh",),
}


def misplaced(
    args: argparse.Namespace, chosen: set[str], owners: dict[str, tuple[str, ...]]
) -> None:
    """Refuse an option given for a stage or a target this run does not have:
    an option that does nothing is a mistake the person cannot see. `owners`
    is keyed by each option's dest, which is its flag's: the message names the
    flag from it."""
    for dest, theirs in owners.items():
        if getattr(args, dest) and not chosen & set(theirs):
            flag = "--" + dest.replace("_", "-")
            msg = f"{flag} is for {' and '.join(theirs)}, which this does not run"
            raise RefusedError(msg)


def payload_build(args: argparse.Namespace) -> Steps:
    stages = [stage for stage in STAGES if stage in args.stages] or list(STAGES)
    misplaced(
        args,
        set(stages),
        {
            "repo": ("fetch",),
            "mirror": ("fetch",),
            "v8_jobs": ("core",),
            "core_jobs": ("core",),
            "fonts": ("dist",),
            "manifest_only": ("dist",),
        },
    )
    env = env_of(args)
    steps = []
    for stage in stages:
        name, *rest = STAGES[stage]
        if stage == "fetch":
            rest += args.repo or []
        if stage == "dist":
            rest += ["--fonts", args.fonts or "core"]
            rest += ["--manifest-only"] if args.manifest_only else []
        steps.append(sh(f"engine/{name}", *rest, env=env))
    if not args.stages:
        steps.append(sh("engine/smoke.sh", env=env))
    return toolchain_first(args, *steps)


def box_options(args: argparse.Namespace) -> BoxOptions:
    return BoxOptions(
        arch=given(args, ARCH) or host_arch(),
        build_dir=path_given(args, BUILD_DIR),
        volume=given(args, VOLUME),
        memory=given(args, MEMORY),
        mirror=path_given(args, MIRROR),
        v8_jobs=given(args, V8_JOBS),
        core_jobs=given(args, CORE_JOBS),
    )


def container_run(args: argparse.Namespace) -> Steps:
    box = buildbox.Box(box_options(args))
    if args.rest:
        return [Call(box.script, (args.rest[0], args.rest[1:]))]
    return [Call(box.all)]


def container_export(args: argparse.Namespace) -> Steps:
    """The directory on stdout, alone, so that a caller can read it."""
    return [Call(print_exported, (box_options(args),))]


def print_exported(options: BoxOptions) -> int:
    print(buildbox.Box(options).exported())
    return 0


def payload_test(args: argparse.Namespace) -> Steps:
    return [sh("engine/smoke.sh", env=env_of(args))]


def payload_check(_args: argparse.Namespace) -> Steps:
    return [sh("engine/check-patches.sh")]


def payload_status(_args: argparse.Namespace) -> Steps:
    return [Step(("uv", "run", "libera", "--payload-status"))]


def toolchain(args: argparse.Namespace) -> Steps:
    return toolchain_steps(args.action, sys.platform, dry=switched(args, DRY))


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


# What `app build` makes, and the Flatpak builder's name for each it makes.
APP_TARGETS = ("macos", "macos-launcher", "flatpak", "flatpak-wheels", "windows")
FLATPAK_ACTION = {"flatpak": "build", "flatpak-wheels": "wheels"}


def app_build(args: argparse.Namespace) -> Steps:
    target = args.target
    misplaced(args, {target}, {"standalone": ("macos",), "arch": tuple(FLATPAK_ACTION)})
    if target == "macos":
        env = {"STANDALONE": "1"} if args.standalone else {}
        return [sh("macos/macos-app.sh", env=env)]
    if target == "macos-launcher":
        return [sh("macos/launcher.sh")]
    if target == "windows":
        return [sh("windows/windows-app.sh")]
    return [flatpak_call(args, FLATPAK_ACTION[target])]


def flatpak_call(args: argparse.Namespace, action: str) -> Call:
    options = FlatpakOptions(action, arch=given(args, ARCH) or host_arch())
    return Call(flatpak.run, (options,))


def app_check(args: argparse.Namespace) -> Steps:
    return [flatpak_call(args, "check")]


def app_test(args: argparse.Namespace) -> Steps:
    misplaced(args, {args.target}, {"arch": ("flatpak",)})
    if args.target == "windows":
        return [sh("windows/gui-test.sh")]
    return [flatpak_call(args, "smoke")]


def given(args: argparse.Namespace, knob: Knob) -> str | None:
    """A knob's value: the option, else its environment variable, which keeps
    working for a command done in this process as it did for a script."""
    # A knob the command does not take is not given: `container shell` reads
    # the payload container's options without offering all of them.
    return getattr(args, knob.dest, None) or os.environ.get(knob.env) or None


def listed(args: argparse.Namespace, knob: Knob) -> tuple[str, ...]:
    """A repeatable knob's values: the options, else its variable's words."""
    return tuple(getattr(args, knob.dest, None) or os.environ.get(knob.env, "").split())


def path_given(args: argparse.Namespace, knob: Knob) -> Path | None:
    value = given(args, knob)
    return Path(value).expanduser() if value else None


def switched(args: argparse.Namespace, knob: Knob) -> bool:
    """A switch: given, or its variable set to 1."""
    return bool(getattr(args, knob.dest, False)) or os.environ.get(knob.env) == "1"


def linux_(args: argparse.Namespace) -> Steps:
    action = args.action
    if getattr(args, "gui", False):
        if args.rest:
            msg = "test --gui runs the gui tier as it is: no pytest arguments"
            raise RefusedError(msg)
        action = "gui-test"
    if getattr(args, "dialog", False):
        action = "dialog"
    options = LinuxOptions(
        action=action,
        arch=given(args, ARCH),
        wheels=path_given(args, WHEELS),
        payload=path_given(args, PAYLOAD),
        lang=given(args, LINUX_LANG),
        pytest_args=tuple(args.rest),
    )
    return [Call(linux.run, (options,))]


# Each container by the group whose work it does.
CONTAINERS = ("payload", "flatpak", "linux")


def container(args: argparse.Namespace) -> Steps:
    """The three containers' shell, pins, image and volume, by one name.

    Their other options (the build tree, the container's LANG) still arrive as
    their environment variables, which each reads."""
    arch, verb = given(args, ARCH) or host_arch(), args.action
    if verb == "run":
        return container_run(args)
    if verb == "export":
        return container_export(args)
    if args.kind == "payload":
        box = buildbox.Box(box_options(args))
        return [
            {
                "shell": Call(box.run, ("exec /bin/bash",)),
                "versions": Call(box.versions),
                "image": Call(box.build_image),
            }[verb]
        ]
    if args.kind == "flatpak":
        steps: Steps = []
        if verb == "clean" and not switched(args, YES):
            question = f"drop the Flatpak builder's {arch} runtime volume (~4 GB)?"
            steps.append(Call(ask, (question, "nothing was removed.")))
        return [*steps, Call(flatpak.run, (FlatpakOptions(verb, arch=arch),))]
    options = LinuxOptions(action=verb, arch=arch, lang=given(args, LINUX_LANG))
    return [Call(linux.run, (options,))]


def ask(question: str, refused: str) -> int:
    report.confirm(question, refused)
    return 0


def release_ship(args: argparse.Namespace) -> Steps:
    return ship_steps(args, yes=args.yes, dry_run=False)


def release_bump(args: argparse.Namespace) -> Steps:
    return [Call(versions.bump, (REPO, args.version)), Step(("uv", "lock"))]


def release_plan(args: argparse.Namespace) -> Steps:
    return ship_steps(args, yes=False, dry_run=True)


def ship_steps(args: argparse.Namespace, *, yes: bool, dry_run: bool) -> Steps:
    options = ShipOptions(
        phases=tuple(args.phases),
        only=tuple(args.only or ()),
        yes=yes,
        dry_run=dry_run,
    )
    return [Call(ship, (options,))]


def release_origin(args: argparse.Namespace) -> Steps:
    """`status`, and `upload`: the bundles and the scripts, or the Windows
    installer alone."""
    verb = args.action if args.action == "status" else args.what or "extras"
    options = OriginOptions(
        verb,
        dry_run=switched(args, DRY),
        yes=switched(args, YES),
    )
    return [Call(verbs.run, (options,))]


def release_check(args: argparse.Namespace) -> Steps:
    misplaced(
        args,
        {args.what},
        {
            "dist": ("distros",),
            "distro": ("distros",),
            "arch": ("distros",),
            "only": ("downloads",),
            "doc": ("downloads",),
        },
    )
    if args.what == "downloads":
        options = ReleasedGuiOptions(only=tuple(args.only or ()), doc=args.doc)
        return [Call(released_gui.run, (options,))]
    matrix_options = MatrixOptions(
        dist=path_given(args, DIST),
        distros=listed(args, DISTROS),
        arches=listed(args, ARCHES),
    )
    return [Call(matrix.run, (matrix_options,))]


def on_(args: argparse.Namespace) -> Steps:
    options = OnOptions(args.platform, tuple(args.rest), update=args.update)
    return [Call(on, (options,))]


def components_build(args: argparse.Namespace) -> Steps:
    version = payload_version(REPO)
    out = path_given(args, OUT) or build_root() / "out" / "wheels" / version
    return [Call(components.wheels, (REPO, out))]


def tidy_(args: argparse.Namespace) -> Steps:
    root = path_given(args, BUILD_ROOT) or build_root()
    yes, dry = switched(args, YES), switched(args, DRY)
    return [Call(tidy.tidy, (REPO, root), {"yes": yes, "dry_run": dry})]


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
        # No help: argparse would list the groups above our list of every
        # command, which says the same and more.
        self._top = parser.add_subparsers(
            dest="group", metavar="GROUP", required=True, help=argparse.SUPPRESS
        )
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

    def passthrough(
        self, name: str, summary: str, func: Callable[[argparse.Namespace], Steps]
    ) -> None:
        """A command with its own parser: everything after its name, --help
        included, is passed on to it."""
        self.listing.append((name, summary))
        p = self._top.add_parser(name, help=summary, add_help=False)
        p.set_defaults(func=func, knobs=(), passes_on=True)


class Group:
    """One group's commands: `payload build`, `payload test`..."""

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
        "the editor payload, built here, and checked",
        "Its stages, in their order: fetch, configure, core, assemble, dist.\n"
        "`build` with none named runs them all, then `test`; on Linux the\n"
        "build runs in a container instead: `container run payload`. Each\n"
        "checks the toolchain first. `uv sync` builds the components itself,\n"
        "through their projects' build hooks.\n\n"
        + examples("payload build", "payload build core assemble", "payload check"),
    )
    p = g.command(
        "build",
        "the payload, from a checkout: every stage then the test, or those named",
        payload_build,
        BUILD_ROOT,
        MIRROR,
        V8_JOBS,
        CORE_JOBS,
        epilog="fetch clones or resets the sources to the pinned SHAs and applies\n"
        "the patch queue; configure is cmake's (missing tools in minutes);\n"
        "core is x2t and the native libraries (V8 alone is ~30 min); assemble\n"
        "is sdkjs, web-apps, fonts, blanks, dictionaries and branding (~4 min);\n"
        "dist is the tarballs and the manifest the components are built from.\n\n"
        + examples(
            "payload build",
            "payload build fetch --repo core --repo sdkjs --mirror ~/ghorg/euro-office",
            "payload build core --v8-jobs 4 --core-jobs 8",
            "payload build dist --fonts full",
        ),
    )
    p.add_argument(
        "stages",
        nargs="*",
        choices=[*STAGES, []],
        metavar="STAGE",
        help="the stages to run, in their order (default: all, then the test)",
    )
    p.add_argument(
        "--repo",
        action="append",
        metavar="REPO",
        help="fetch only this repository; repeatable (default: all)",
    )
    p.add_argument(
        "--fonts",
        choices=("core", "full"),
        help="dist's font set: core, what ships, or full, all of core-fonts; "
        "default: core",
    )
    p.add_argument(
        "--manifest-only",
        action="store_true",
        help="dist writes the manifest, over what is there",
    )
    g.command(
        "test",
        "the converter: fonts, docx -> odt -> docx, docx -> pdf",
        payload_test,
        BUILD_ROOT,
    )
    g.command(
        "check",
        "whether the patch queue still applies to the pinned SHAs (~20 s)",
        payload_check,
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
        ("install", "the packages this distribution needs, installed"),
    ):
        p = g.command(
            action, summary, toolchain, *((DRY,) if action == "install" else ())
        )
        p.set_defaults(action=action)


def add_app(groups: Groups) -> None:
    g = groups.group(
        "app",
        "the applications users install: the .app, the Flatpak, the Windows installer",
        examples(
            "app build macos --standalone",
            "app build flatpak --arch arm64",
            "app check flatpak",
            "app test windows",
        ),
    )
    p = g.command(
        "build",
        "an application: the .app, its launcher, the Flatpak, the Windows installer",
        app_build,
        ARCH,
        epilog="macos is Libera.app, unsigned; macos-launcher rebuilds\n"
        "src/libera/macos/, its executable and icon, which are committed;\n"
        "flatpak is the bundle with its wheels and its check, flatpak-wheels\n"
        "the offline wheel set alone; windows is the installer, on Windows.\n\n"
        + examples("app build macos", "app build flatpak --arch arm64"),
    )
    p.add_argument("target", choices=APP_TARGETS, metavar="TARGET")
    p.add_argument(
        "--standalone",
        action="store_true",
        help="macos: with Python, libera and the payload inside; "
        "default: runs this checkout",
    )
    p = g.command(
        "check",
        "the built Flatpak installed, and --diagnose run in it",
        app_check,
        ARCH,
    )
    p.add_argument("target", choices=("flatpak",), metavar="flatpak")
    p = g.command(
        "test",
        "the Flatpak converting a document, or the gui tier in a Windows window",
        app_test,
        ARCH,
        epilog="flatpak installs the built bundle and converts a document in it;\n"
        "windows runs the suite's gui tier in a real window, in the desktop\n"
        "session.\n\n" + examples("app test flatpak", "app test windows"),
    )
    p.add_argument("target", choices=("flatpak", "windows"), metavar="flatpak|windows")


def add_linux(groups: Groups) -> None:
    g = groups.group(
        "linux",
        "this repository's checks on Linux, in a container",
        "The suite needs this architecture's component wheels, which\n"
        "`components build` makes on a Linux machine, or a --payload DIR.\n\n"
        + examples(
            "linux lint",
            "linux test -k bridge",
            "linux test --gui",
            "linux screenshot --lang fr_FR.UTF-8",
        ),
    )
    runs_libera = (ARCH, WHEELS, PAYLOAD, LINUX_LANG)
    p = g.command(
        "test",
        "the suite; anything after it goes to pytest",
        linux_,
        *runs_libera,
    )
    p.add_argument(
        "--gui",
        action="store_true",
        help="the gui tier (tests/d_gui), in a real GTK window under Xvfb",
    )
    p.set_defaults(action="test", passes_on=True)
    p = g.command(
        "lint",
        "the type checkers, where the Linux branches are live",
        linux_,
        ARCH,
    )
    p.set_defaults(action="lint")
    p = g.command(
        "screenshot",
        "a real GTK window under Xvfb, screenshotted",
        linux_,
        *runs_libera,
    )
    p.add_argument(
        "--dialog", action="store_true", help="the GTK question the host asks, answered"
    )
    p.set_defaults(action="gui")


def add_container(groups: Groups) -> None:
    g = groups.group(
        "container",
        "the containers the other groups build and test in, by the group's name",
        "payload builds the Linux payload, flatpak the Flatpak, linux runs the\n"
        "suite. Each is built when first needed; `image` rebuilds it.\n\n"
        + examples(
            "container run payload --arch arm64",
            "container shell linux",
            "container versions flatpak --arch arm64",
            "container image payload",
            "container clean flatpak",
        ),
    )
    box = (BUILD_ROOT, BUILD_DIR, VOLUME)
    p = g.command(
        "run",
        "the whole Linux payload build in its container, or one build/ script",
        container,
        ARCH,
        *box,
        MEMORY,
        MIRROR,
        V8_JOBS,
        CORE_JOBS,
        epilog="Anything after the options is one build/ script and its arguments,\n"
        "run in the container instead of the whole build.\n\n"
        + examples(
            "container run payload",
            "container run payload --arch arm64 --memory 12g",
            "container run payload --build-dir /Volumes/T7/linux-amd64",
            "container run payload --arch arm64 dist.sh --fonts core",
        ),
    )
    p.add_argument("kind", choices=("payload",), metavar="payload")
    p.set_defaults(action="run", passes_on=True)
    p = g.command(
        "export",
        "the payload container's artifacts, copied here, and where they went",
        container,
        ARCH,
        *box,
    )
    p.add_argument("kind", choices=("payload",), metavar="payload")
    p.set_defaults(action="export")
    for verb, summary, kinds, knobs in (
        ("shell", "a shell in one of the containers", CONTAINERS, ()),
        ("versions", "what a container's image is pinned to", CONTAINERS, ()),
        ("image", "a container's image, built or rebuilt", CONTAINERS, ()),
        (
            "clean",
            "the Flatpak builder's runtime volume, dropped",
            ("flatpak",),
            (YES,),
        ),
    ):
        p = g.command(verb, summary, container, ARCH, *knobs)
        p.add_argument("kind", choices=kinds, metavar="|".join(kinds))
        p.set_defaults(action=verb)


WIDEST = max(map(len, PHASES))
PHASE_LIST = "\n".join(f"  {name:<{WIDEST}}  {what}" for name, what in PHASES.items())


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
            "release ship components bundles --only linux-arm64",
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
                f"release {name}",
                f"release {name} update native build components bundles wheel stage",
                f"release {name} build bundles --only linux-arm64",
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
            # The flag alone, not the YES knob: its variable, set for a tidy,
            # would skip the one question PyPI's no-undo is worth asking.
            p.add_argument(
                "--yes", action="store_true", help="do not ask before publishing"
            )

    p = g.command(
        "bump",
        "the release's version, for libera, libera-core and libera-web alike",
        release_bump,
        epilog=examples("release bump 0.7.2", "release bump 0.8.0rc1"),
    )
    p.add_argument(
        "version",
        metavar="VERSION",
        help="the new version, digits and dots, or a pre-release",
    )

    p = g.command(
        "status",
        "where this release has got to, here and on PyPI (read-only)",
        release_origin,
    )
    p.set_defaults(action="status")
    p = g.command(
        "upload",
        "the Flatpak bundles and the install scripts to the CDN, or the installer",
        release_origin,
        DRY,
        YES,
        epilog="With no argument, the Flatpak bundles, install.sh and install.ps1;\n"
        "`windows`, the Windows installer alone, once `ship bundles` fetched it.\n"
        "`ship`'s publish uploads both itself.\n\n"
        + examples("release upload --dry-run", "release upload windows"),
    )
    p.add_argument("what", nargs="?", choices=("windows",), metavar="windows")
    p.set_defaults(action="upload")
    p = g.command(
        "check",
        "the staged converter in each Linux distribution, or what users download",
        release_check,
        DIST,
        DISTROS,
        ARCHES,
        epilog="distros runs the staged libera-core wheels in a clean container of\n"
        "each distribution the install page names. downloads installs the\n"
        "*published* Flatpak and Windows installer on the builders, opens a\n"
        "window from each and screenshots it.\n\n"
        + examples(
            "release check distros",
            "release check distros --arch arm64",
            "release check distros --distro docker.io/library/debian:13",
            "release check downloads --only linux-arm64",
        ),
    )
    p.add_argument(
        "what", choices=("distros", "downloads"), metavar="distros|downloads"
    )
    p.add_argument(
        "--only",
        action="append",
        metavar="PLATFORM",
        help="downloads: one builder, by its platform in build/builders.toml; "
        "repeatable (default: every Linux and Windows builder)",
    )
    p.add_argument("--doc", metavar="FILE", help="downloads: the document to open")


def add_components(groups: Groups) -> None:
    g = groups.group(
        "components",
        "the components as Python packages: libera-core and libera-web",
        "`uv sync` builds this machine's from the pinned sources, and `build`\n"
        "makes their wheels, for PyPI: run it on each platform.\n\n"
        + examples("components build"),
    )
    g.command(
        "build",
        "libera-core's wheel for this machine, from its sdist, and libera-web's",
        components_build,
        OUT,
        epilog=examples("components build", "components build --out /tmp/wheels"),
    )


def add_others(groups: Groups) -> None:
    p = groups.leaf(
        "on",
        "any lb command, run on a builder from build/builders.toml",
        on_,
        epilog="The builder runs the commit its checkout is at; --update sends this\n"
        "checkout's first. The command's output streams back as it comes; it\n"
        "has no terminal there, so nothing interactive (container shell) works.\n\n"
        + examples(
            "on linux-x86_64 app test flatpak",
            "on linux-arm64 --update linux lint",
            "on linux-x86_64 release check distros",
        ),
    )
    p.usage = "lb on [-h] [--update] PLATFORM COMMAND ..."
    p.add_argument("platform", metavar="PLATFORM", help="as in build/builders.toml")
    p.add_argument("--update", action="store_true", help="send this commit there first")
    p.set_defaults(passes_on=True, needs_rest="which lb command to run there?")
    groups.leaf(
        "tidy",
        "every build on this machine, listed, then removed once you say yes",
        tidy_,
        BUILD_ROOT,
        YES,
        DRY,
        epilog=examples("tidy", "tidy --dry-run", "tidy --yes"),
    )
    # Each has a parser of its own, which `lb bench --help` reaches: the
    # options are listed once, where they are read.
    groups.passthrough("bench", "a document to the screen, timed stage by stage", bench)
    groups.passthrough(
        "fidelity",
        "the same pages rendered twice, and scored against references",
        fidelity,
    )


USUAL = """\
what is usually run:
  lb payload check                whether the patch queue still applies (~20 s)
  lb payload build                this machine's payload, from a checkout (hours)
  lb payload test                 whether that payload converts documents
  lb linux test                   the suite on Linux, in a container (lint: linux lint)
  lb on linux-x86_64 COMMAND      any of these, on a builder (--update first)

  a release:
  lb release bump X.Y.Z           the version, in all six places
  lb release plan                 what ship would do, running nothing
  lb release ship update components bundles wheel stage
                                  built and installed everywhere, nothing published
  lb release ship publish verify  the staged files to PyPI and the CDN (asks first)

  lb help GROUP [COMMAND]         a group's commands, or one command's options"""


# Each group's commands, in the order the help lists them.
GROUPS = (
    add_payload,
    add_toolchain,
    add_app,
    add_linux,
    add_release,
    add_components,
    add_container,
    add_others,
)


@functools.cache
def make_parser() -> argparse.ArgumentParser:
    """Built once: a parse leaves it as it was, and building it is ~85 ms,
    half of it argparse asking gettext for each string's translation."""
    parser = argparse.ArgumentParser(
        prog="lb",
        usage="lb [-h] GROUP [COMMAND] ...",
        description=__doc__.split("\n\n")[0],
        epilog=USUAL,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    groups = Groups(parser)
    for add in GROUPS:
        add(groups)
    commands = "\n".join(f"  {name:<24} {what}" for name, what in groups.listing)
    parser.epilog = (
        f"commands (lb help GROUP COMMAND: its options, and examples):\n"
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
    if not rest and (missing := getattr(args, "needs_rest", None)):
        parser.error(f"{args.group}: {missing}")
    args.rest = rest
    # Here and not in each command, so that no call done in this process can
    # be planned without the environment its options ask for.
    env = env_of(args)
    return [
        replace(s, env={**env, **s.env}) if isinstance(s, Call) else s
        for s in args.func(args)
    ]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # `lb` and `lb help release ship` are `lb --help` and `lb release ship --help`.
    if not argv or argv[0] == "help":
        argv = [*argv[1:], "--help"]
    try:
        steps = plan(argv)
    except RefusedError as e:
        # A command line that cannot be planned is a usage error, as argparse's.
        print(f"lb: error: {e}", file=sys.stderr)
        return 2
    return run_steps(steps)
