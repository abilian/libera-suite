"""extras, windows: what goes up to the CDN, and in what order.

The Flatpak bundles, the Windows installer and the two install scripts; since
0.7 nothing downloads a payload from it. The install scripts sit at the zone
root, because the URL in the README cannot move every release; the pointers
under bundles/ move last, so that nothing ever names a file not up yet.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from libera.manifest import hash_file
from libera_build import versions
from libera_build.artifacts import BUNDLES_DIR, bundle_name, installer_name
from libera_build.origin.cdn import key_for, put
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from libera_build.origin.place import Origin

ARCHES = ("amd64", "arm64")
# The release key, as the install pages print it. Its primary key only certifies,
# so gpg signs with the signing subkey, and a signature still names this one.
SIGNING_KEY = "E1B31B9935BEDA0C53D21A1DD35A9ACA9BE0C732"


def need_token(token: str | None, *, dry: bool, zone: str) -> None:
    if not token and not dry:
        msg = (
            "CDN_TOKEN is not set.\n"
            "  Mint one on the CDN host, scoped to this zone:\n"
            f"    cdn create-token 'libera releases' --org <org> --zone {zone} "
            "--scopes read,write"
        )
        raise RefusedError(msg)


def pointer(
    origin: Origin, name: str, value: str, *, token: str | None, dry: bool
) -> None:
    """One line holding a version, under bundles/: what an install script reads
    to learn which file to fetch, so the script need not be re-published every
    release to carry a version number. A copy and not a redirect: the CDN
    serves objects, and this is one PUT rather than a rule to maintain."""
    with tempfile.TemporaryDirectory() as scratch:
        f = Path(scratch) / name
        f.write_text(f"{value}\n", encoding="utf-8")
        put(origin, f, key_for("bundles", name), token=token, dry=dry)


def installer_here(bundles: Path, app: str) -> Path | None:
    """The Windows installer, if it is here with its SHA-256: brought by
    `ship`'s bundles, or built on this machine. None is a normal state, since
    a release's Flatpaks can go out before its Windows build."""
    setup = bundles / installer_name(app)
    digest = setup.with_name(setup.name + ".sha256")
    return setup if setup.is_file() and digest.is_file() else None


def hash_problem(setup: Path) -> Path:
    """The installer's .sha256, refused unless it describes the installer:
    install.ps1 checks one against the other, and would refuse every download."""
    digest = setup.with_name(setup.name + ".sha256")
    if digest.read_text(encoding="utf-8").split()[0] != hash_file(setup):
        msg = f"{digest} does not describe {setup}"
        raise RefusedError(msg)
    return digest


def put_windows(
    origin: Origin, setup: Path, app: str, *, token: str | None, dry: bool
) -> None:
    """The Windows installer and its SHA-256; then, for a release, the stable
    name and the pointer, which a pre-release leaves alone."""
    digest = hash_problem(setup)
    put(origin, setup, key_for("bundles", setup.name), token=token, dry=dry)
    put(origin, digest, key_for("bundles", digest.name), token=token, dry=dry)
    if versions.is_prerelease(app):
        say(f"    {app} is a pre-release: no stable name, no latest-windows")
        return
    # And under a name without the version: the link on the download page,
    # which should not move every release. install.ps1 fetches the versioned
    # name, so its hash is checked against the file it names.
    put(
        origin,
        setup,
        key_for("bundles", "Libera-Suite-Setup.exe"),
        token=token,
        dry=dry,
    )
    # Last, so that install.ps1 never names an installer that is not up yet.
    pointer(origin, "latest-windows", app, token=token, dry=dry)


def windows_ready(origin: Origin) -> str | None:
    """Why install.ps1 must not be republished yet, or None.

    It installs the version in bundles/latest-windows, which only a published
    Windows installer moves, so a release's Flatpaks can go out a week before
    its Windows build. Republished while that pointer names no installer, it
    would fail every Windows install.
    """
    try:
        with urllib.request.urlopen(
            origin.public("bundles/latest-windows"), timeout=30
        ) as r:
            named = r.read().decode("utf-8").strip()
        head = urllib.request.Request(
            origin.public(f"bundles/{installer_name(named)}"), method="HEAD"
        )
        with urllib.request.urlopen(head, timeout=30):
            return None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return (
            f"{origin.public('bundles/latest-windows')} names no installer ({e}),\n"
            "  and install.ps1 would then fail every Windows install. Nothing was\n"
            "  uploaded. Publishing an installer moves it: lb release ship\n"
            "  bundles --only windows-x86_64, then lb release upload windows"
        )


def signing_key_here() -> bool:
    gpg = shutil.which("gpg")
    return (
        gpg is not None
        and subprocess.run(
            [gpg, "--list-secret-keys", SIGNING_KEY], capture_output=True, check=False
        ).returncode
        == 0
    )


def signature_of(bundle: Path) -> Path:
    return bundle.with_name(f"{bundle.name}.asc")


def sign(bundle: Path) -> None:
    """A detached signature beside `bundle`, made on the machine that publishes:
    that is where the key is, and where someone can answer its passphrase. A
    builder's job is detached, with nobody to ask.

    A good signature already there is kept: `publish` signs every bundle before
    PyPI takes the packages, and the upload after asks for nothing."""
    if signature_problem(bundle) is None:
        return
    if not signing_key_here():
        msg = f"gpg has no secret key {SIGNING_KEY} here, and a bundle goes up signed"
        raise RefusedError(msg)
    subprocess.run(
        [
            "gpg",
            "--yes",
            "--armor",
            "--local-user",
            SIGNING_KEY,
            "--output",
            str(signature_of(bundle)),
            "--detach-sign",
            str(bundle),
        ],
        check=False,
    )
    # gpg's status says whether it signed; its exit code, not reliably.
    if problem := signature_problem(bundle):
        msg = f"gpg made no good signature of {bundle.name}\n{problem}"
        raise RefusedError(msg)


