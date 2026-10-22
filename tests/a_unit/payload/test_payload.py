"""Payload resolution and installation.

The install path is mostly I/O, so these cover the decisions rather than the
plumbing: which payload gets picked, what happens when it is incomplete, and
the two things that must never be waved through -- a hash that does not match,
and a tar member that escapes the destination.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
import time
import urllib.error
from pathlib import Path, PurePath

import pytest
from support import built_dist, repo_root

from libera import payload
from libera.cli import dispatch
from libera.payload import PayloadError, locate

REPO = repo_root()


def make_payload(root: Path) -> Path:
    """A directory that satisfies is_complete()."""
    (root / "bin" / "tools").mkdir(parents=True)
    (root / "bin" / f"x2t{locate.EXE}").write_text("#!/bin/sh\n")
    (root / "bin" / "DoctRenderer.config").write_text("<Settings/>")
    (root / "sdkjs").mkdir()
    (root / "web-apps").mkdir()
    (root / "empty").mkdir()
    (root / "empty" / "new.docx").write_bytes(b"PK\x03\x04")
    (root / "AllFonts.js").write_text("window={}")
    (root / "fonts").mkdir()
    return root


def test_payload_version_matches_the_build() -> None:
    """The host and the build read one file, and must read the same version.

    The host parses it as TOML; the build's scripts take the `version = ` line
    with sed. Every format mismatch in this project has been two halves
    disagreeing about a file.
    """
    declared = (REPO / "src" / "libera" / "payload" / "payload.version").read_text(
        encoding="utf-8"
    )
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
    with pytest.raises(PayloadError, match="not a complete payload") as raised:
        payload.resolve()
    # A payload somebody pointed at and got wrong is not offered a download.
    assert not isinstance(raised.value, payload.NoPayloadError)


def test_missing_payload_says_what_to_do(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LIBERA_PAYLOAD", raising=False)
    monkeypatch.setattr(payload.locate, "get_data_dir", lambda: tmp_path / "nothing")
    monkeypatch.setattr(payload.locate, "_read_configured_dir", lambda: None)
    with pytest.raises(payload.NoPayloadError, match="libera --payload-install"):
        payload.resolve()


def test_generated_files_count_as_required(tmp_path: Path) -> None:
    """An unpacked-but-not-generated payload is not usable."""
    root = make_payload(tmp_path / "p")
    assert payload.is_complete(root)
    (root / "bin" / "DoctRenderer.config").unlink()
    assert not payload.is_complete(root)


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


def test_a_link_out_of_the_payload_is_refused(tmp_path: Path) -> None:
    """A name inside the payload, pointing outside it.

    Checking member names alone let this through: `bin/etc` is a fine name,
    and the file after it lands wherever the link points.
    """
    evil = tmp_path / "evil.tar"
    outside = tmp_path / "outside"
    outside.mkdir()
    with tarfile.open(evil, "w") as tar:
        link = tarfile.TarInfo("bin/etc")
        link.type = tarfile.SYMTYPE
        link.linkname = str(outside)
        tar.addfile(link)
        planted = tarfile.TarInfo("bin/etc/planted")
        planted.size = 0
        tar.addfile(planted, io.BytesIO(b""))
    dest = tmp_path / "dest"
    dest.mkdir()
    with (
        tarfile.open(evil) as tar,
        pytest.raises(PayloadError, match="outside the payload"),
    ):
        payload.safe_extract(tar, dest)
    assert not (outside / "planted").exists()


def _fake_dist(tmp_path: Path, *, corrupt: bool) -> Path:
    """A manifest plus one artifact, whose hash may or may not be honest."""
    dist = tmp_path / "dist"
    dist.mkdir()
    member = tmp_path / "bin"
    member.mkdir()
    (member / "x2t").write_text("#!/bin/sh\n")
    artifact = dist / f"core-{payload.get_current_platform()}.tar.gz"
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
                    "platform": payload.get_current_platform(),
                    "size": artifact.stat().st_size,
                    "sha256": digest,
                }
            ],
        })
    )
    return dist


def test_a_config_file_that_is_not_toml_is_named(tmp_path: Path, monkeypatch) -> None:
    """Not a traceback from every command, --diagnose included."""
    config = tmp_path / "config.toml"
    config.write_text("payload_dir = \n", encoding="utf-8")
    monkeypatch.setattr(locate, "get_config_file", lambda: config)

    with pytest.raises(PayloadError, match=r"config\.toml is not valid TOML"):
        locate._read_configured_dir()


def test_install_refuses_a_bad_hash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    dist = _fake_dist(tmp_path, corrupt=True)
    dest = tmp_path / "dest"
    with pytest.raises(PayloadError, match="failed verification"):
        payload.install(source=dist, dest=dest, say=lambda *_: None)
    assert not dest.exists()


def test_a_local_build_the_wheel_does_not_describe_names_both_manifests(
    tmp_path: Path, monkeypatch
) -> None:
    """The copy a release left in src/libera/ refused every later build as a
    core that "failed verification", naming neither manifest."""
    dist = _fake_dist(tmp_path, corrupt=False)
    ours = payload.installer.Manifest.read(dist / "manifest.json")
    (core,) = ours.artifacts
    stale = dataclasses.replace(
        ours,
        artifacts=(dataclasses.replace(core, sha256="0" * 64),),
        built="2026-10-15T20:32:59Z",
    )
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: stale)

    with pytest.raises(PayloadError, match=r"another build(.|\n)*2026-10-15T20:32:59Z"):
        payload.install(source=dist, dest=tmp_path / "dest", say=lambda *_: None)

    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: ours)
    monkeypatch.setattr(payload.installer, "_finish", lambda _d, _say: None)
    payload.install(source=dist, dest=tmp_path / "dest", say=lambda *_: None)


def test_an_install_removes_a_version_nobody_has_used_for_weeks(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    monkeypatch.setattr(payload.installer, "_finish", lambda _d, _say: None)
    old = tmp_path / "0.1"
    (old / "bin").mkdir(parents=True)
    (old / "payload.json").write_text("{}")
    month_ago = time.time() - 40 * 24 * 3600
    os.utime(old / "payload.json", (month_ago, month_ago))
    said: list[str] = []

    payload.install(
        source=_fake_dist(tmp_path, corrupt=False),
        dest=tmp_path / "0.5",
        say=said.append,
    )

    assert not old.exists()
    assert said[-1] == "  removed the unused payload 0.1 (0 MB)"


def test_a_platform_this_release_dropped_names_the_last_release_that_has_it(
    tmp_path: Path, monkeypatch
) -> None:
    """0.5 has no arm64 Linux core: say which version to install instead."""
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    dist = _fake_dist(tmp_path, corrupt=False)
    monkeypatch.setattr(payload.locate, "get_current_platform", lambda: "linux-arm64")

    with pytest.raises(PayloadError, match=r"libera==0\.4\.1"):
        payload.install(source=dist, dest=tmp_path / "dest", say=lambda *_: None)


def test_install_refuses_a_mismatched_payload_version(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    dist = _fake_dist(tmp_path, corrupt=False)
    manifest = json.loads((dist / "manifest.json").read_text())
    manifest["payload_version"] = "99.0"
    (dist / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(PayloadError, match="this libera needs"):
        payload.install(source=dist, dest=tmp_path / "dest", say=lambda *_: None)


def test_install_replaces_the_payload_by_a_rename_beside_it(
    tmp_path: Path, monkeypatch
) -> None:
    """Staged beside the destination, not in /tmp: a rename cannot cross
    filesystems, and shutil.move then copied, twice the size and not atomic."""
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "old").write_text("the previous payload")
    staged_beside: list[Path] = []
    monkeypatch.setattr(
        payload.installer,
        "_finish",
        lambda d, _say: staged_beside.extend(d.parent.glob(".libera-staging-*")),
    )

    payload.install(
        source=_fake_dist(tmp_path, corrupt=False), dest=dest, say=lambda *_: None
    )

    assert (dest / "bin" / "x2t").is_file()
    assert not (dest / "old").exists()
    assert not dest.with_name("dest.previous").exists()
    assert staged_beside, "staged somewhere other than beside the destination"


def test_an_install_says_which_payload_before_anything_else(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    said: list[str] = []
    monkeypatch.setattr(payload.installer, "_finish", lambda _d, say: say("done"))

    payload.install(
        source=_fake_dist(tmp_path, corrupt=False), dest=tmp_path / "d", say=said.append
    )

    assert said == [
        f"Installing Libera Suite's components, version {payload.PAYLOAD_VERSION}",
        "done",
    ]


def test_an_interrupted_install_puts_the_old_payload_back(
    tmp_path: Path, monkeypatch
) -> None:
    """Ctrl-C while the fonts are generated. The rollback caught Exception
    only, so the working payload stayed at .previous, where nothing looks and
    the next install deletes it."""
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "old").write_text("the previous payload")

    def interrupted(_dest: Path, _say) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(payload.installer, "_finish", interrupted)

    with pytest.raises(KeyboardInterrupt):
        payload.install(
            source=_fake_dist(tmp_path, corrupt=False), dest=dest, say=lambda *_: None
        )

    assert (dest / "old").read_text() == "the previous payload"
    assert not dest.with_name("dest.previous").exists()


def test_trusting_the_origin_asks_the_default_one(tmp_path: Path, monkeypatch) -> None:
    """With no --from there is no source, and it asked for None/manifest.json."""
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    asked: list[str] = []

    def offline(url: str, timeout: float):
        asked.append(url)
        reason = "offline"
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(payload.installer.urllib.request, "urlopen", offline)

    with pytest.raises(PayloadError):
        payload.install(trust_manifest=True, dest=tmp_path / "d", say=lambda *_: None)

    origin = payload.installer.DEFAULT_ORIGIN
    assert asked == [f"{origin}/{payload.PAYLOAD_VERSION}/manifest.json"]


def test_unverifiable_download_is_refused(tmp_path: Path, monkeypatch) -> None:
    """Without a manifest in the wheel, the origin would decide what we install."""
    monkeypatch.setattr(payload.installer, "read_bundled_manifest", lambda: None)
    with pytest.raises(PayloadError, match="no checksums of its own"):
        payload.install(
            source="https://example.invalid/libera",
            dest=tmp_path / "d",
            say=lambda *_: None,
        )


def test_the_artifacts_carry_no_apple_metadata() -> None:
    """macOS tar stores extended attributes as `._name` members beside every
    file that has any, and a build tree collects them just by living on an
    external volume.

    Half of editors.tar.gz was those, and every install unpacked 1548 stray
    files. dist.sh exports COPYFILE_DISABLE=1; this is what notices if that
    goes away.

    The dist is **found**, not declared. This wanted `LIBERA_DIST` in the
    environment, so it skipped on every machine that had a dist, including the
    kind it was written for. `built_dist` looks where `build/engine/dist.sh` writes.
    """
    import tarfile

    dist = built_dist(payload.PAYLOAD_VERSION)
    if dist is None:
        pytest.skip("needs built artifacts: `lb payload dist`, or set LIBERA_DIST")

    archives = sorted(dist.glob("*.tar.gz"))
    # An empty directory would make every assertion below vacuous, and a check
    # that passes by having nothing to look at is the failure this file is about.
    assert archives, f"{dist} holds no tarballs"

    for archive in archives:
        with tarfile.open(archive, "r:gz") as tar:
            stray = [n for n in tar.getnames() if PurePath(n).name.startswith("._")]
        assert not stray, f"{archive.name} carries {len(stray)} AppleDouble members"


# --- a payload shipped inside the application --------------------------------
#
# Every channel that can carry 120 MB now does: the Flatpak installs it at
# /app/share/libera/payload, and the .dmg and cask will do the same. Only PyPI
# fetches on first run, which is the one place that complexity is earned.


def _complete_payload(root):
    """The files locate.is_complete insists on, and nothing else."""
    for rel in (
        f"bin/x2t{locate.EXE}",
        "bin/DoctRenderer.config",
        "empty/new.docx",
        "AllFonts.js",
    ):
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

    assert locate.find_bundled_dir() == prefix / "share" / "libera" / "payload"


def test_an_incomplete_one_is_not_a_payload(monkeypatch, tmp_path):
    """Half an unpack is worse than none: it would be chosen and then fail."""
    prefix = tmp_path / "app"
    (prefix / "share" / "libera" / "payload").mkdir(parents=True)
    module = prefix / "lib" / "python3.13" / "site-packages" / "libera" / "payload"
    module.mkdir(parents=True)
    monkeypatch.setattr(locate, "__file__", str(module / "locate.py"))

    assert locate.find_bundled_dir() is None


def test_the_bundled_one_wins_over_a_separately_installed_one(monkeypatch, tmp_path):
    """Both are the same PAYLOAD_VERSION or neither is used, so this only picks
    between equals -- and the one that shipped with the application cannot be
    half-upgraded by an earlier run."""
    monkeypatch.delenv("LIBERA_PAYLOAD", raising=False)
    monkeypatch.setattr(locate, "_read_configured_dir", lambda: None)
    bundled = _complete_payload(tmp_path / "bundled")
    installed = _complete_payload(tmp_path / "installed")
    monkeypatch.setattr(locate, "find_bundled_dir", lambda: bundled)
    monkeypatch.setattr(locate, "get_data_dir", lambda: installed.parent)

    found = locate.resolve()

    assert found.root == bundled
    assert found.origin == "bundled"


# --- one Recent list, however the document was opened -----------------------


def test_nothing_spells_the_sessions_directory_for_itself():
    """Three callers composed this path and one of them spelt it `session`.

    `Session.recents` sits one hop up from a session directory, so two commands
    share a Recent list exactly when their session directories share a parent.
    `serve` defaulted to `get_state_dir()/"session"` while `app.run` uses the
    plural, so a document opened through the harness was remembered in a file
    the application never reads -- and `--diagnose`, which went looking under
    the plural, could not see its unsaved edits either. Nothing failed; the two
    simply never met.

    A test comparing the two values proves nothing now that both come from
    `get_sessions_dir()`. What can still regress is somebody writing the path out
    again, so that is what this looks for.
    """
    src = repo_root() / "src" / "libera"
    offenders = [
        f"{path.relative_to(src)}:{n}"
        for path in sorted(src.rglob("*.py"))
        if path.name != "locate.py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r'get_state_dir\(\)\s*/\s*"sessions?"', line)
    ]
    assert offenders == [], (
        f"compose it with payload.get_sessions_dir() instead: {offenders}"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="a POSIX mode")
@pytest.mark.parametrize("before", [None, 0o755, 0o775])
def test_the_state_directory_is_this_accounts_alone(tmp_path, monkeypatch, before):
    """It holds a copy of every open document. A directory an earlier version
    made with the umask, 755 or Ubuntu's 775, is tightened too."""
    state = tmp_path / "share" / "libera"
    if before is not None:
        state.mkdir(parents=True)
        state.chmod(before)
    monkeypatch.setattr(locate, "get_state_dir", lambda: state)

    locate.make_state_dir_private()

    assert stat.S_IMODE(state.stat().st_mode) == 0o700


