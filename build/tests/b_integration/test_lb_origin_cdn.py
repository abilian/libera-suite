"""push, check and collect against a CDN that is really there: a small HTTP
server in a thread, which stores what is PUT and serves it back, and can be
told to lose bytes, to have no zone, or to refuse the token."""

from __future__ import annotations

import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from libera_build.hosts import LocalHost
from libera_build.inventory import Builder
from libera_build.origin import check, collect, publish
from libera_build.origin.place import Origin
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

from libera import manifest

API = "/_/api/v1/zones/"


class FakeCdn(http.server.BaseHTTPRequestHandler):
    store: Path
    mode = "ok"  # or "short", "no-zone", "refuse"

    def log_message(self, *_args) -> None:
        pass

    def do_PUT(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if self.mode == "no-zone":
            return self.answer(404, {"error": "no such zone"})
        if self.mode == "refuse":
            return self.answer(401, {"error": "bad token"})
        key = self.path.removeprefix(API).split("/", 2)[2]
        kept = body[:-1] if self.mode == "short" else body
        (self.store / key).parent.mkdir(parents=True, exist_ok=True)
        (self.store / key).write_bytes(kept)
        return self.answer(201, {"size": len(kept)})

    def do_GET(self) -> None:
        self.serve(body=True)

    def do_HEAD(self) -> None:
        self.serve(body=False)

    def serve(self, *, body: bool) -> None:
        f = self.store / self.path.split("/", 2)[2]
        if not f.is_file():
            self.send_error(404)
            return
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if body:
            self.wfile.write(data)

    def answer(self, status: int, doc: dict) -> None:
        data = json.dumps(doc).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def cdn(tmp_path):
    """The fake CDN, and an Origin pointing at it."""
    store = tmp_path / "cdn" / "libera"
    store.mkdir(parents=True)
    handler = type("Handler", (FakeCdn,), {"store": store})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = Origin(f"http://127.0.0.1:{server.server_address[1]}", "libera", "0.4")
    try:
        yield origin, handler, store
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture
def release(tmp_path) -> Path:
    """A checkout with a stamped manifest, and the dist directory it names."""
    root = tmp_path / "root"
    (root / "src" / "libera").mkdir(parents=True)
    (root / "build" / "upstream").mkdir(parents=True)
    (root / "build" / "upstream" / "pins.toml").write_text('[repos]\ncore = "abc"\n')
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "core-linux-arm64.tar.gz").write_bytes(b"core" * 100)
    (dist / "fonts-core.tar.gz").write_bytes(b"fonts")
    stamped = manifest.stamp(dist, payload_version="0.4", font_set="core", repo=root)
    (root / "src" / "libera" / "manifest.json").write_text(stamped.to_json())
    return root


def dist_of(root: Path) -> Path:
    return root.parent / "dist"


