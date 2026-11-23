"""label and release: the version a run's files carry, given after the build.

The version is a label on what was built (relabel), so nothing waits for it.
`check` builds at whatever version the tree says and labels its wheels as a
candidate, the tree's version with the commit as a local label: 0.7.4+69906cd
cannot collide with a release on PyPI, which refuses such a version, so pip
can never take a published file for it. `publish VERSION` then makes the
release out of a checked commit: the version written and committed on top of
it (not pushed), and the checked files, the very ones its stage installed,
labelled with VERSION. Only the sources are built again, from that commit,
which is seconds: a source distribution carries the version in its files.
"""

from __future__ import annotations

import datetime as dt
import shutil
from typing import TYPE_CHECKING

from libera_build import repo, versions
from libera_build.artifacts import release_files, release_wheels
from libera_build.components import CORE, TAGS
from libera_build.process import run_here
from libera_build.relabel import relabel
from libera_build.release.phases import staging
from libera_build.report import RefusedError, problems, say, step

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.inventory import Builder
    from libera_build.release.context import Context

CHANGES = "CHANGES.md"
UNRELEASED = "## [Unreleased]"
# What a release's own commit changes, and nothing else: the version, in
# every place `bump` writes it, the lock that records the workspace's, and
# the changelog's heading.
BUMPED = frozenset({
    "pyproject.toml",
    "uv.lock",
    CHANGES,
    *(path for path, _ in versions.PLACES),
})


def candidate_version(root: Path, commit: str) -> str:
    """A check's label: the tree's version, and the commit."""
    return f"{versions.app_version(root)}+{commit[:7]}"


def tags(builders: list[Builder]) -> list[str]:
    return [TAGS[b.platform] for b in builders]


def label(ctx: Context) -> None:
    """The wheels `components` and `wheel` built, labelled as this check's
    candidate, into its own pypi/."""
    built = versions.app_version(ctx.root)
    source = ctx.run / "pypi"
    step(f"the wheels, labelled {ctx.version}")
    missing = [
        f"{name} is not in {source}: run components, then wheel"
        for name in release_wheels(built, tags(ctx.builders))
        if not (source / name).is_file()
    ]
    problems(missing, "nothing was labelled.")
    dest = fresh(ctx.files / "pypi")
    for name in release_wheels(built, tags(ctx.builders)):
        say(f"    {relabel(source / name, ctx.version, dest).name}")


def subject(version: str) -> str:
    """The release commit's message."""
    return f"chore: release {version}"


def checked_commit(root: Path, version: str) -> str:
    """The commit a publish of `version` releases: HEAD, or, when HEAD is
    already that version's commit (a publish run again), the commit under it,
    which must be all it changed."""
    said = repo.git(root, "log", "-1", "--format=%s").strip()
    if said != subject(version):
        return repo.head(root)
    changed = set(repo.git(root, "diff", "--name-only", "HEAD~1", "HEAD").split())
    if extra := sorted(changed - BUMPED):
        msg = (
            f"HEAD is at {version} and changes {', '.join(extra)} besides the"
            " version: the files checked under it are not what it holds."
            "\n  Check it again (lb release check), then publish a new version."
        )
        raise RefusedError(msg)
    return repo.git(root, "rev-parse", "HEAD~1").strip()


def candidate(run: Path) -> Path:
    """The candidate's files in a checked commit's run directory: the one
    labelled directory there, since a commit has one candidate."""
    found = sorted(p for p in run.glob("*+*") if p.is_dir())
    if len(found) != 1:
        msg = f"no checked candidate in {run}: run lb release check"
        raise RefusedError(msg)
    return found[0]


def changelog_problems(root: Path) -> list[str]:
    """The changelog must have its unreleased section, which becomes the
    release's: the release commit dates it."""
    text = (root / CHANGES).read_text(encoding="utf-8")
    if (n := text.count(f"{UNRELEASED}\n")) != 1:
        return [f"{CHANGES} has {n} '{UNRELEASED}' headings, not one: write it"]
    return []


def release(ctx: Context) -> None:
    """The release's commit, unless HEAD is it already, then its files: the
    candidate's staged wheels labelled `ctx.version`, and the two sources,
    built from that commit."""
    if repo.head(ctx.root) == ctx.run.name:  # not committed yet
        commit_version(ctx.root, ctx.version)
    staged = staging.staged(candidate(ctx.run) / "staged")
    step(f"the checked files, labelled {ctx.version}")
    dest = fresh(ctx.files / "pypi")
    for f in staged:
        if f.suffix == ".whl":
            say(f"    {relabel(f, ctx.version, dest).name}")
    for project in (ctx.root, ctx.root / CORE):
        argv = ["uv", "build", "--sdist", "--out-dir", str(dest), str(project)]
        run_here(argv, "release", cwd=ctx.root)
    missing = [
        f"{name} was not made"
        for name in release_files(ctx.version, tags(ctx.builders))
        if not (dest / name).is_file()
    ]
    problems(missing, "nothing was published.")


def commit_version(root: Path, version: str) -> None:
    """`version` written everywhere, the changelog's section dated, and that
    committed alone, on top of the checked commit. Not pushed: that is the
    person's, as every push here is."""
    step(f"the commit of {version}")
    versions.bump(root, version)
    run_here(["uv", "lock", "--quiet"], "release", cwd=root)
    path = root / CHANGES
    today = dt.datetime.now(tz=dt.UTC).astimezone().date().isoformat()
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f"{UNRELEASED}\n", f"## [{version}] - {today}\n", 1
        ),
        encoding="utf-8",
    )
    repo.git(root, "add", "--", *sorted(BUMPED))
    repo.git(root, "commit", "--quiet", "-m", subject(version))
    say(f"    {repo.head(root)[:9]}  {subject(version)}  (not pushed)")


def fresh(folder: Path) -> Path:
    """`folder`, emptied: a file left from another run is not this one's."""
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    return folder
