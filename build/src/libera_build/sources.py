"""The pinned upstream trees: build/upstream/pins.toml, and whether a tree on
this machine is at its pin with the patch queue applied.

Read by the components' build hooks, which fetch a tree that is not.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import tomllib

from libera_build import repo
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from collections.abc import Collection


def pinned(root: Path) -> dict[str, str]:
    return tomllib.loads((root / repo.PINS).read_text(encoding="utf-8"))["repos"]


def source_problems(
    root: Path, src: Path, only: Collection[str] | None = None
) -> list[str]:
    """Why the trees under `src` are not the pins plus the patch queue in
    `root`, one sentence a tree; of every pinned tree, or of `only`.

    The manifest stamps the pins from pins.toml, not from what was compiled,
    and nothing in re-tarring a core fetches: a patch added since the trees
    were last fetched would ship as a release that claims it. What is compared
    is the result, HEAD's tree against the tree the queue makes of the pin in
    a scratch index, so a patch refreshed in place counts, and neither the
    patches' order nor how their diffs were written does. It compared each
    commit's `git patch-id` once, which hashes the diff's text: the Windows
    builder's git, on its default diff algorithm, wrote one of 113 commits
    with its hunks split otherwise than the queue's histogram had, and every
    build there fetched again and recompiled the whole core.
    """
    found = []
    for name, pin in pinned(root).items():
        if only is not None and name not in only:
            continue
        tree = src / name
        if not (tree / ".git").exists():
            found.append(f"{name}: no source tree at {tree}")
            continue
        # Exit 1, from either, is the answer "no": the pin is not in the
        # clone (it moved since the last fetch), or HEAD is not built on it.
        # Anything else is git unable to look, which was once read as the
        # same "no", and fetched and rebuilt the whole core on every run.
        if not (
            answers(tree, "rev-parse", "--verify", "--quiet", f"{pin}^{{commit}}")
            and answers(tree, "merge-base", "--is-ancestor", pin, "HEAD")
        ):
            found.append(f"{name}: {tree} is not on its pin, {pin[:9]}")
            continue
        queue = sorted((root / repo.PATCHES / name).glob("*.patch"))
        head = git_out(tree, "rev-parse", "HEAD^{tree}")
        if queued_tree(tree, pin, queue) != head:
            found.append(
                f"{name}: {tree} is not its pin plus the {len(queue)} patch(es)"
                " in the queue"
            )
    return found


def queued_tree(tree: Path, pin: str, queue: list[Path]) -> bytes | None:
    """The tree the queue makes of the pin, built in a scratch index and a
    scratch object store, so the clone is only read: the arm64 builder's are
    root's, and git apply could not write a blob into them. None if the queue
    does not apply, which the fetch that follows then says patch by patch."""
    with tempfile.TemporaryDirectory() as scratch:
        env = scratch_env(tree, Path(scratch))
        git_out(tree, "read-tree", pin, env=env)
        if queue:
            applied = subprocess.run(
                [*git(tree), "apply", "--cached", "--whitespace=nowarn"],
                input=b"".join(p.read_bytes() for p in queue),
                env=env,
                capture_output=True,
                check=False,
            )
            # 1 is a patch that does not apply; anything else, git failing.
            if applied.returncode == 1:
                return None
            if applied.returncode != 0:
                said = applied.stderr.decode(errors="replace").strip()
                msg = f"git apply in {tree} failed ({applied.returncode}): {said}"
                raise RefusedError(msg)
        return git_out(tree, "write-tree", env=env)


def scratch_env(tree: Path, scratch: Path) -> dict[str, str]:
    """git's environment for working on `tree` without writing to it: an
    index and an object store in `scratch`, the clone's objects read through
    as an alternate."""
    git_dir = Path(git_out(tree, "rev-parse", "--absolute-git-dir").decode().strip())
    return os.environ | {
        "GIT_INDEX_FILE": str(scratch / "index"),
        "GIT_OBJECT_DIRECTORY": str(scratch),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(git_dir / "objects"),
    }


def answers(tree: Path, *args: str) -> bool:
    """A git question's yes (0) or no (1); a refusal for anything else."""
    done = subprocess.run([*git(tree), *args], capture_output=True, check=False)
    if done.returncode not in {0, 1}:
        said = done.stderr.decode(errors="replace").strip()
        msg = f"git {args[0]} in {tree} failed ({done.returncode}): {said}"
        raise RefusedError(msg)
    return done.returncode == 0


def git(tree: Path) -> list[str]:
    """git, in `tree`, whoever owns it. A rootful Docker (the arm64 builder's)
    leaves the trees owned by root, and git then refuses to read them
    ("dubious ownership") to the user who checks them. They are our own
    build's trees, so they are trusted here, for these commands alone."""
    return ["git", "-c", f"safe.directory={tree.resolve()}", "-C", str(tree)]


def git_out(tree: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    """What git printed, as bytes; or a refusal carrying what git said
    instead."""
    done = subprocess.run(
        [*git(tree), *args], env=env, capture_output=True, check=False
    )
    if done.returncode != 0:
        said = done.stderr.decode(errors="replace").strip()
        msg = f"git {args[0]} in {tree} failed ({done.returncode}): {said}"
        raise RefusedError(msg)
    return done.stdout