def gpg(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--passphrase",
            "",
            "--pinentry-mode",
            "loopback",
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def signing_key(monkeypatch):
    """A key of its own, in a keyring of its own, the shape of the real one: a
    primary that only certifies and a subkey that signs. Not under tmp_path,
    whose length on a Mac is past what gpg-agent's socket can take."""
    if shutil.which("gpg") is None or sys.platform == "win32":
        pytest.skip("the machine that publishes has gpg, and is not Windows")
    with tempfile.TemporaryDirectory(prefix="lb-gpg-") as home:
        monkeypatch.setenv("GNUPGHOME", home)
        gpg("--quick-generate-key", "Test <t@example.org>", "ed25519", "cert", "never")
        rows = gpg("--list-keys", "--with-colons").stdout.splitlines()
        primary = next(r.split(":")[9] for r in rows if r.startswith("fpr:"))
        gpg("--quick-add-key", primary, "ed25519", "sign", "never")
        monkeypatch.setattr(publish, "SIGNING_KEY", primary)
        yield primary
        subprocess.run(["gpgconf", "--kill", "gpg-agent"], check=False)


@pytest.fixture
def checkout(tmp_path) -> Path:
    """A checkout at 0.4.0 with an amd64 bundle and the two install scripts."""
    root = tmp_path / "root"
    (root / "build" / "install").mkdir(parents=True)
    for script in ("install.sh", "install.ps1"):
        (root / "build" / "install" / script).write_text("# installs\n")
    (root / "pyproject.toml").write_text('[project]\nversion = "0.4.0"\n')
    bundles = root / "build" / "out" / "bundles"
    bundles.mkdir(parents=True)
    setup = bundles / "Libera-Suite-Setup-0.4.0.exe"
    setup.write_bytes(b"MZ" * 100)
    (bundles / f"{setup.name}.sha256").write_text(
        f"{manifest.hash_file(setup)}  {setup.name}\n"
    )
    (bundles / "libera-0.4.0-amd64.flatpak").write_bytes(b"flatpak" * 100)
    return root


def test_a_bundle_goes_up_with_a_signature_only_of_it(
    cdn, checkout, signing_key, monkeypatch
):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    publish.extras(checkout, origin, dry=False)
    up = store / "bundles" / "libera-0.4.0-amd64.flatpak"
    signature = f"{up}.asc"
    done = gpg("--status-fd", "1", "--verify", signature, str(up))
    assert f" {signing_key}\n" in done.stdout, done.stderr
    up.write_bytes(b"flatpak" * 99 + b"flatpaK")
    assert gpg("--verify", signature, str(up)).returncode != 0


def test_no_key_here_sends_nothing(cdn, checkout, signing_key, monkeypatch):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    monkeypatch.setattr(publish, "SIGNING_KEY", "0" * 40)
    with pytest.raises(RefusedError, match="no secret key"):
        publish.extras(checkout, origin, dry=False)
    assert not list(store.iterdir())


def test_a_signature_that_is_not_made_sends_nothing(
    cdn, checkout, signing_key, monkeypatch
):
    """The primary is here and the subkey that signs is not, so gpg lists the
    key and then cannot sign."""
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    rows = gpg("--list-secret-keys", "--with-colons").stdout.splitlines()
    subkey = [r.split(":")[9] for r in rows if r.startswith("fpr:")][1]
    assert gpg("--delete-secret-keys", f"{subkey}!").returncode == 0
    with pytest.raises(RefusedError, match="no good signature"):
        publish.extras(checkout, origin, dry=False)
    assert not list(store.iterdir())


def test_a_dry_run_signs_nothing(cdn, checkout, monkeypatch, capsys):
    """No passphrase asked for a run that sends nothing."""
    origin, _, store = cdn
    monkeypatch.delenv("CDN_TOKEN", raising=False)
    publish.extras(checkout, origin, dry=True)
    assert "would PUT bundles/libera-0.4.0-amd64.flatpak" in capsys.readouterr().out
    bundles = checkout / "build" / "out" / "bundles"
    assert not list(bundles.glob("*.asc"))
    assert not list(store.iterdir())


def test_what_push_uploads_check_reads_back(cdn, release, monkeypatch, capsys):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    publish.push(release, origin, dist_of(release), dry=False)
    assert sorted(p.name for p in (store / "0.4").iterdir()) == [
        "core-linux-arm64.tar.gz",
        "fonts-core.tar.gz",
        "manifest.json",
    ]
    stamped = manifest.Manifest.read(release / "src" / "libera" / "manifest.json")
    check.check(origin.base, stamped, quick=False)
    assert "all 2 artifacts match" in capsys.readouterr().out


def test_a_short_upload_is_refused_when_the_cdn_says_what_it_kept(
    cdn, release, monkeypatch
):
    origin, handler, _ = cdn
    handler.mode = "short"
    monkeypatch.setenv("CDN_TOKEN", "t")
    with pytest.raises(RefusedError, match="sent 5 bytes, the CDN stored 4"):
        publish.push(release, origin, dist_of(release), dry=False)


@pytest.mark.parametrize(
    ("mode", "says"), [("no-zone", "create-zone"), ("refuse", "401")]
)
def test_a_missing_zone_or_a_refused_token_says_so(
    cdn, release, monkeypatch, mode, says
):
    origin, handler, _ = cdn
    handler.mode = mode
    monkeypatch.setenv("CDN_TOKEN", "t")
    with pytest.raises(RefusedError, match=says):
        publish.push(release, origin, dist_of(release), dry=False)


def test_check_finds_what_changed_and_what_is_gone(cdn, release, monkeypatch, capsys):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    publish.push(release, origin, dist_of(release), dry=False)
    (store / "0.4" / "fonts-core.tar.gz").write_bytes(b"fontz")
    (store / "0.4" / "core-linux-arm64.tar.gz").unlink()
    stamped = manifest.Manifest.read(release / "src" / "libera" / "manifest.json")
    with pytest.raises(RefusedError, match="2 of 3"):
        check.check(origin.base, stamped, quick=False)
    out = capsys.readouterr().out
    assert "MISSING  core-linux-arm64.tar.gz" in out
    assert "WRONG    fonts-core.tar.gz" in out
    # Sizes alone cannot see a changed byte of the same length.
    check.check(
        origin.base, replace(stamped, artifacts=stamped.artifacts[1:]), quick=True
    )


def test_a_dirty_manifest_is_not_pushed_without_saying_so(cdn, release, monkeypatch):
    origin, _, store = cdn
    path = release / "src" / "libera" / "manifest.json"
    doc = json.loads(path.read_text())
    doc["source"]["libera_dirty"] = True
    path.write_text(json.dumps(doc))
    monkeypatch.setenv("CDN_TOKEN", "t")
    monkeypatch.delenv("ALLOW_DIRTY", raising=False)
    with pytest.raises(RefusedError, match="dirty tree"):
        publish.push(release, origin, dist_of(release), dry=False)
    assert not (store / "0.4").exists()


def test_dry_run_needs_no_token_and_sends_nothing(cdn, release, monkeypatch, capsys):
    origin, _, store = cdn
    monkeypatch.delenv("CDN_TOKEN", raising=False)
    publish.push(release, origin, dist_of(release), dry=True)
    assert "would PUT 0.4/fonts-core.tar.gz" in capsys.readouterr().out
    assert not (store / "0.4").exists()
    with pytest.raises(RefusedError, match="CDN_TOKEN is not set"):
        publish.push(release, origin, dist_of(release), dry=False)


def test_extras_refuses_while_no_windows_installer_is_named(cdn, release, monkeypatch):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    assert publish.windows_ready(origin) is not None
    (store / "bundles").mkdir()
    (store / "bundles" / "latest-windows").write_text("0.3.3\n")
    assert publish.windows_ready(origin) is not None, "named, but not there"
    (store / "bundles" / "Libera-Suite-Setup-0.3.3.exe").write_bytes(b"MZ")
    assert publish.windows_ready(origin) is None


def test_extras_with_an_installer_here_names_it_before_install_ps1_goes_up(
    cdn, tmp_path, monkeypatch
):
    """The installer `ship`'s bundles brought here moves latest-windows in the
    same run, so an origin that names none yet is no reason to refuse."""
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    root = tmp_path / "root"
    (root / "build" / "install").mkdir(parents=True)
    for script in ("install.sh", "install.ps1"):
        (root / "build" / "install" / script).write_text("# installs\n")
    (root / "pyproject.toml").write_text('[project]\nversion = "0.4.0"\n')
    bundles = root / "build" / "out" / "bundles"
    bundles.mkdir(parents=True)
    setup = bundles / "Libera-Suite-Setup-0.4.0.exe"
    setup.write_bytes(b"MZ" * 100)
    digest = f"{manifest.hash_file(setup)}  {setup.name}\n"
    (bundles / f"{setup.name}.sha256").write_text(digest)
    publish.extras(root, origin, dry=False)
    assert (store / "bundles" / "latest-windows").read_text() == "0.4.0\n"
    assert (store / "bundles" / setup.name).read_bytes() == setup.read_bytes()
    assert (store / "install.ps1").is_file()


def test_a_pre_release_goes_up_under_its_own_names_and_moves_nothing(
    cdn, tmp_path, monkeypatch
):
    """install.sh refuses a pointer that is not digits and dots, so a
    pre-release that moved one would stop every curl | sh."""
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    monkeypatch.setattr(
        publish, "sign", lambda b: publish.signature_of(b).write_text("signed")
    )
    root = tmp_path / "root"
    (root / "build" / "install").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nversion = "0.4.0rc1"\n')
    bundles = root / "build" / "out" / "bundles"
    bundles.mkdir(parents=True)
    (bundles / "libera-0.4.0rc1-amd64.flatpak").write_bytes(b"flatpak")
    setup = bundles / "Libera-Suite-Setup-0.4.0rc1.exe"
    setup.write_bytes(b"MZ" * 100)
    (bundles / f"{setup.name}.sha256").write_text(
        f"{manifest.hash_file(setup)}  {setup.name}\n"
    )
    publish.extras(root, origin, dry=False)
    up = sorted(p.name for p in (store / "bundles").iterdir())
    assert up == [
        "Libera-Suite-Setup-0.4.0rc1.exe",
        "Libera-Suite-Setup-0.4.0rc1.exe.sha256",
        "libera-0.4.0rc1-amd64.flatpak",
        "libera-0.4.0rc1-amd64.flatpak.asc",
    ]
    assert not (store / "install.sh").exists()
    assert not (store / "install.ps1").exists()


def test_collect_takes_each_core_and_one_shared_pair_then_stamps(tmp_path, monkeypatch):
    """Two LocalHost builders with their own dists; the neutral one supplies
    the shared pair. The manifest lands in the dist and in the wheel's place."""
    root = tmp_path / "root"
    (root / "src" / "libera").mkdir(parents=True)
    (root / "build" / "upstream").mkdir(parents=True)
    (root / "build" / "upstream" / "pins.toml").write_text('[repos]\ncore = "abc"\n')
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "here"))
    homes = {}
    builders = []
    for platform, neutral in (("linux-x86_64", False), ("linux-arm64", True)):
        home = tmp_path / platform
        out = home / "dist" / "0.4"
        out.mkdir(parents=True)
        (out / f"core-{platform}.tar.gz").write_bytes(platform.encode() * 50)
        for shared in collect.SHARED:
            (out / shared).write_bytes(f"{shared} from {platform}".encode())
        b = Builder(platform, platform, "~/dist", neutral, "~/r")
        homes[b] = LocalHost(home)
        builders.append(b)
    collect.collect(root, "0.4", builders, homes.__getitem__, dry=False)
    dist = tmp_path / "here" / "out" / "dist" / "0.4"
    stamped = manifest.Manifest.read(root / "src" / "libera" / "manifest.json")
    assert stamped.core_platforms == ["linux-arm64", "linux-x86_64"]
    assert (dist / "editors.tar.gz").read_text() == "editors.tar.gz from linux-arm64"
    assert (dist / "manifest.json").read_text() == stamped.to_json()