def signature_problem(bundle: Path) -> str | None:
    """Why the signature beside `bundle` is not a good one by the release key,
    or None."""
    checked = subprocess.run(
        ["gpg", "--status-fd", "1", "--verify", str(signature_of(bundle)), str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    if re.search(
        rf"^\[GNUPG:\] VALIDSIG .* {SIGNING_KEY}$", checked.stdout, re.MULTILINE
    ):
        return None
    return checked.stderr.strip() or "no signature"


def bundles_here(bundles: Path, app: str) -> dict[str, Path | None]:
    """Each architecture's Flatpak bundle, or None. Optional: an arm64 builder
    short of disk is a normal state of the world, and should not stop
    install.sh going out."""
    made = {arch: bundles / bundle_name(app, arch) for arch in ARCHES}
    return {arch: b if b.is_file() else None for arch, b in made.items()}


def put_bundles(
    origin: Origin, bundles: Path, app: str, *, token: str | None, dry: bool
) -> None:
    """The Flatpak bundles and their signatures, which `ready` made."""
    for arch, bundle in bundles_here(bundles, app).items():
        if bundle is None:
            say(f"    no bundle for {arch}")
            continue
        put(origin, bundle, key_for("bundles", bundle.name), token=token, dry=dry)
        if not dry:
            signature = signature_of(bundle)
            put(
                origin,
                signature,
                key_for("bundles", signature.name),
                token=token,
                dry=dry,
            )


def ready(root: Path, origin: Origin, *, dry: bool, bundles: Path) -> None:
    """Everything `extras` could refuse, refused before anything goes up:
    `publish` runs it before PyPI takes the packages, which has no undo, so a
    passphrase not given or an origin naming no installer leaves the release
    as it was rather than half out. Signs the bundles."""
    need_token(os.environ.get("CDN_TOKEN"), dry=dry, zone=origin.zone)
    app = versions.app_version(root)
    # An installer in this run moves latest-windows before install.ps1 goes up;
    # a pre-release puts up no install script, so it needs neither.
    setup = installer_here(bundles, app)
    pre = versions.is_prerelease(app)
    if not pre and setup is None and (problem := windows_ready(origin)):
        raise RefusedError(problem)
    if setup is not None:
        hash_problem(setup)
    if not dry:
        for bundle in bundles_here(bundles, app).values():
            if bundle is not None:
                sign(bundle)


def extras(
    root: Path, origin: Origin, *, dry: bool, bundles: Path | None = None
) -> None:
    """The bundles, the Windows installer if it is here, install.sh and
    install.ps1, then `latest`, which moves both install scripts. From
    `bundles`, the staged release when `publish` calls it, else where the
    builders' bundles are brought."""
    bundles = bundles or root / BUNDLES_DIR
    ready(root, origin, dry=dry, bundles=bundles)
    token = os.environ.get("CDN_TOKEN")
    app = versions.app_version(root)
    step(f"publishing the extras for {app} to {origin.cdn_url}/{origin.zone}/")
    setup = installer_here(bundles, app)
    pre = versions.is_prerelease(app)
    put_bundles(origin, bundles, app, token=token, dry=dry)
    if setup:
        put_windows(origin, setup, app, token=token, dry=dry)
    else:
        say("    no Windows installer here; lb release ship bundles brings it")
    if pre:
        say(f"    {app} is a pre-release: the install scripts and latest stay")
        step("nothing was uploaded (--dry-run)" if dry else "published")
        return
    put(
        origin,
        root / "build" / "install" / "install.sh",
        "install.sh",
        token=token,
        dry=dry,
    )
    put(
        origin,
        root / "build" / "install" / "install.ps1",
        "install.ps1",
        token=token,
        dry=dry,
    )
    pointer(origin, "latest", app, token=token, dry=dry)
    step("nothing was uploaded (--dry-run)" if dry else "published")
    if not dry:
        say(f"    check it:  curl -fsS {origin.public('install.sh')} | head -5")


def windows(root: Path, origin: Origin, *, dry: bool) -> None:
    """The Windows installer on its own, for a Windows build that comes after
    the release's Flatpaks: `lb release ship bundles --only windows-x86_64`
    brings it here, and this sends it up.

    Not `lb release upload`: that also moves `latest`, which would name a version whose
    Flatpak bundles are not up yet.
    """
    token = os.environ.get("CDN_TOKEN")
    need_token(token, dry=dry, zone=origin.zone)
    app = versions.app_version(root)
    bundles = root / BUNDLES_DIR
    step(f"publishing the Windows installer for {app} to {origin.public('bundles')}/")
    if (setup := installer_here(bundles, app)) is None:
        msg = (
            f"no {bundles}/{installer_name(app)} and .sha256\n"
            "  lb release ship bundles --only windows-x86_64 brings both here."
        )
        raise RefusedError(msg)
    put_windows(origin, setup, app, token=token, dry=dry)
    step("nothing was uploaded (--dry-run)" if dry else "published")
