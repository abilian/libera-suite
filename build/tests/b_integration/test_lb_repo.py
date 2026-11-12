"""What git says about a checkout, read from a scratch repository."""

from __future__ import annotations

import subprocess

import pytest
from libera_build import repo, tidy
from libera_build.report import RefusedError


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def clone(tmp_path):
    """A clone of a one-commit repository, and that repository as its remote."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "-q", "-b", "main")
    git(
        upstream,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "first",
    )
    git(tmp_path, "clone", "-q", str(upstream), "clone")
    return tmp_path / "clone"


def test_a_commit_is_on_a_remote_once_pushed_and_not_before(clone):
    assert repo.on_a_remote(clone)
    git(
        clone,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "second",
    )
    assert not repo.on_a_remote(clone)


def test_what_git_says_failing_is_a_refusal_and_never_an_answer(tmp_path):
    # Not a repository: git says so on stderr, which once read as "pushed".
    with pytest.raises(RefusedError, match="not a git repository"):
        repo.on_a_remote(tmp_path)
    with pytest.raises(RefusedError, match="not a git repository"):
        repo.dirty(tmp_path)


def test_everything_tidy_removes_is_gitignored():
    # `rm -rf build` once took the patch queue with it; and a scratch directory
    # nobody ignored made a builder's checkout dirty, which refuses a release.
    paths = [f"{p}/x" for p in tidy.REPO_PATHS]
    done = subprocess.run(
        ["git", "-C", str(repo.REPO), "check-ignore", "--no-index", *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    assert sorted(done.stdout.split()) == sorted(paths)