def test_collect_stamps_nothing_when_a_builder_is_missing_its_core(
    tmp_path, monkeypatch
):
    root = tmp_path / "root"
    (root / "src" / "libera").mkdir(parents=True)
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "here"))
    home = tmp_path / "empty"
    home.mkdir()
    b = Builder("linux-arm64", "arm", "~/dist", True, "~/r")
    with pytest.raises(RefusedError, match="did not arrive"):
        collect.collect(root, "0.4", [b], lambda _: LocalHost(home), dry=False)
    assert not (root / "src" / "libera" / "manifest.json").exists()


def a_checkout(tmp_path: Path) -> Path:
    """A driving checkout collect can stamp from: pins and a git repository."""
    root = tmp_path / "root"
    (root / "src" / "libera").mkdir(parents=True)
    (root / "build" / "upstream").mkdir(parents=True)
    (root / "build" / "upstream" / "pins.toml").write_text('[repos]\ncore = "abc"\n')
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_collect_reads_a_builder_with_no_dist_where_its_build_wrote(
    tmp_path, monkeypatch
):
    """A Linux builder's `payload container` writes under
    ~/euro-office-build/linux-<arch>, and that is where collect looks."""
    root = a_checkout(tmp_path)
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "here"))
    home = tmp_path / "arm"
    out = home / "euro-office-build" / "linux-arm64" / "out" / "dist" / "0.4"
    out.mkdir(parents=True)
    (out / "core-linux-arm64.tar.gz").write_bytes(b"core" * 50)
    for shared in collect.SHARED:
        (out / shared).write_bytes(shared.encode())
    b = Builder("linux-arm64", "arm", None, True, "~/r")
    collect.collect(root, "0.4", [b], lambda _: LocalHost(home), dry=False)
    dist = tmp_path / "here" / "out" / "dist" / "0.4"
    assert (dist / "core-linux-arm64.tar.gz").read_bytes() == b"core" * 50


def test_collect_refuses_an_empty_core_over_the_last_releases(tmp_path, monkeypatch):
    root = a_checkout(tmp_path)
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "here"))
    dist = tmp_path / "here" / "out" / "dist" / "0.4"
    dist.mkdir(parents=True)
    (dist / "core-linux-arm64.tar.gz").write_bytes(b"the last release's")
    home = tmp_path / "arm"
    out = home / "dist" / "0.4"
    out.mkdir(parents=True)
    (out / "core-linux-arm64.tar.gz").write_bytes(b"")
    for shared in collect.SHARED:
        (out / shared).write_bytes(shared.encode())
    b = Builder("linux-arm64", "arm", "~/dist", True, "~/r")
    with pytest.raises(RefusedError, match="did not arrive: core-linux-arm64"):
        collect.collect(root, "0.4", [b], lambda _: LocalHost(home), dry=False)
