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

    from libera.manifest import Manifest
    from libera_build.inventory import Builder

# The phases, in the only order they work in, with what each does. `wheel`
# follows `collect` because the wheel carries the manifest collect restamps;
# `verify` follows `publish` because what it checks is the *published* wheel.
PHASES = {
    "update": "send this commit to each builder and check it out there",
    "native": "the macOS core and its tarballs, here",
    "build": "the Linux and Windows cores, each on its builder, in parallel (hours)",
    "collect": "every core here, the manifest restamped over all of them",
    "push": "upload the payload to the origin (needs CDN_TOKEN)",
    "check": "read the origin back with no token and verify every hash",
    "bundles": "the Flatpaks and the Windows installer, each on its builder",
    "wheel": "make verify, then the wheel",
    "publish": "the wheel to PyPI, bundles and install scripts to the origin (no undo)",
    "verify": "read the published wheel back and check it against the origin",
}

# What `--only` can narrow. The rest act on every builder at once -- collect
# reads them all -- so a run narrowed to one platform that went on to them
# published cores nobody had rebuilt.
PER_BUILDER = ("update", "native", "build", "bundles")

# The phases that reach outside this machine and cannot be taken back. PyPI
# refuses a version it has already seen, so a mistaken `publish` costs a
# version number rather than a retry.
IRREVERSIBLE = ("publish",)

# The phases that stamp or upload the manifest, which records this commit.
STAMPING = ("collect", "push", "publish")
UPLOADING = ("push", "publish")


def choose_phases(asked: Sequence[str], *, narrowed: bool) -> list[str]:
    """The phases to run, in the order they work in, whatever order they were
    asked in: `push collect` means `collect push`, because there is only one
    order that works and a command line is a poor place to discover that.

    Asked for none, all of them; or, narrowed to some builders, those that
    narrow with them.
    """
    if unknown := sorted(set(asked) - set(PHASES)):
        msg = f"no such phase: {', '.join(unknown)}"
        raise RefusedError(msg)
    default = PER_BUILDER if narrowed else tuple(PHASES)
    wanted = set(asked) or set(default)
    phases = [p for p in PHASES if p in wanted]
    if narrowed and (spanning := [p for p in phases if p not in PER_BUILDER]):
        msg = (
            f"--only narrows {', '.join(PER_BUILDER)}, and not "
            f"{', '.join(spanning)}, which work on every builder at once"
        )
        raise RefusedError(msg)
    return phases


def token_problems(phases: Sequence[str], *, have_token: bool) -> list[str]:
    """A missing CDN token is a one-second discovery that used to be a two-hour
    one, because push is the last stage and the builds are the first."""
    if (needs := [p for p in UPLOADING if p in phases]) and not have_token:
        return [f"{'/'.join(needs)} needs CDN_TOKEN in the environment"]
    return []


def dirty_problems(
    phases: Sequence[str], *, dirty: int, allow_dirty: bool
) -> list[str]:
    """Uncommitted files here. Harmless to a build -- the builders are sent
    the commit and never see this tree -- and fatal to anything that stamps the
    manifest, which records the commit as its provenance: a dirty tree names
    nothing anyone could check. lb release push refuses the same, with the same
    escape; both exist because they happen hours apart."""
    stamping = [p for p in STAMPING if p in phases]
    if dirty and stamping and not allow_dirty:
        return [
            (
                f"{dirty} uncommitted file(s) here, and {'/'.join(stamping)} "
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
    uploading = [p for p in UPLOADING if p in phases]
    if uploading and not on_a_remote:
        return [
            (
                f"{'/'.join(uploading)} would stamp {head[:9]} into the "
                "manifest, and no remote has it: push it first"
            )
        ]
    return []


def publish_problems(
    phases: Sequence[str],
    *,
    manifest: Manifest | None,
    payload_version: str,
    head: str,
) -> list[str]:
    """Why what `publish` would upload is not this release, if it is not.

    The manifest is whatever the last collect wrote. Publishing used to want
    only that it existed, so a run of `publish` alone uploaded a wheel carrying
    an earlier run's manifest -- another payload version, another commit --
    that nothing had read back from the origin.
    """
    if "publish" not in phases:
        return []
    problems = []
    if "check" not in phases:
        problems.append(
            "publish without check: add check, so that what goes up is what "
            "the origin serves"
        )
    if "collect" in phases:
        return problems  # written in this run, from this commit
    if manifest is None:
        return [*problems, "publish needs src/libera/manifest.json; run collect"]
    if manifest.payload_version != payload_version:
        problems.append(
            f"the manifest is for payload {manifest.payload_version}, this tree "
            f"for {payload_version}; run collect"
        )
    stamped = manifest.commit
    if stamped != head:
        problems.append(
            f"the manifest was collected at {stamped[:9] or 'no commit'}, this "
            f"tree is at {head[:9]}; run collect"
        )
    return problems


def builder_problems(b: Builder, facts: dict[str, str]) -> list[str]:
    """What is wrong with a builder, from what it said about itself."""
    problems = []
    # Cross-building is not what these machines are for: a container built for
    # the other architecture either runs under emulation for hours or fails
    # partway through with a platform mismatch.
    if b.arch and DOCKER_ARCH.get(facts["ARCH"]) != b.arch:
        problems.append(
            f"{b.platform}: wants {b.arch} and {b.target} reports "
            f"{facts['ARCH']}. Assign it a machine of that architecture."
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
