"""Fetching a payload, checking it, and putting it in place.

The top of the package. Everything it verifies against comes from the manifest
shipped inside the wheel, which is what makes the origin untrusted storage: a
download that does not match its hash is never unpacked.
"""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from libera.manifest import Manifest, ManifestError
from libera.payload import fonts, generate, locate, prune
from libera.payload.locate import Payload, PayloadError

if TYPE_CHECKING:
    from collections.abc import Callable
    from importlib.resources.abc import Traversable

    from libera.manifest import Artifact

DEFAULT_ORIGIN = "https://cdn.abilian.com/libera"


def read_bundled_manifest() -> Manifest | None:
    """The manifest shipped in the wheel, which is what makes the origin untrusted.

    resources.files("libera"), not Path(__file__).with_name(): this module is
    `libera.payload.installer`, so with_name looked in `libera/payload/` and
    build/engine/dist.sh has always written `libera/manifest.json`, one level up. The
    two never met. A released wheel would therefore have answered every
    `libera --payload-install` with "this build ships no manifest, so downloads
    cannot be verified", leaving --from DIR as the only way in.

    Nothing caught it because nothing could: every test that touches this
    replaces it with a lambda, and --from DIR reads the directory's own copy
    without ever asking here. It surfaced the first time the origin existed and
    a container with no payload was pointed at it.
    """
    f = _bundled_file()
    if not f.is_file():
        return None
    return Manifest.from_dict(json.loads(f.read_text(encoding="utf-8")))


def _bundled_file() -> Traversable:
    return resources.files("libera") / "manifest.json"


def can_fetch() -> bool:
    """Whether this build could install from the origin if asked.

    A release stamps manifest.json into the wheel, and that copy is what makes
    the origin ordinary storage: every download is checked against hashes that
    travelled with the application. A checkout has none, so there is nothing to
    verify against.

    Asked *before* offering, because the offer is a question. Without this the
    application asked "Download and install it now? [Y/n]", took yes, and then
    refused -- which reads as a failure when the install was never on
    offer.
    """
    return read_bundled_manifest() is not None


def _fetch(url: str, dest: Path) -> None:
    """Download one artifact, turning network failures into something readable.

    The common failure is a machine with no network, or one that cannot reach
    the origin, and as a raw traceback that tells a user nothing they can act
    on.
    """
    # A full disk is not a network fault, and was reported as one, with advice
    # to check the connection: only what urlopen raises gets that advice.
    with dest.open("wb") as out:
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                shutil.copyfileobj(r, out, 1 << 20)
        except urllib.error.HTTPError as e:
            msg = f"{url}\n  the origin answered {e.code} {e.reason}"
            raise PayloadError(msg) from e
        except (urllib.error.URLError, TimeoutError) as e:
            reason = getattr(e, "reason", e)
            msg = (
                f"could not reach {url}\n"
                f"  {reason}\n"
                "  Check the network connection, or install from artifacts you\n"
                "  have built or been given:\n"
                "    libera --payload-install --from DIR"
            )
            raise PayloadError(msg) from e
        except OSError as e:
            msg = f"could not download {url} to {dest}\n  {e}"
            raise PayloadError(msg) from e


# Platforms this release does not build, and the last release that does. 0.5
# lost its arm64 Linux builder: a wheel installed there would otherwise fail on
# "no core artifact", naming nothing to do about it. build/install/install.sh
# pins the same version for its Flatpak and pip paths.
LAST_RELEASE_FOR = {"linux-arm64": "0.4.1"}


def _artifacts_for(manifest: Manifest, platform: str) -> list[Artifact]:
    """This machine's core and the shared artifacts, refused as a PayloadError
    when the manifest has no core for it, which every caller already reports."""
    try:
        return manifest.select(platform)
    except ManifestError as e:
        last = LAST_RELEASE_FOR.get(platform)
        if last is None:
            raise PayloadError(str(e)) from e
        msg = (
            f"this release of Libera Suite has no editors for {platform}; "
            f"{last} is the last one that does.\n"
            f"  install it:  pipx install 'libera=={last}'"
            f"   (or: uv tool install 'libera=={last}')\n"
            "  or run the install script, which picks it for this machine:\n"
            "    curl -fsSL https://cdn.abilian.com/libera/install.sh | sh"
        )
        raise PayloadError(msg) from e


def safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract, refusing members that would escape dest.

    The standard library's "data" filter does the checking: a
    name can stay inside dest while a link does not -- a symlink to /etc,
    then a file written through it -- and only the filter looks at both. It
    matters where the hash does not protect us: `--from DIR` and
    `--trust-manifest`. The payload's own links are relative and inside it.
    """
    try:
        tar.extractall(dest, filter="data")
    except tarfile.FilterError as e:
        msg = f"refusing tar member outside the payload: {e}"
        raise PayloadError(msg) from e


def _refuse_another_build(bundled: Manifest, local: Path) -> None:
    """Refuse a directory the wheel's manifest does not describe, naming both.

    The wheel's manifest decides, for a local directory too. In a checkout it
    is the copy the last release left in src/libera/, gitignored, so every
    build after that release was refused as a core that "failed verification",
    with two hashes and nothing to say where the expected one came from.
    """
    f = local / "manifest.json"
    if not f.is_file():
        return
    found = Manifest.read(f)
    theirs = {a.name: a for a in found.artifacts}
    wanted = bundled.select(locate.get_current_platform())
    if all(theirs.get(a.name) == a for a in wanted):
        return
    msg = (
        f"{local} holds another build than the one this libera verifies against:\n"
        f"  {f}: built {found.built}, from {found.commit[:9]}\n"
        f"  {_bundled_file()}: built {bundled.built}, from {bundled.commit[:9]}\n"
        "  In a checkout, the second is the manifest a release left behind;\n"
        "  remove it to install a local build."
    )
    raise PayloadError(msg)


def _read_manifest(
    base_url: str, local: Path | None, *, trust_manifest: bool
) -> Manifest:
    """The manifest that decides what gets installed, and whether to trust it.

    The wheel's copy is authoritative -- that is what makes the origin untrusted
    storage. Without it, a local directory is still fine (the user chose those
    bytes), but a download needs an explicit --trust-manifest.
    """
    bundled = read_bundled_manifest()
    if bundled is not None:
        if local is not None:
            _refuse_another_build(bundled, local)
        return bundled
    if local is not None:
        f = local / "manifest.json"
        if not f.is_file():
            msg = (
                f"no manifest.json in {local}\n"
                "  --from wants a directory of built artifacts, as written by\n"
                "  build/engine/dist.sh: BUILD_ROOT/out/dist/<payload-version>/"
            )
            raise PayloadError(msg)
        return Manifest.read(f)
    if not trust_manifest:
        msg = (
            "this copy was installed from source, not from a release, so it has\n"
            "no checksums of its own to check a download against.\n"
            "  check it against the download site's:  libera --payload-install"
            " --trust-manifest\n"
            "  or install a local build:  libera --payload-install --from DIR"
        )
        raise PayloadError(msg)
    url = f"{base_url}/manifest.json"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return Manifest.from_dict(json.loads(r.read()))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        msg = f"could not read the manifest at {url}\n  {getattr(e, 'reason', e)}"
        raise PayloadError(msg) from e


def _finish(dest: Path, say: Callable[[str], object]) -> None:
    """Generate the local files and confirm the result is usable."""
    say("  generating fonts and configuration")
    found = generate.generate(dest)
    say(f"    {found} fonts")
    if not locate.is_complete(dest):
        msg = "installed payload is incomplete"
        raise PayloadError(msg)


def _check_room(where: Path, artifacts: list[Artifact]) -> None:
    """Refuse before downloading if the disk cannot hold the result.

    `No space left on device` arrives a hundred megabytes in, from inside
    copytree, as six tracebacks about individual files. The sizes are in the
    manifest, so the answer is knowable first.

    Twice the compressed total: the tarballs are deleted as they are extracted,
    so the peak is the unpacked payload (about 1.5x compressed) plus the one
    tarball being unpacked. Approximate, and on the generous side
    of a number that is cheap to check and expensive to get wrong.
    """
    need = 2 * sum(a.size for a in artifacts)
    free = shutil.disk_usage(where).free
    if free >= need:
        return
    msg = (
        f"not enough room in {where}\n"
        f"  needs about {need / 1e6:.0f} MB free, has {free / 1e6:.0f} MB\n"
        f"  the payload unpacks to roughly "
        f"{sum(a.size for a in artifacts) * 1.5 / 1e6:.0f} MB"
    )
    raise PayloadError(msg)


def _stage(
    tmpdir: Path,
    artifacts: list[Artifact],
    source: Path | str,
    say: Callable[[str], object],
) -> Path:
    """Every artifact copied from a directory or fetched from a URL, checked
    against its hash, and unpacked into `tmpdir`/payload. Nothing is unpacked
    from a file that failed its check."""
    staged = tmpdir / "payload"
    staged.mkdir()
    for a in artifacts:
        got = tmpdir / a.name
        if isinstance(source, Path):
            shutil.copyfile(source / a.name, got)
        else:
            say(f"  fetching {a.name} ({a.size / 1e6:.0f} MB)")
            _fetch(f"{source}/{a.name}", got)

        if problem := a.problem_with(got):
            raise PayloadError(problem)

        with tarfile.open(got, "r:gz") as tar:
            safe_extract(tar, staged)
        got.unlink()
    return staged


def _swap_in(staged: Path, dest: Path, say: Callable[[str], object]) -> None:
    """Put the staged payload where the old one was, generate its local files
    there, and put the old one back if either fails.

    The generated files record absolute paths, so they have to be written
    where the payload will actually live -- generating in the staging
    directory bakes in a temporary path that is gone a moment later. Hence:
    move first, generate second, and roll back if that fails.
    """
    previous = dest.with_name(dest.name + ".previous")
    shutil.rmtree(previous, ignore_errors=True)
    if dest.exists():
        dest.rename(previous)

    # The rename and the generation share one rollback. They used to be
    # separate, so a failed move left dest broken and the working payload
    # stranded at .previous -- the one outcome worse than not installing.
    # BaseException: a Ctrl-C while the fonts are generated is the likeliest
    # interruption of all, and it left the working payload at .previous,
    # where nothing looks and the next install deletes it. Re-raised.
    try:
        staged.rename(dest)
        _finish(dest, say)
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        if previous.exists():
            previous.rename(dest)
        raise
    shutil.rmtree(previous, ignore_errors=True)


def install(
    *,
    source: Path | str | None = None,
    dest: Path | None = None,
    trust_manifest: bool = False,
    say: Callable[[str], object] = print,
) -> Payload:
    """Fetch or copy the artifacts, verify them, unpack, and generate.

    ``source`` is a local directory of artifacts or a base URL; the default is
    the public origin. Nothing is installed until every hash matches.
    """
    dest = dest or locate.get_installed_dir()
    want_platform = locate.get_current_platform()

    is_url = bool(source) and str(source).startswith(("http://", "https://"))
    local = Path(source) if source and not is_url else None
    # Before the manifest, which is read from it: with no --from, `source` is
    # None, and --trust-manifest asked for "None/manifest.json".
    base_url = str(source or f"{DEFAULT_ORIGIN}/{locate.PAYLOAD_VERSION}")
    # First, so that what is coming is named before the hundred megabytes.
    verb = "Installing" if local else "Downloading"
    say(f"{verb} Libera Suite's components, version {locate.PAYLOAD_VERSION}")
    manifest = _read_manifest(base_url, local, trust_manifest=trust_manifest)

    if manifest.payload_version != locate.PAYLOAD_VERSION:
        msg = (
            f"manifest is for payload {manifest.payload_version}, "
            f"this libera needs {locate.PAYLOAD_VERSION}"
        )
        raise PayloadError(msg)

    artifacts = _artifacts_for(manifest, want_platform)

    if local is not None:
        missing = [a.name for a in artifacts if not (local / a.name).is_file()]
        if missing:
            msg = (
                f"{local} is missing {', '.join(missing)}\n"
                f"  the manifest lists them for {want_platform}; "
                "build them with build/engine/dist.sh"
            )
            raise PayloadError(msg)

    # Staged beside the destination, where tempfile would default to /tmp.
    #
    # The move at the end has to be a rename, and a rename cannot cross a
    # filesystem. On a machine where /tmp is its own mount (tmpfs, or a small
    # partition, as on most Linux boxes), shutil.move silently degrades to
    # copytree. Three things follow: the payload needs its own size twice; the
    # install stops being atomic; a copy that runs out of room leaves a
    # half-populated payload where a working one used to be. All three were
    # measured on an arm64 box with a small /tmp:
    #
    #   OSError: [Errno 18] Invalid cross-device link:
    #     '/tmp/libera-payload-4i926s5m/payload' -> '~/.local/share/.../0.2'
    #   ... [Errno 28] No space left on device
    #
    # Here the rename is within one directory, so it is atomic and free; the
    # downloads also land on the filesystem that has to hold them anyway.
    dest.parent.mkdir(parents=True, exist_ok=True)
    _check_room(dest.parent, artifacts)

    with tempfile.TemporaryDirectory(prefix=".libera-staging-", dir=dest.parent) as tmp:
        staged = _stage(Path(tmp), artifacts, local or base_url, say)
        (staged / "payload.json").write_text(
            json.dumps(
                {
                    "payload_version": manifest.payload_version,
                    "platform": want_platform,
                    "font_set": manifest.font_set,
                    "built": manifest.built,
                    # Which source this binary corresponds to. Printed by
                    # `payload status`; an AGPL obligation.
                    "source": manifest.source,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _swap_in(staged, dest, say)

    installed = Payload(dest, "installed")
    _index_installed_fonts(installed, say)
    for gone in prune.remove_unused(dest.parent, keep=dest.name):
        say(f"  removed the unused payload {gone}")
    return installed


def _index_installed_fonts(layout: locate.Layout, say: Callable[[str], object]) -> None:
    """Index the machine's fonts now, while the first start waits for the
    payload anyway, so that its first window has them.

    Not a failed install when it fails: the payload works without them, and
    the next window to open tries again.
    """
    if not fonts.is_wanted() or fonts.get_index_dir(layout).is_dir():
        return
    say("  indexing the fonts installed on this machine")
    try:
        count = fonts.build(layout, fonts.get_index_dir(layout))
    except PayloadError as e:
        say(f"    not indexed: {e}")
        return
    say(f"    {count} fonts")
