"""Uploads to a CDN that is really there: a small HTTP
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
from typing import TYPE_CHECKING

import pytest
from libera_build.origin import cdn as cdn_, publish
from libera_build.origin.place import Origin
from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

from libera import manifest

API = "/_/api/v1/zones/"


class FakeCdn(http.server.BaseHTTPRequestHandler):
    store: Path
    keys: list[str]  # what was stored, in the order it arrived
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
        self.keys.append(key)
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
    handler = type("Handler", (FakeCdn,), {"store": store, "keys": []})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = Origin(f"http://127.0.0.1:{server.server_address[1]}", "libera")
    try:
        yield origin, handler, store
    finally:
        server.shutdown()
        thread.join(timeout=5)


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


def make_checkout(
    tmp_path: Path, *, version: str = "0.4.0", flatpak: bool = True, setup: bool = True
) -> Path:
    """A checkout at `version` with the two install scripts, and, as asked, an
    amd64 bundle and the Windows installer with its SHA-256."""
    root = tmp_path / "root"
    (root / "build" / "install").mkdir(parents=True)
    for script in ("install.sh", "install.ps1"):
        (root / "build" / "install" / script).write_text("# installs\n")
    (root / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    bundles = root / "build" / "out" / "bundles"
    bundles.mkdir(parents=True)
    if setup:
        installer = bundles / f"Libera-Suite-Setup-{version}.exe"
        installer.write_bytes(b"MZ" * 100)
        (bundles / f"{installer.name}.sha256").write_text(
            f"{manifest.hash_file(installer)}  {installer.name}\n"
        )
    if flatpak:
        (bundles / f"libera-{version}-amd64.flatpak").write_bytes(b"flatpak" * 100)
    return root


@pytest.fixture
def checkout(tmp_path) -> Path:
    return make_checkout(tmp_path)


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


def upload(tmp_path: Path, origin: Origin) -> None:
    sent = tmp_path / "libera-0.4.0-amd64.flatpak"
    sent.write_bytes(b"12345")
    cdn_.put(origin, sent, cdn_.key_for("bundles", sent.name), token="t", dry=False)


def test_a_short_upload_is_refused_when_the_cdn_says_what_it_kept(cdn, tmp_path):
    origin, handler, _ = cdn
    handler.mode = "short"
    with pytest.raises(RefusedError, match="sent 5 bytes, the CDN stored 4"):
        upload(tmp_path, origin)


@pytest.mark.parametrize(
    ("mode", "says"), [("no-zone", "create-zone"), ("refuse", "401")]
)
def test_a_missing_zone_or_a_refused_token_says_so(cdn, tmp_path, mode, says):
    origin, handler, _ = cdn
    handler.mode = mode
    with pytest.raises(RefusedError, match=says):
        upload(tmp_path, origin)


def test_extras_refuses_while_no_windows_installer_is_named(cdn, tmp_path, monkeypatch):
    """install.ps1 installs what bundles/latest-windows names: republished
    while that is no installer, it would fail every Windows install."""
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    root = make_checkout(tmp_path, flatpak=False, setup=False)
    with pytest.raises(RefusedError, match="names no installer"):
        publish.extras(root, origin, dry=False)
    assert not list(store.iterdir())
    (store / "bundles").mkdir()
    (store / "bundles" / "latest-windows").write_text("0.3.3\n")
    with pytest.raises(RefusedError, match="names no installer"):
        publish.extras(root, origin, dry=False)  # named, but not there
    assert not (store / "install.ps1").exists()
    (store / "bundles" / "Libera-Suite-Setup-0.3.3.exe").write_bytes(b"MZ")
    publish.extras(root, origin, dry=False)
    assert (store / "install.ps1").is_file()


def test_extras_with_an_installer_here_moves_the_pointers_after_their_files(
    cdn, tmp_path, monkeypatch
):
    """The installer `ship`'s bundles brought here moves latest-windows in the
    same run, so an origin that names none yet is no reason to refuse; each
    pointer goes up after what it names, so no install script ever reads a
    version whose file is not there."""
    origin, handler, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    root = make_checkout(tmp_path, flatpak=False)
    publish.extras(root, origin, dry=False)
    assert (store / "bundles" / "latest-windows").read_text() == "0.4.0\n"
    keys = handler.keys
    assert keys.index("bundles/latest-windows") > keys.index(
        "bundles/Libera-Suite-Setup-0.4.0.exe"
    )
    assert keys[-1] == "bundles/latest"
    assert keys.index("install.ps1") > keys.index("bundles/latest-windows")


def test_an_installer_its_hash_does_not_describe_sends_nothing(
    cdn, checkout, monkeypatch
):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    sha = checkout / "build" / "out" / "bundles" / "Libera-Suite-Setup-0.4.0.exe.sha256"
    sha.write_text("0" * 64 + "  Libera-Suite-Setup-0.4.0.exe\n")
    with pytest.raises(RefusedError, match="does not describe"):
        publish.extras(checkout, origin, dry=False)
    with pytest.raises(RefusedError, match="does not describe"):
        publish.windows(checkout, origin, dry=False)
    assert not list(store.iterdir())


def test_the_installer_alone_goes_up_with_its_pointer_last(cdn, tmp_path, monkeypatch):
    origin, handler, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    publish.windows(make_checkout(tmp_path, flatpak=False), origin, dry=False)
    assert handler.keys == [
        "bundles/Libera-Suite-Setup-0.4.0.exe",
        "bundles/Libera-Suite-Setup-0.4.0.exe.sha256",
        "bundles/Libera-Suite-Setup.exe",
        "bundles/latest-windows",
    ]
    assert not (store / "bundles" / "latest").exists()


def test_the_installer_alone_refuses_when_it_is_not_here(cdn, tmp_path, monkeypatch):
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    with pytest.raises(RefusedError, match="ship bundles --only windows"):
        publish.windows(make_checkout(tmp_path, setup=False), origin, dry=False)
    assert not list(store.iterdir())


def test_a_good_signature_already_there_is_kept(
    cdn, checkout, signing_key, monkeypatch
):
    """`publish` signs before PyPI and uploads after: the upload asks for no
    passphrase, and needs no secret key any more."""
    origin, _, store = cdn
    monkeypatch.setenv("CDN_TOKEN", "t")
    bundles = checkout / "build" / "out" / "bundles"
    publish.ready(checkout, origin, dry=False, bundles=bundles)
    signed = (bundles / "libera-0.4.0-amd64.flatpak.asc").read_bytes()
    rows = gpg("--list-secret-keys", "--with-colons").stdout.splitlines()
    for fpr in [r.split(":")[9] for r in rows if r.startswith("fpr:")]:
        gpg("--delete-secret-keys", f"{fpr}!")
    publish.extras(checkout, origin, dry=False)
    assert (store / "bundles" / "libera-0.4.0-amd64.flatpak.asc").read_bytes() == signed


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
    root = make_checkout(tmp_path, version="0.4.0rc1")
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
