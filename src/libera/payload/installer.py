"""Fetching a payload, checking it, and putting it in place.

The top of the package. Everything it verifies against comes from the manifest
shipped inside the wheel, which is what makes the origin untrusted storage: a
download that does not match its hash is never unpacked.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path

from libera.payload import generate, locate
from libera.payload.locate import Payload, PayloadError

DEFAULT_ORIGIN = "https://cdn.abilian.com/libera"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bundled_manifest() -> dict | None:
    """The manifest shipped in the wheel, which is what makes the origin untrusted.

    resources.files("libera"), not Path(__file__).with_name(): this module is
    `libera.payload.installer`, so with_name looked in `libera/payload/` and
    build/dist.sh has always written `libera/manifest.json`, one level up. The
    two never met. A released wheel would therefore have answered every
    `libera --payload-install` with "this build ships no manifest, so downloads
    cannot be verified", and the only way in would have been --from DIR.

    Nothing caught it because nothing could: every test that touches this
    replaces it with a lambda, and --from DIR reads the directory's own copy
    without ever asking here. It surfaced the first time the origin existed and
    a container with no payload was pointed at it.
    """
    f = resources.files("libera") / "manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def can_fetch() -> bool:
    """Whether this build could install from the origin if asked.

    A release stamps manifest.json into the wheel, and that copy is what makes
    the origin ordinary storage: every download is checked against hashes that
    travelled with the application. A checkout has none, so there is nothing to
    verify against.

    Asked *before* offering, because the offer is a question. Without this the
    application asked "Download and install it now? [Y/n]", took yes, and then
    refused -- which reads as a failure rather than as something that was never
    on offer.
    """
    return bundled_manifest() is not None


def _fetch(url: str, dest: Path) -> None:
    """Download one artifact, turning network failures into something readable.

    The public origin does not exist yet, so the common case here is a DNS
    failure -- which as a raw traceback tells a user nothing they can act on.
    """
    try:
        with urllib.request.urlopen(url, timeout=60) as r, dest.open("wb") as out:
            shutil.copyfileobj(r, out, 1 << 20)
    except urllib.error.HTTPError as e:
        msg = f"{url}\n  the origin answered {e.code} {e.reason}"
        raise PayloadError(msg) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        msg = (
            f"could not reach {url}\n"
            f"  {reason}\n"
            "  The public payload origin is not published yet. Until it is,\n"
            "  install from artifacts you have built or been given:\n"
            "    libera --payload-install --from DIR"
        )
        raise PayloadError(msg) from e


def _wanted(manifest: dict, want_platform: str) -> list[dict]:
    """The artifacts this machine needs: its own core, plus the neutral ones."""
    out = []
    for a in manifest["artifacts"]:
        if a["kind"] == "core" and a.get("platform") != want_platform:
            continue
        out.append(a)
    if not any(a["kind"] == "core" for a in out):
        msg = f"manifest has no core artifact for {want_platform}"
        raise PayloadError(msg)
    return out


def safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract, refusing members that would escape dest."""
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if dest not in target.parents and target != dest:
            msg = f"refusing tar member outside the payload: {member.name}"
            raise PayloadError(msg)
    tar.extractall(dest)


def _manifest_for(source, local: Path | None, *, trust_manifest: bool) -> dict:
    """The manifest that decides what gets installed, and whether to trust it.

    The wheel's copy is authoritative -- that is what makes the origin untrusted
    storage. Without it, a local directory is still fine (the user chose those
    bytes), but a download needs an explicit --trust-manifest.
    """
    bundled = bundled_manifest()
    if bundled is not None:
        return bundled
    if local is not None:
        f = local / "manifest.json"
        if not f.is_file():
            msg = (
                f"no manifest.json in {local}\n"
                "  --from wants a directory of built artifacts, as written by\n"
                "  build/dist.sh: BUILD_ROOT/out/dist/<payload-version>/"
            )
            raise PayloadError(msg)
        return json.loads(f.read_text(encoding="utf-8"))
    if not trust_manifest:
        msg = (
            "this build ships no manifest, so downloads cannot be verified.\n"
            "  install from local artifacts:  libera --payload-install --from DIR\n"
            "  or accept the origin's manifest explicitly: --trust-manifest"
        )
        raise PayloadError(msg)
    url = f"{source}/manifest.json"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        msg = f"could not read the manifest at {url}\n  {getattr(e, 'reason', e)}"
        raise PayloadError(msg) from e


def _finish(dest: Path, log) -> None:
    """Generate the local files and confirm the result is usable."""
    log("  generating fonts and configuration")
    found = generate.generate(dest)
    log(f"    {found} fonts")
    if not locate.looks_complete(dest):
        msg = "installed payload is incomplete"
        raise PayloadError(msg)


