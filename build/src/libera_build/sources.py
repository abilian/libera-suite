"""The pinned upstream trees: build/upstream/pins.toml, and whether a tree on
this machine is at its pin with the patch queue applied.

Read by the components' build hooks, which fetch a tree that is not.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import tomllib

from libera_build import repo
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path


def pinned(root: Path) -> dict[str, str]:
    return tomllib.loads((root / repo.PINS).read_text(encoding="utf-8"))["repos"]


def source_problems(
    root: Path, src: Path, only: Collection[str] | None = None
) -> list[str]:
    """Why the trees under `src` are not the pins plus the patch queue in
    `root`, one sentence a tree; of every pinned tree, or of `only`.

    The manifest stamps the pins from pins.toml, not from what was compiled,
    and nothing in re-tarring a core fetches: a patch added since the trees
    were last fetched would ship as a release that claims it. Patches are
    compared by `git patch-id`, which reads the change rather than the subject
    line, so a patch refreshed in place counts as a different one. Not their
    order: a tree fetched before a patch was renumbered holds the same changes
    in another order, as this Mac's core did when this was written.
    """
    found = []
    for name, pin in pinned(root).items():
        if only is not None and name not in only:
            continue
        tree = src / name
        if not (tree / ".git").exists():
            found.append(f"{name}: no source tree at {tree}")
            continue
        on_pin = subprocess.run(
            ["git", "-C", str(tree), "merge-base", "--is-ancestor", pin, "HEAD"],
            capture_output=True,
            check=False,
        )
        if on_pin.returncode != 0:
            found.append(f"{name}: {tree} is not on its pin, {pin[:9]}")
            continue
        queue = sorted((root / repo.PATCHES / name).glob("*.patch"))
        want = patch_ids(b"".join(p.read_bytes() for p in queue), tree)
        applied = git_out(tree, "format-patch", "--stdout", f"{pin}..HEAD")
        if sorted(have := patch_ids(applied, tree)) != sorted(want):
            found.append(
                f"{name}: {tree} carries {len(have)} commit(s) on its pin, and "
                f"they are not the {len(want)} patch(es) in the queue"
            )
    return found


def patch_ids(patches: bytes, tree: Path) -> list[str]:
    """The `git patch-id` of each patch in a series, in order."""
    out = git_out(tree, "patch-id", "--stable", stdin=patches)
    return [line.split()[0] for line in out.decode().splitlines()]


def git_out(tree: Path, *args: str, stdin: bytes = b"") -> bytes:
    """What git printed, as bytes, since a patch need not be UTF-8; or a
    refusal carrying what git said instead."""
    done = subprocess.run(
        ["git", "-C", str(tree), *args], input=stdin, capture_output=True, check=False
    )
    if done.returncode != 0:
        said = done.stderr.decode(errors="replace").strip()
        msg = f"git {args[0]} in {tree} failed ({done.returncode}): {said}"
        raise RefusedError(msg)
    return done.stdout
