"""Payload resolution and installation.

The install path is mostly I/O, so these cover the decisions rather than the
plumbing: which payload gets picked, what happens when it is incomplete, and
the two things that must never be waved through -- a hash that does not match,
and a tar member that escapes the destination.
"""

from __future__ import annotations

import re
import stat
import sys
import tarfile
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
    (root / "fonts-src").mkdir()
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
    with pytest.raises(PayloadError, match="not a complete payload"):
        payload.resolve()


def test_missing_payload_says_what_to_do(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LIBERA_PAYLOAD", raising=False)
    monkeypatch.setattr(payload.locate, "get_data_dir", lambda: tmp_path / "nothing")
    monkeypatch.setattr(payload.locate, "_read_configured_dir", lambda: None)
    monkeypatch.setattr(payload.locate, "find_components", lambda: None)
    with pytest.raises(PayloadError, match="pip install libera-core==") as raised:
        payload.resolve()
    assert "--payload-install" not in str(raised.value), "there is nothing to download"


@pytest.fixture
def components(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    """libera_web and libera_core installed as packages, in this host's
    version, and nothing else that resolve() would take first."""
    site = tmp_path / "site-packages"
    web, core = site / "libera_web", site / "libera_core"
    for folder in ("sdkjs", "web-apps", "fonts-src", "empty"):
        (web / folder).mkdir(parents=True)
    (web / "empty" / "new.docx").write_bytes(b"PK\x03\x04")
    (core / "bin").mkdir(parents=True)
    (core / "bin" / f"x2t{locate.EXE}").write_text("#!/bin/sh\n")
    (core / "bin" / "DoctRenderer.config").write_text("<Settings/>")
    packages = {"libera_web": web, "libera_core": core}
    monkeypatch.setattr(locate, "find_component", packages.get)
    versions = {
        "libera-web": payload.PAYLOAD_VERSION,
        "libera-core": payload.PAYLOAD_VERSION,
    }
    monkeypatch.setattr(locate.importlib.metadata, "version", versions.__getitem__)
    monkeypatch.delenv("LIBERA_PAYLOAD", raising=False)
    monkeypatch.setattr(locate, "_read_configured_dir", lambda: None)
    return web, core


def test_installed_components_are_found_as_two_folders(components) -> None:
    web, core = components
    found = payload.resolve()
    assert found.origin == "components"
    assert found.root == web
    assert found.x2t.parent == core / "bin"
    assert found.sdkjs == web / "sdkjs"


def test_the_components_record_is_this_machines_platform(components) -> None:
    """libera-web is every platform's, so its payload.json names none."""
    web, _ = components
    (web / "payload.json").write_text('{"payload_version": "0.7"}')
    record = payload.resolve().read_record()
    platform = locate.get_current_platform()
    assert record == {"payload_version": "0.7", "platform": platform}


def test_components_of_another_version_say_how_to_get_this_ones(
    components, monkeypatch
) -> None:
    """The host pins them, so this is a broken environment, not a choice:
    neither is used, and no download of the old payload is offered."""
    versions = {"libera-web": payload.PAYLOAD_VERSION, "libera-core": "0.1"}
    monkeypatch.setattr(locate.importlib.metadata, "version", versions.__getitem__)
    with pytest.raises(PayloadError, match=r"libera-core 0\.1 is installed") as raised:
        payload.resolve()
    assert f"pip install libera-core=={payload.PAYLOAD_VERSION}" in str(raised.value)


def test_the_editors_without_the_converter_are_refused(components, monkeypatch):
    web, _ = components
    monkeypatch.setattr(locate, "find_component", {"libera_web": web}.get)
    with pytest.raises(PayloadError, match="but not libera-core"):
        payload.resolve()


def test_a_payload_folder_is_its_own_core(tmp_path: Path) -> None:
    root = make_payload(tmp_path / "p")
    assert locate.Layout.of(root) == locate.Layout(root, root)


def test_generated_files_count_as_required(tmp_path: Path) -> None:
    """An unpacked-but-not-generated payload is not usable."""
    root = make_payload(tmp_path / "p")
    assert payload.is_complete(root)
    (root / "bin" / "DoctRenderer.config").unlink()
    assert not payload.is_complete(root)


def test_a_config_file_that_is_not_toml_is_named(tmp_path: Path, monkeypatch) -> None:
    """Not a traceback from every command, --diagnose included."""
    config = tmp_path / "config.toml"
    config.write_text("payload_dir = \n", encoding="utf-8")
    monkeypatch.setattr(locate, "get_config_file", lambda: config)

    with pytest.raises(PayloadError, match=r"config\.toml is not valid TOML"):
        locate._read_configured_dir()


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

    dist = built_dist(payload.PAYLOAD_VERSION)
    if dist is None:
        pytest.skip(
            "needs built artifacts: `lb payload build dist`, or set LIBERA_DIST"
        )

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
# The Windows installer's: a frozen application has no site-packages for the
# components to be installed into.


def _complete_payload(root):
    """The files locate.is_complete insists on, and nothing else."""
    for rel in (
        f"bin/x2t{locate.EXE}",
        "bin/DoctRenderer.config",
        "empty/new.docx",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    for d in ("sdkjs", "web-apps", "fonts-src"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return root


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
