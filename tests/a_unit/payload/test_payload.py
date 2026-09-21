"""Payload resolution and installation.

The install path is mostly I/O, so these cover the decisions rather than the
plumbing: which payload gets picked, what happens when it is incomplete, and
the two things that must never be waved through -- a hash that does not match,
and a tar member that escapes the destination.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tarfile
from pathlib import Path, PurePath

import pytest
from support import repo_root

from libera import payload
from libera.payload import PayloadError, locate

REPO = repo_root()


def make_payload(root: Path) -> Path:
    """A directory that satisfies looks_complete()."""
    (root / "bin" / "tools").mkdir(parents=True)
    (root / "bin" / "x2t").write_text("#!/bin/sh\n")
    (root / "bin" / "DoctRenderer.config").write_text("<Settings/>")
    (root / "sdkjs").mkdir()
    (root / "web-apps").mkdir()
    (root / "empty").mkdir()
    (root / "empty" / "new.docx").write_bytes(b"PK\x03\x04")
    (root / "AllFonts.js").write_text("window={}")
    (root / "fonts").mkdir()
    return root


def test_payload_version_matches_the_build() -> None:
    """The wheel and the artifact builder must agree on the payload version.

    Every format mismatch in this project has been two halves disagreeing about
    a file. This is the cheapest possible guard against another one.
    """
    declared = (REPO / "build" / "payload.version").read_text(encoding="utf-8")
    version = next(
        line.split("=", 1)[1].strip().strip('"')
        for line in declared.splitlines()
        if line.strip().startswith("version")
    )
    assert version == payload.PAYLOAD_VERSION


def test_env_var_wins(tmp_path: Path, monkeypatch) -> None:
    root = make_payload(tmp_path / "local-build")
    monkeypatch.setenv("LIBERA_PAYLOAD", str(root))
    resolved = payload.resolve()
    assert resolved.root == root
    assert resolved.origin == "LIBERA_PAYLOAD"


def test_incomplete_env_payload_fails_loudly(tmp_path: Path, monkeypatch) -> None:
    """A half-built tree must fail here, not mysteriously later."""
    half = tmp_path / "half"
    (half / "bin").mkdir(parents=True)
    (half / "bin" / "x2t").write_text("#!/bin/sh\n")
    monkeypatch.setenv("LIBERA_PAYLOAD", str(half))
    with pytest.raises(PayloadError, match="not a complete payload"):
        payload.resolve()


def test_missing_payload_says_what_to_do(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LIBERA_PAYLOAD", raising=False)
    monkeypatch.setattr(payload.locate, "data_dir", lambda: tmp_path / "nothing")
    monkeypatch.setattr(payload.locate, "_configured_dir", lambda: None)
    with pytest.raises(PayloadError, match="libera --payload-install"):
        payload.resolve()


def test_generated_files_count_as_required(tmp_path: Path) -> None:
    """An unpacked-but-not-generated payload is not usable."""
    root = make_payload(tmp_path / "p")
    assert payload.looks_complete(root)
    (root / "bin" / "DoctRenderer.config").unlink()
    assert not payload.looks_complete(root)


def test_tar_member_escaping_the_payload_is_refused(tmp_path: Path) -> None:
    evil = tmp_path / "evil.tar"
    victim = tmp_path / "outside.txt"
    victim.write_text("original")
    with tarfile.open(evil, "w") as tar:
        tar.add(victim, arcname="../outside.txt")
    dest = tmp_path / "dest"
    dest.mkdir()
    with (
        tarfile.open(evil) as tar,
        pytest.raises(PayloadError, match="outside the payload"),
    ):
        payload.safe_extract(tar, dest)
    assert victim.read_text() == "original"


def _fake_dist(tmp_path: Path, *, corrupt: bool) -> Path:
    """A manifest plus one artifact, whose hash may or may not be honest."""
    dist = tmp_path / "dist"
    dist.mkdir()
    member = tmp_path / "bin"
    member.mkdir()
    (member / "x2t").write_text("#!/bin/sh\n")
    artifact = dist / f"core-{payload.current_platform()}.tar.gz"
    with tarfile.open(artifact, "w:gz") as tar:
        tar.add(member, arcname="bin")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if corrupt:
        digest = "0" * 64
    (dist / "manifest.json").write_text(
        json.dumps({
            "payload_version": payload.PAYLOAD_VERSION,
            "artifacts": [
                {
                    "name": artifact.name,
                    "kind": "core",
                    "platform": payload.current_platform(),
                    "size": artifact.stat().st_size,
                    "sha256": digest,
                }
            ],
        })
    )
    return dist


def test_install_refuses_a_bad_hash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(payload.installer, "bundled_manifest", lambda: None)
    dist = _fake_dist(tmp_path, corrupt=True)
    dest = tmp_path / "dest"
    with pytest.raises(PayloadError, match="failed verification"):
        payload.install(source=dist, dest=dest, log=lambda *_: None)
    assert not dest.exists()


def test_install_refuses_a_mismatched_payload_version(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(payload.installer, "bundled_manifest", lambda: None)
    dist = _fake_dist(tmp_path, corrupt=False)
    manifest = json.loads((dist / "manifest.json").read_text())
    manifest["payload_version"] = "99.0"
    (dist / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(PayloadError, match="this libera needs"):
        payload.install(source=dist, dest=tmp_path / "dest", log=lambda *_: None)


def test_unverifiable_download_is_refused(tmp_path: Path, monkeypatch) -> None:
    """Without a manifest in the wheel, the origin would decide what we install."""
    monkeypatch.setattr(payload.installer, "bundled_manifest", lambda: None)
    with pytest.raises(PayloadError, match="cannot be verified"):
        payload.install(
            source="https://example.invalid/libera",
            dest=tmp_path / "d",
            log=lambda *_: None,
        )


def test_the_artifacts_carry_no_apple_metadata(tmp_path: Path) -> None:
    """macOS tar stores extended attributes as `._name` members beside every
    file that has any, and a build tree collects them just by living on an
    external volume.

    Half of editors.tar.gz was those, and every install unpacked 1548 stray
    files. dist.sh exports COPYFILE_DISABLE=1; this is what notices if that
    goes away.
    """
    import tarfile

    dist = os.environ.get("LIBERA_DIST")
    if not dist or not Path(dist).is_dir():
        pytest.skip("needs a built dist: LIBERA_DIST=$BUILD_ROOT/out/dist/<version>")

    for archive in sorted(Path(dist).glob("*.tar.gz")):
        with tarfile.open(archive, "r:gz") as tar:
            stray = [n for n in tar.getnames() if PurePath(n).name.startswith("._")]
        assert not stray, f"{archive.name} carries {len(stray)} AppleDouble members"


# --- a payload shipped inside the application --------------------------------
#
# Every channel that can carry 120 MB now does: the Flatpak installs it at
# /app/share/libera/payload, and the .dmg and cask will do the same. Only PyPI
# fetches on first run, which is the one place that complexity is earned.


def _complete_payload(root):
    """The files locate.looks_complete insists on, and nothing else."""
    for rel in ("bin/x2t", "bin/DoctRenderer.config", "empty/new.docx", "AllFonts.js"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    for d in ("sdkjs", "web-apps", "fonts"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return root


def test_a_bundled_payload_is_found_under_the_same_prefix(monkeypatch, tmp_path):
    """Searched upwards, not counted: the Flatpak runs the *runtime's* python,
    so sys.prefix is /usr and says nothing about where the application went."""
    prefix = tmp_path / "app"
    _complete_payload(prefix / "share" / "libera" / "payload")
    module = prefix / "lib" / "python3.13" / "site-packages" / "libera" / "payload"
    module.mkdir(parents=True)
    monkeypatch.setattr(locate, "__file__", str(module / "locate.py"))

    assert locate.bundled_dir() == prefix / "share" / "libera" / "payload"


def test_an_incomplete_one_is_not_a_payload(monkeypatch, tmp_path):
    """Half an unpack is worse than none: it would be chosen and then fail."""
    prefix = tmp_path / "app"
    (prefix / "share" / "libera" / "payload").mkdir(parents=True)
    module = prefix / "lib" / "python3.13" / "site-packages" / "libera" / "payload"
    module.mkdir(parents=True)
    monkeypatch.setattr(locate, "__file__", str(module / "locate.py"))

    assert locate.bundled_dir() is None


def test_the_bundled_one_wins_over_a_separately_installed_one(monkeypatch, tmp_path):
    """Both are the same PAYLOAD_VERSION or neither is used, so this only picks
    between equals -- and the one that shipped with the application cannot be
    half-upgraded by an earlier run."""
    monkeypatch.delenv("LIBERA_PAYLOAD", raising=False)
    monkeypatch.setattr(locate, "_configured_dir", lambda: None)
    bundled = _complete_payload(tmp_path / "bundled")
    installed = _complete_payload(tmp_path / "installed")
    monkeypatch.setattr(locate, "bundled_dir", lambda: bundled)
    monkeypatch.setattr(locate, "data_dir", lambda: installed.parent)

    found = locate.resolve()

    assert found.root == bundled
    assert found.origin == "bundled"


# --- one Recent list, however the document was opened -----------------------


def test_nothing_spells_the_sessions_directory_for_itself():
    """Three callers composed this path and one of them spelt it `session`.

    `Host.recents` sits one hop up from a session directory, so two commands
    share a Recent list exactly when their session directories share a parent.
    `cmd_serve` defaulted to `state_dir()/"session"` while `app.run` uses the
    plural, so a document opened through the harness was remembered in a file
    the application never reads -- and `--diagnose`, which went looking under
    the plural, could not see its unsaved edits either. Nothing failed; the two
    simply never met.

    A test comparing the two values proves nothing now that both come from
    `sessions_dir()`. What can still regress is somebody writing the path out
    again, so that is what this looks for.
    """
    src = repo_root() / "src" / "libera"
    offenders = [
        f"{path.relative_to(src)}:{n}"
        for path in sorted(src.rglob("*.py"))
        if path.name != "locate.py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r'state_dir\(\)\s*/\s*"sessions?"', line)
    ]
    assert offenders == [], (
        f"compose it with payload.sessions_dir() instead: {offenders}"
    )


# --- the manifest the wheel ships ---------------------------------------------
#
# Every other test in this file replaces bundled_manifest with a lambda, which
# is what let it point at the wrong directory for as long as it did. These two
# are the ones that look at the real lookup.


def manifest_the_code_reads() -> Path:
    from importlib import resources

    return Path(str(resources.files("libera"))) / "manifest.json"


def test_the_build_writes_the_manifest_where_the_application_reads_it():
    """One path, written by a shell script and read by a module.

    `build/dist.sh` copies it into the package under INSTALL_MANIFEST, and
    `installer.bundled_manifest` opens it. They disagreed: the copy went to
    `libera/manifest.json` and the read looked in `libera/payload/`, because it
    was spelt `Path(__file__).with_name(...)` inside `libera.payload.installer`.

    Compared by the last two components rather than as absolute paths, so this
    says the same thing about a checkout and about an installed wheel.
    """
    dist_sh = (REPO / "build" / "dist.sh").read_text(encoding="utf-8")
    written = re.search(r"src/(libera/\S*?manifest\.json)", dist_sh)
    assert written, "build/dist.sh no longer copies a manifest into the package"
    assert written.group(1) == "/".join(manifest_the_code_reads().parts[-2:])


@pytest.mark.skipif(
    not manifest_the_code_reads().is_file(),
    reason="no manifest stamped into this checkout; INSTALL_MANIFEST=1 dist.sh writes one",
)
def test_a_stamped_manifest_is_the_one_found():
    """With a manifest on disk, this build can fetch and verify.

    The symptom of getting it wrong is a released wheel that refuses every
    download it was built to make.

    The version agreement is checked separately, below, because the two are
    allowed to disagree for a while and this half is not.
    """
    assert payload.can_fetch()
    found = payload.installer.bundled_manifest()
    assert found is not None
    assert [a["name"] for a in found["artifacts"]]


@pytest.mark.skipif(
    not manifest_the_code_reads().is_file(),
    reason="no manifest stamped into this checkout",
)
def test_the_stamped_manifest_is_for_the_payload_this_build_wants():
    """Bump the payload version and this goes red until the payload is rebuilt.

    That window is real and expected: `build/payload.version` and
    `locate.PAYLOAD_VERSION` move first, the cores are rebuilt on three
    machines afterwards, and until the last one lands the manifest in the tree
    describes the payload before the bump. So it skips rather than fails, and
    says what is outstanding.

    What it must not do is pass. A wheel built in that window ships a manifest
    its own installer rejects -- `manifest is for payload 0.1, this libera
    needs 0.2` -- and the only thing that would have told anyone is this.
    """
    found = payload.installer.bundled_manifest()
    assert found is not None
    if found["payload_version"] != locate.PAYLOAD_VERSION:
        pytest.skip(
            f"stamped for payload {found['payload_version']}, this tree wants "
            f"{locate.PAYLOAD_VERSION}: rebuild the cores and re-run "
            "INSTALL_MANIFEST=1 sh build/dist.sh --manifest-only before publishing"
        )
    assert found["payload_version"] == locate.PAYLOAD_VERSION
