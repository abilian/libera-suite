"""The rules of a release: the phases, their order, and every refusal.

Pure functions of facts gathered elsewhere (precheck, the phases), so each rule
is tested on its own. Each refusal is a sentence naming what to do next.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from libera_build.containers import DOCKER_ARCH
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from libera_build.inventory import Builder

# The phases of each verb, in the only order they work in, with what each
# does. `check` builds the release and installs it as users will, and
# publishes nothing, so it runs at any commit, as often as wanted: what it
# builds carries no release's version, only a candidate's (phases.labels).
# `publish VERSION` turns a checked commit into that release: the version
# committed, the checked files labelled with it, the bundles made again from
# them, staged again, and only then the part with no undo. PyPI refuses a
# version it has already seen, so a mistaken publish costs a version number
# rather than a retry. `stage` follows everything that makes a file;
# `verify` and `downloads` follow `publish`, because what they check is what
# users get. The macOS core is built by `components`, into libera-core's
# wheel.
CHECK = {
    "update": "send this commit to each builder and check it out there",
    "components": "libera-core's wheel on each builder, in parallel, and libera-web"
    " here: built from the pins, or kept from a build of the same inputs",
    "wheel": "make verify (not with --fast), then the wheel",
    "label": "the wheels labelled as this commit's candidate, X.Y.Z+<commit>",
    "bundles": "the Flatpaks and the Windows installer, each on its builder,"
    " from the labelled wheels",
    "stage": "every file, gathered and installed on every platform",
    "distros": "the staged Linux converter in a clean container of each"
    " distribution the install page names, on each Linux builder (not with --fast)",
}
PUBLISH = {
    "release": "the version committed on the checked commit (not pushed), the"
    " checked files labelled with it, the sources built",
    "update": "send that commit to each builder",
    "bundles": "the Flatpaks and the Windows installer again, from those files",
    "stage": "every file, gathered and installed on every platform again",
    "publish": "the staged files: the packages to PyPI, the bundles to the CDN",
    "verify": "libera installed from PyPI alone on each platform, a document converted",
    "downloads": "the published Flatpak and Windows installer, installed on the"
    " builders, a window opened from each",
    "tap": "the Homebrew formula moved to the release, committed and pushed",
    "docs": "the documentation site deployed, and read back",
}
VERBS = {"check": CHECK, "publish": PUBLISH}
PHASES = {**CHECK, **PUBLISH}

# What `--only` can narrow. The rest act on every builder at once, so a run
# narrowed to one platform that went on to them would stage what nobody had
# rebuilt.
PER_BUILDER = ("update", "components", "bundles")


# What `check --fast` leaves out unless asked for: the suite (`wheel` then
# builds the wheel alone) and the distributions, about half an hour of the
# hour. What it keeps is every file built and installed on every platform.
SLOW = ("distros",)


def choose_phases(
    verb: str, asked: Sequence[str], *, narrowed: bool, fast: bool = False
) -> list[str]:
    """The phases of `verb` to run, in the order they work in, whatever order
    they were asked in: `stage wheel` means `wheel stage`, because there is
    only one order that works and a command line is a poor place to discover
    that.

    Asked for none, all of them; or, narrowed to some builders, those that
    narrow with them; or, fast, all but the slow ones.
    """
    own = VERBS[verb]
    if unknown := sorted(set(asked) - set(PHASES)):
        msg = f"no such phase: {', '.join(unknown)}"
        raise RefusedError(msg)
    if other := sorted(set(asked) - set(own)):
        theirs = next(v for v in VERBS if v != verb)
        msg = f"{', '.join(other)}: a phase of `lb release {theirs}`, not of {verb}"
        raise RefusedError(msg)
    default = [p for p in own if p in PER_BUILDER] if narrowed else list(own)
    if fast:
        default = [p for p in default if p not in SLOW]
    wanted = set(asked) or set(default)
    phases = [p for p in own if p in wanted]
    if narrowed and (spanning := [p for p in phases if p not in PER_BUILDER]):
        msg = (
            f"--only narrows {', '.join(PER_BUILDER)}, and not "
            f"{', '.join(spanning)}, which work on every builder at once"
        )
        raise RefusedError(msg)
    return phases


def token_problems(phases: Sequence[str], *, have_token: bool) -> list[str]:
    """A missing CDN token is a one-second discovery that used to be a two-hour
    one, because publish is the last stage and the builds are the first."""
    if "publish" in phases and not have_token:
        return ["publish needs CDN_TOKEN in the environment"]
    return []


def signing_problems(phases: Sequence[str], *, have_key: bool) -> list[str]:
    """`publish` signs the bundles, before PyPI takes the packages: a key
    missing here is found now, not after the hours of building."""
    if "publish" in phases and not have_key:
        return ["publish signs the bundles, and gpg has no release key here"]
    return []


def dirty_problems(
    phases: Sequence[str], *, dirty: int, allow_dirty: bool
) -> list[str]:
    """Uncommitted files here. Harmless to a build -- the builders are sent
    the commit and never see this tree -- and fatal to anything that stamps the
    manifest, which records the commit as its provenance: a dirty tree names
    nothing anyone could check."""
    if dirty and "publish" in phases and not allow_dirty:
        return [
            (
                f"{dirty} uncommitted file(s) here, and publish "
                "would stamp a commit that describes none of them. Commit "
                "first, or ALLOW_DIRTY=1 to publish with no reproducible "
                "provenance."
            )
        ]
    return []


def unpushed_problems(
    phases: Sequence[str], *, on_a_remote: bool, head: str
) -> list[str]:
    """The builders do not need the commit pushed; the manifest does. It
    stamps this commit as the release's provenance, and a commit only this
    laptop holds is provenance nobody can check."""
    if "publish" in phases and not on_a_remote:
        return [
            (
                f"publish would stamp {head[:9]} into the "
                "manifest, and no remote has it: push it first"
            )
        ]
    return []


def builder_problems(b: Builder, facts: dict[str, str]) -> list[str]:
    """What is wrong with a builder, from what it said about itself."""
    problems = []
    # Cross-building is not what these machines are for: a container built for
    # the other architecture either runs under emulation for hours or fails
    # partway through with a platform mismatch.
    if DOCKER_ARCH.get(facts["ARCH"]) != b.arch:
        problems.append(
            f"{b.platform}: wants {b.arch} and {b.target} reports "
            f"{facts['ARCH']}. Assign it a machine of that architecture."
        )
    # Found here, not when a phase spawns it: the arm64 builder had no uv, and
    # its components job died at the end of the wheel build.
    if missing := facts.get("MISSING", "").split():
        problems.append(
            f"{b.platform}: {b.target} has no {', '.join(missing)}. Install it there."
        )
    # Before the update, not after: checking out over somebody's edits does
    # not belong in a script that is about to run for two hours.
    if facts.get("DIRTY", "0") != "0":
        problems.append(
            f"{b.platform}: {facts['DIRTY']} uncommitted file(s) in "
            f"{b.repo} on {b.target}. Clean it before building."
        )
    return problems


def update_problems(
    b: Builder, facts: dict[str, str], *, sent: str, mark: str
) -> list[str]:
    """What is wrong with a builder after `update` checked out the commit."""
    if (verdict := facts.get(mark, "")) != "ok":
        said = verdict or "the update said nothing"
        return [f"{b.platform}: {said} (in {b.repo} on {b.target})"]
    # Clean again afterwards. A checkout cannot dirty a clean tree, but one
    # crossing a mode change or a submodule can.
    if facts.get("DIRTY", "0") != "0":
        return [f"{b.platform}: {facts['DIRTY']} file(s) dirty after the checkout"]
    if facts.get("HEAD") != sent:
        return [
            f"{b.platform}: at {facts.get('SHORT', '?')} after checking out {sent[:9]}"
        ]
    return []


def build_problem(platform: str, verdict: str, elapsed: str) -> str | None:
    """A build's verdict line, read: none, a failure, or None for ok."""
    if not verdict:
        return (
            f"{platform}: stopped after {elapsed} without saying how.\n"
            "       The connection dropped, or bash never reached the end."
        )
    if verdict != "ok":
        return f"{platform}: {verdict} after {elapsed}"
    return None


def upload_problems(
    present: set[str],
    *,
    wanted: Sequence[str],
    payload_version: str,
    requires: Sequence[str],
) -> list[str]:
    """Why what `publish` would upload is not a release a user can install.

    `wanted` is every file a release puts on PyPI, `present` what is here.
    0.7.0b1 went up as `libera` alone, naming libera-core and libera-web,
    which were nowhere: every install of it failed to resolve.
    """
    found = [
        f"{name} is not here: run the phase that makes it (label, or release)"
        for name in wanted
        if name not in present
    ]
    pins = {r.replace(" ", "") for r in requires}
    for component in ("libera-core", "libera-web"):
        if f"{component}=={payload_version}" not in pins:
            named = sorted(r for r in pins if r.startswith(component)) or ["nothing"]
            found.append(
                f"the libera wheel asks for {', '.join(named)}, not "
                f"{component}=={payload_version}: run wheel"
            )
    return found