def _check_room(where: Path, artifacts: list[dict]) -> None:
    """Refuse before downloading if the disk cannot hold the result.

    `No space left on device` arrives a hundred megabytes in, from inside
    copytree, as six tracebacks about individual files. The sizes are in the
    manifest, so the answer is knowable first.

    Twice the compressed total: the tarballs are deleted as they are extracted,
    so the peak is the unpacked payload (about 1.5x compressed) plus the one
    tarball being unpacked. Approximate, and deliberately on the generous side
    of a number that is cheap to check and expensive to get wrong.
    """
    need = 2 * sum(int(a["size"]) for a in artifacts)
    free = shutil.disk_usage(where).free
    if free >= need:
        return
    msg = (
        f"not enough room in {where}\n"
        f"  needs about {need / 1e6:.0f} MB free, has {free / 1e6:.0f} MB\n"
        f"  the payload unpacks to roughly "
        f"{sum(int(a['size']) for a in artifacts) * 1.5 / 1e6:.0f} MB"
    )
    raise PayloadError(msg)


def install(
    *,
    source: Path | str | None = None,
    dest: Path | None = None,
    trust_manifest: bool = False,
    log=print,
) -> Payload:
    """Fetch or copy the artifacts, verify them, unpack, and generate.

    ``source`` is a local directory of artifacts or a base URL; the default is
    the public origin. Nothing is installed until every hash matches.
    """
    dest = dest or (locate.data_dir() / locate.PAYLOAD_VERSION)
    want_platform = locate.current_platform()

    is_url = bool(source) and str(source).startswith(("http://", "https://"))
    local = Path(source) if source and not is_url else None
    manifest = _manifest_for(source, local, trust_manifest=trust_manifest)

    if manifest["payload_version"] != locate.PAYLOAD_VERSION:
        msg = (
            f"manifest is for payload {manifest['payload_version']}, "
            f"this libera needs {locate.PAYLOAD_VERSION}"
        )
        raise PayloadError(msg)

    artifacts = _wanted(manifest, want_platform)
    base_url = str(source or f"{DEFAULT_ORIGIN}/{locate.PAYLOAD_VERSION}")

    if local is not None:
        missing = [a["name"] for a in artifacts if not (local / a["name"]).is_file()]
        if missing:
            msg = (
                f"{local} is missing {', '.join(missing)}\n"
                f"  the manifest lists them for {want_platform}; "
                "build them with build/dist.sh"
            )
            raise PayloadError(msg)

    # Staged beside the destination, not in /tmp.
    #
    # The move at the end has to be a rename, and a rename cannot cross a
    # filesystem. On a machine where /tmp is its own mount -- tmpfs, or a small
    # partition, which is most Linux boxes -- shutil.move silently degrades to
    # copytree, and three things follow: the payload needs its own size twice,
    # the install stops being atomic, and a copy that runs out of room leaves a
    # half-populated payload where a working one used to be. All three were
    # measured on an arm64 box with a small /tmp:
    #
    #   OSError: [Errno 18] Invalid cross-device link:
    #     '/tmp/libera-payload-4i926s5m/payload' -> '~/.local/share/.../0.2'
    #   ... [Errno 28] No space left on device
    #
    # Here the rename is within one directory, so it is atomic and free, and
    # the downloads land on the filesystem that has to hold them anyway.
    dest.parent.mkdir(parents=True, exist_ok=True)
    _check_room(dest.parent, artifacts)

    with tempfile.TemporaryDirectory(prefix=".libera-staging-", dir=dest.parent) as tmp:
        tmpdir = Path(tmp)
        staged = tmpdir / "payload"
        staged.mkdir()

        for a in artifacts:
            got = tmpdir / a["name"]
            if local:
                shutil.copyfile(local / a["name"], got)
            else:
                log(f"  fetching {a['name']} ({a['size'] / 1e6:.0f} MB)")
                _fetch(f"{base_url}/{a['name']}", got)

            digest = _sha256(got)
            if digest != a["sha256"]:
                msg = (
                    f"{a['name']} failed verification\n"
                    f"  expected {a['sha256']}\n  got      {digest}"
                )
                raise PayloadError(msg)

            with tarfile.open(got, "r:gz") as tar:
                safe_extract(tar, staged)
            got.unlink()

        (staged / "payload.json").write_text(
            json.dumps(
                {
                    "payload_version": manifest["payload_version"],
                    "platform": want_platform,
                    "font_set": manifest.get("font_set"),
                    "built": manifest.get("built"),
                    # Which source this binary corresponds to. Printed by
                    # `payload status`; an AGPL obligation, not decoration.
                    "source": manifest.get("source"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        # The generated files record absolute paths, so they have to be written
        # where the payload will actually live -- generating in the staging
        # directory bakes in a temporary path that is gone a moment later.
        # Hence: move first, generate second, and roll back if that fails.
        previous = dest.with_name(dest.name + ".previous")
        shutil.rmtree(previous, ignore_errors=True)
        if dest.exists():
            dest.rename(previous)

        # The rename and the generation share one rollback. They used to be
        # separate, so a failed move left dest broken and the working payload
        # stranded at .previous -- the one outcome worse than not installing.
        try:
            staged.rename(dest)
            _finish(dest, log)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            if previous.exists():
                previous.rename(dest)
            raise
        shutil.rmtree(previous, ignore_errors=True)

    return Payload(dest, "installed")
