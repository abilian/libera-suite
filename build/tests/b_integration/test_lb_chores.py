"""tap and docs, the release's chores outside this repository: a real tap
clone pushing to a bare repository here, with `make update` stood in for, and
the site's deploy and read-back stood in for."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from libera_build.release.context import Context
from libera_build.release.phases import chores
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

# What the tap's generator writes for a version, as far as the phase reads it.
UPDATE = """update:
\tprintf '[libera]\\npypi = "libera"\\nversion = "{v}"\\n' > formulae.toml
\tprintf 'url "https://files.pythonhosted.org/x/libera-{v}.tar.gz"\\n' > Formula/libera.rb
"""


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def tap(tmp_path, monkeypatch):
    """A tap clone at libera 9.9.8 whose `make update` writes `writes`, its
    branch tracking a bare repository; and that repository.

    The tap phase commits as whoever runs it. A machine with no git identity
    of its own (the Linux test container) refused that commit, so the test
    names one."""
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    clone = tmp_path / "homebrew-tap"
    (clone / "Formula").mkdir(parents=True)
    git(clone, "init", "-q", "-b", "main")
    (clone / "Makefile").write_text(UPDATE.format(v="9.9.8"))
    subprocess.run(["make", "-s", "update"], cwd=clone, check=True)
    git(clone, "add", ".")
    git(clone, "commit", "-q", "-m", "libera 9.9.8")
    git(clone, "remote", "add", "origin", str(bare))
    git(clone, "push", "-q", "-u", "origin", "main")
    return clone, bare


def release(tmp_path: Path, version: str, tap_dir: Path) -> Context:
    root = tmp_path / "repo"
    root.mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    return Context(root=root, builders=[], phases=["tap"], tap=tap_dir)


def test_the_tap_moves_to_the_release_and_is_pushed(tmp_path, tap):
    clone, bare = tap
    (clone / "Makefile").write_text(UPDATE.format(v="9.9.9"))
    git(clone, "commit", "-q", "-am", "the generator, as PyPI has 9.9.9")
    git(clone, "push", "-q")
    assert chores.tap_problems(clone) == []
    chores.tap(release(tmp_path, "9.9.9", clone))
    assert git(bare, "log", "-1", "--format=%s", "main") == "libera 9.9.9"
    assert chores.formula_problems(clone, "9.9.9") == []


def test_a_formula_the_generator_did_not_move_is_not_committed(tmp_path, tap):
    """`make update` exits 0 when PyPI has not got the release yet: the
    formula is believed by what it says, not by that."""
    clone, bare = tap
    before = git(bare, "rev-parse", "main")
    with pytest.raises(RefusedError, match="nothing was committed to the tap"):
        chores.tap(release(tmp_path, "9.9.9", clone))
    assert git(bare, "rev-parse", "main") == before
    found = chores.formula_problems(clone, "9.9.9")
    assert found == [
        "formulae.toml says libera 9.9.8, not 9.9.9",
        "Formula/libera.rb does not fetch libera-9.9.9.tar.gz",
    ]


def test_a_pre_release_leaves_the_tap_alone(tmp_path, tap):
    clone, bare = tap
    before = git(bare, "rev-parse", "main")
    chores.tap(release(tmp_path, "9.9.9rc1", clone))
    assert git(bare, "rev-parse", "main") == before


def test_a_tap_that_cannot_take_the_release_is_refused_before_it(tmp_path, tap):
    clone, _ = tap
    assert "no Homebrew tap" in chores.tap_problems(tmp_path / "nowhere")[0]
    (clone / "README.md").write_text("someone's change")
    assert "uncommitted changes" in chores.tap_problems(clone)[0]
    (clone / "README.md").unlink()
    git(clone, "branch", "--unset-upstream")
    assert "no upstream" in chores.tap_problems(clone)[0]


@pytest.mark.parametrize(("served", "passes"), [("this", True), ("other", False)])
def test_the_site_is_believed_by_the_stamp_it_serves(
    tmp_path, monkeypatch, served, passes
):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    git(root, "init", "-q")
    (root / "docs" / "index.md").write_text("news")
    (root / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "docs")
    this = git(root, "log", "-1", "--format=%H", "--", "docs")
    deployed = []
    monkeypatch.setattr(
        chores, "run_here", lambda argv, *_a, **_k: deployed.append(argv)
    )
    monkeypatch.setattr(
        chores, "deployed_commit", lambda: this if served == "this" else "f" * 40
    )
    monkeypatch.setattr(chores, "DEPLOYED_SECONDS", 0)
    ctx = Context(root=root, builders=[], phases=["docs"])
    if passes:
        chores.docs(ctx)
    else:
        with pytest.raises(RefusedError, match="the site did not go live"):
            chores.docs(ctx)
    assert deployed == [["make", "-C", "docs", "publish"]]