@pytest.mark.skipif(sys.platform == "win32", reason="a POSIX mode")
def test_every_command_starts_by_making_it_so(tmp_path, monkeypatch):
    """The test above holds for the function; this one, for `libera` calling
    it. Without it, the line could go and nothing would fail."""
    state = tmp_path / "share" / "libera"
    state.mkdir(parents=True)
    state.chmod(0o755)
    monkeypatch.setattr(locate, "get_state_dir", lambda: state)
    monkeypatch.setattr(dispatch, "_choose_command", lambda _p, _a: lambda _a: 0)

    assert dispatch.main(["--payload-status"]) == 0

    assert stat.S_IMODE(state.stat().st_mode) == 0o700


# --- the manifest the wheel ships ---------------------------------------------
#
# Every other test in this file replaces read_bundled_manifest with a lambda, which
# is what let it point at the wrong directory for as long as it did. These two
# are the ones that look at the real lookup.


def manifest_the_code_reads() -> Path:
    from importlib import resources

    return Path(str(resources.files("libera"))) / "manifest.json"


def test_the_build_writes_the_manifest_where_the_application_reads_it():
    """One path, written by a shell script and read by a module.

    `build/engine/dist.sh` copies it into the package under INSTALL_MANIFEST, and
    `installer.read_bundled_manifest` opens it. They disagreed: the copy went to
    `libera/manifest.json` and the read looked in `libera/payload/`, because it
    was spelt `Path(__file__).with_name(...)` inside `libera.payload.installer`.

    Compared by the last two components rather than as absolute paths, so this
    says the same thing about a checkout and about an installed wheel.
    """
    dist_sh = (REPO / "build" / "engine" / "dist.sh").read_text(encoding="utf-8")
    written = re.search(r"src/(libera/\S*?manifest\.json)", dist_sh)
    assert written, "build/engine/dist.sh no longer copies a manifest into the package"
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
    found = payload.installer.read_bundled_manifest()
    assert found is not None
    assert [a.name for a in found.artifacts]


@pytest.mark.skipif(
    not manifest_the_code_reads().is_file(),
    reason="no manifest stamped into this checkout",
)
def test_the_stamped_manifest_is_for_the_payload_this_build_wants():
    """Bump the payload version and this goes red until the payload is rebuilt.

    That window is real and expected: `src/libera/payload/payload.version`
    moves first, the cores are rebuilt on three machines afterwards, and until
    the last one lands the manifest in the tree
    describes the payload before the bump. So it skips rather than fails, and
    says what is outstanding.

    What it must not do is pass. A wheel built in that window ships a manifest
    its own installer rejects -- `manifest is for payload 0.1, this libera
    needs 0.2` -- and the only thing that would have told anyone is this.
    """
    found = payload.installer.read_bundled_manifest()
    assert found is not None
    # Agreeing is the pass, and disagreeing the skip: nothing after it could
    # fail, so there is nothing after it.
    if found.payload_version != locate.PAYLOAD_VERSION:
        pytest.skip(
            f"stamped for payload {found.payload_version}, this tree wants "
            f"{locate.PAYLOAD_VERSION}: rebuild the cores and re-run "
            "INSTALL_MANIFEST=1 sh build/engine/dist.sh --manifest-only before publishing"
        )
