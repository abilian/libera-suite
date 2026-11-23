"""A check's candidate, and the release a publish makes of it.

`check` labels what it built 9.9.9+<commit>; `publish 9.10.0` commits the
version on the checked commit and labels the very files the candidate's stage
installed. Against a real git repository, with the uv commands stood in for.
"""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest
from libera_build import repo, versions
from libera_build.artifacts import RELEASE_DIR
from libera_build.inventory import Builder
from libera_build.release import plan, precheck
from libera_build.release.context import Context
from libera_build.release.phases import labels, staging
from libera_build.report import RefusedError

MAC = Builder("macos-arm64", "local", "~/r")
TREE = {
    "pyproject.toml": (
        '[project]\nversion = "9.9.9"\n'
        'dependencies = ["libera-core==9.9.9", "libera-web==9.9.9"]\n'
    ),
    "src/libera/payload/payload.version": 'version = "9.9.9"\n',
    "components/core/pyproject.toml": '[project]\nversion = "9.9.9"\n',
    "components/web/pyproject.toml": (
        '[project]\nversion = "9.9.9"\n'
        '[build-system]\nrequires = ["libera-core==9.9.9"]\n'
    ),
    "uv.lock": "lock\n",
    "CHANGES.md": "# Changelog\n\n## [Unreleased]\n\n- a fix\n\n## [9.9.9] - 2026-01-01\n",
}


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def tree(tmp_path, monkeypatch) -> Path:
    """A checkout at 9.9.9, committed; uv's builds stood in for."""
    root = tmp_path / "repo"
    for path, text in TREE.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    git(root.parent, "init", "-q", str(root))
    git(root, "add", "-f", ".")
    git(root, "commit", "-qm", "checked")

    def uv(argv, *_args, **_kwargs):
        if "--sdist" in argv:
            dest, project = Path(argv[argv.index("--out-dir") + 1]), Path(argv[-1])
            name = "libera_core" if project.name == "core" else "libera"
            version = versions.app_version(root)
            (dest / f"{name}-{version}.tar.gz").write_bytes(b"sdist")

    monkeypatch.setattr(labels, "run_here", uv)
    return root


def wheel(folder: Path, name: str, version: str, tag: str = "any") -> Path:
    """A wheel of ours, as small as relabel allows."""
    info = f"{name}-{version}.dist-info"
    metadata = f"Version: {version}\n"
    files = {}
    if name == "libera":
        metadata += (
            f"Requires-Dist: libera-core=={version}\n"
            f"Requires-Dist: libera-web=={version}\n"
        )
        files["libera/payload/payload.version"] = f'version = "{version}"\n'
    if name == "libera_web":
        files["libera_web/payload.json"] = f'{{"payload_version": "{version}"}}'
    made = folder / f"{name}-{version}-py3-none-{tag}.whl"
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(made, "w") as z:
        z.writestr(f"{info}/METADATA", metadata)
        for path, text in files.items():
            z.writestr(path, text)
    return made


def built(folder: Path, version: str) -> None:
    """What components and wheel leave for one Mac."""
    wheel(folder, "libera_core", version, "macosx_14_0_arm64")
    wheel(folder, "libera_web", version)
    wheel(folder, "libera", version)


def context(root: Path, phases: list[str], version: str, checked: str) -> Context:
    return Context(
        root=root,
        builders=[MAC],
        phases=phases,
        version=version,
        run=root / RELEASE_DIR / checked,
    )


def stamped(dest: Path, *, fast: bool = False) -> None:
    files = {
        f.name: staging.hash_file(f) for f in dest.iterdir() if f.name != staging.STAMP
    }
    stamp = {"commit": "c", "version": "v", "fast": fast, "files": files}
    (dest / staging.STAMP).write_text(json.dumps(stamp))


def checked(root: Path, *, fast: bool = False) -> tuple[str, Path]:
    """A check of HEAD: its candidate labelled, staged and stamped."""
    head = repo.head(root)
    ctx = context(root, ["label"], labels.candidate_version(root, head), head)
    built(ctx.run / "pypi", "9.9.9")
    labels.label(ctx)
    staged = ctx.files / "staged"
    staged.mkdir()
    for f in (ctx.files / "pypi").iterdir():
        (staged / f.name).write_bytes(f.read_bytes())
    stamped(staged, fast=fast)
    return head, staged


def test_a_check_labels_its_candidate_with_its_commit(tree):
    head, staged = checked(tree)
    assert sorted(p.name for p in staged.iterdir() if p.suffix == ".whl") == [
        f"libera-9.9.9+{head[:7]}-py3-none-any.whl",
        f"libera_core-9.9.9+{head[:7]}-py3-none-macosx_14_0_arm64.whl",
        f"libera_web-9.9.9+{head[:7]}-py3-none-any.whl",
    ]


def test_a_release_is_committed_and_made_of_the_checked_files(tree):
    head, _ = checked(tree)
    ctx = context(tree, ["release"], "9.10.0", labels.checked_commit(tree, "9.10.0"))
    assert ctx.run.name == head

    labels.release(ctx)

    # The version, committed on the checked commit, and nothing else.
    assert git(tree, "rev-parse", "HEAD~1").strip() == head
    assert git(tree, "log", "-1", "--format=%s").strip() == "chore: release 9.10.0"
    assert versions.app_version(tree) == "9.10.0"
    assert "## [9.10.0] - " in (tree / "CHANGES.md").read_text()
    assert "[Unreleased]" not in (tree / "CHANGES.md").read_text()
    assert not git(tree, "status", "--porcelain")
    assert sorted(p.name for p in (ctx.files / "pypi").iterdir()) == [
        "libera-9.10.0-py3-none-any.whl",
        "libera-9.10.0.tar.gz",
        "libera_core-9.10.0-py3-none-macosx_14_0_arm64.whl",
        "libera_core-9.10.0.tar.gz",
        "libera_web-9.10.0-py3-none-any.whl",
    ]

    # Run again, it releases the same commit, and commits nothing more.
    assert labels.checked_commit(tree, "9.10.0") == head
    labels.release(ctx)
    assert git(tree, "rev-parse", "HEAD~1").strip() == head


def test_a_release_commit_with_more_than_the_version_is_not_the_checked_one(tree):
    checked(tree)
    labels.release(
        context(tree, ["release"], "9.10.0", labels.checked_commit(tree, "9.10.0"))
    )
    (tree / "pyproject.toml").write_text(
        (tree / "pyproject.toml").read_text() + "# an edit\n"
    )
    (tree / "other.py").write_text("x = 1\n")
    git(tree, "add", "-A")
    git(tree, "commit", "-q", "--amend", "--no-edit")
    with pytest.raises(RefusedError, match=r"changes other\.py besides the version"):
        labels.checked_commit(tree, "9.10.0")


def test_a_release_needs_a_full_check_and_an_unreleased_section(tree):
    head, staged = checked(tree, fast=True)
    ctx = context(tree, ["release"], "9.10.0", head)
    (problem,) = precheck.release_problems(ctx)
    assert "checked with --fast" in problem

    stamped(staged)
    assert precheck.release_problems(ctx) == []

    (tree / "CHANGES.md").write_text("# Changelog\n")
    (problem,) = precheck.release_problems(ctx)
    assert "'## [Unreleased]' headings, not one" in problem


def test_a_commit_never_checked_has_no_candidate(tree):
    ctx = context(tree, ["release"], "9.10.0", repo.head(tree))
    with pytest.raises(RefusedError, match="no checked candidate"):
        precheck.release_problems(ctx)


def test_a_fast_check_leaves_the_distributions_out_unless_asked():
    assert "distros" not in plan.choose_phases("check", [], narrowed=False, fast=True)
    assert plan.choose_phases("check", ["distros"], narrowed=False, fast=True) == [
        "distros"
    ]
