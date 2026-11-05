"""push, extras, windows: what goes up to the origin, and in what order.

The payload goes under its version. What a release ships that the payload
manifest does not name -- the Flatpak bundles, the Windows installer, the two
install scripts -- carries the *application* version and sits outside it: the
two versions move independently, which is why `libera --version` prints both.
The install scripts sit at the zone root, because the URL in the README cannot
move every release.
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

from libera.manifest import Manifest, hash_file
from libera_build import repo, versions
from libera_build.artifacts import bundle_name, installer_name
from libera_build.origin.cdn import key_for, put
from libera_build.report import RefusedError, say, step

if TYPE_CHECKING:
    from libera_build.origin.place import Origin

ARCHES = ("amd64", "arm64")
# The release key, as the install pages print it. Its primary key only certifies,
# so gpg signs with the signing subkey, and a signature still names this one.
SIGNING_KEY = "E1B31B9935BEDA0C53D21A1DD35A9ACA9BE0C732"


def upload_order(manifest: Manifest) -> list[str]:
    """What `push` uploads: what the manifest names, smallest first, then the
    manifest itself.

    From the manifest rather than a glob of the dist directory, which also
    holds dist.sh's staging and, after a version bump, the previous release.
    Smallest first, so a wrong token or a missing zone costs the 3.8 MB of
    fonts rather than the 68 MB of a core. manifest.json last: a half-finished
    upload that already carries the manifest describes artifacts the origin
    does not have yet.
    """
    return [a.name for a in sorted(manifest.artifacts, key=lambda a: a.size)] + [
        "manifest.json"
    ]


def need_token(token: str | None, *, dry: bool, zone: str) -> None:
    if not token and not dry:
        msg = (
            "CDN_TOKEN is not set.\n"
            "  Mint one on the CDN host, scoped to this zone:\n"
            f"    cdn create-token 'libera releases' --org <org> --zone {zone} "
            "--scopes read,write"
        )
        raise RefusedError(msg)


def push(root: Path, origin: Origin, dist: Path, *, dry: bool) -> None:
    stamped = root / repo.MANIFEST
    if not stamped.is_file():
        msg = f"no {stamped}\n  Run: lb release collect"
        raise RefusedError(msg)
    manifest = Manifest.read(stamped)
    # The dirty check before the token check, because it is the one that costs
    # something to fix: commit, collect again, and only then come back. The
    # manifest is the provenance a user reads out of `libera --payload-status`
    # to find the source these binaries came from, which under the AGPL is the
    # point of recording it, and "a commit, plus some uncommitted changes"
    # names nothing.
    if manifest.dirty:
        if os.environ.get("ALLOW_DIRTY") != "1":
            msg = (
                "the manifest was stamped from a dirty tree, so it names no source\n"
                "  anyone could check. Commit, run collect again, then push.\n"
                "  To publish anyway: ALLOW_DIRTY=1 lb release push"
            )
            raise RefusedError(msg)
        say("    ALLOW_DIRTY=1: publishing artifacts with no reproducible provenance")
    token = os.environ.get("CDN_TOKEN")
    need_token(token, dry=dry, zone=origin.zone)

    step(f"publishing payload {origin.version} to {origin.base}/")
    names = upload_order(manifest)
    for name in names:
        src = stamped if name == "manifest.json" else dist / name
        if not src.is_file():
            msg = f"the manifest names {name} and {src} is not there"
            raise RefusedError(msg)
        put(origin, src, key_for(origin.version, name), token=token, dry=dry)
    if dry:
        step("nothing was uploaded (--dry-run)")
        return
    step("published")
    for name in names:
        say(f"    {origin.base}/{name}")
    say("\n    check it:  lb release check")


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


def put_windows(
    origin: Origin, setup: Path, app: str, *, token: str | None, dry: bool
) -> None:
    """The Windows installer and its SHA-256; then, for a release, the stable
    name and the pointer, which a pre-release leaves alone."""
    digest = setup.with_name(setup.name + ".sha256")
    # The hash file has to describe the file being published, or install.ps1
    # refuses every download of it: checked before either goes out.
    if digest.read_text(encoding="utf-8").split()[0] != hash_file(setup):
        msg = f"{digest} does not describe {setup}"
        raise RefusedError(msg)
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
            "  bundles --only windows-x86_64, then lb release windows"
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
    builder's job is detached, with nobody to ask."""
    if not signing_key_here():
        msg = f"gpg has no secret key {SIGNING_KEY} here, and a bundle goes up signed"
        raise RefusedError(msg)
    signature = signature_of(bundle)
    subprocess.run(
        [
            "gpg",
            "--yes",
            "--armor",
            "--local-user",
            SIGNING_KEY,
            "--output",
            str(signature),
            "--detach-sign",
            str(bundle),
        ],
        check=False,
    )
    checked = subprocess.run(
        ["gpg", "--status-fd", "1", "--verify", str(signature), str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    if not re.search(
        rf"^\[GNUPG:\] VALIDSIG .* {SIGNING_KEY}$", checked.stdout, re.MULTILINE
    ):
        msg = f"gpg made no good signature of {bundle.name}\n{checked.stderr}"
        raise RefusedError(msg)


def put_bundles(
    origin: Origin, bundles: Path, app: str, *, token: str | None, dry: bool
) -> None:
    """The Flatpak bundles and their signatures. Optional: an arm64 builder short
    of disk is a normal state of the world, and should not stop install.sh going
    out."""
    made = {arch: bundles / bundle_name(app, arch) for arch in ARCHES}
    here = [bundle for bundle in made.values() if bundle.is_file()]
    # All signed first: a passphrase not given then leaves the origin as it was.
    if not dry:
        for bundle in here:
            sign(bundle)
    for arch, bundle in made.items():
        if bundle not in here:
            say(f"    no bundle for {arch} ({bundle})")
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


def extras(root: Path, origin: Origin, *, dry: bool) -> None:
    """The bundles, the Windows installer if it is here, install.sh and
    install.ps1, then `latest`, which moves both install scripts."""
    token = os.environ.get("CDN_TOKEN")
    need_token(token, dry=dry, zone=origin.zone)
    app = versions.app_version(root)
    bundles = root / "build" / "out" / "bundles"
    step(f"publishing the extras for {app} to {origin.cdn_url}/{origin.zone}/")
    setup = installer_here(bundles, app)
    pre = versions.is_prerelease(app)
    # An installer in this run moves latest-windows before install.ps1 goes up;
    # a pre-release puts up no install script, so it needs neither.
    if not pre and setup is None and (problem := windows_ready(origin)):
        raise RefusedError(problem)
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

    Not `extras`: that also moves `latest`, which would name a version whose
    Flatpak bundles are not up yet.
    """
    token = os.environ.get("CDN_TOKEN")
    need_token(token, dry=dry, zone=origin.zone)
    app = versions.app_version(root)
    bundles = root / "build" / "out" / "bundles"
    step(f"publishing the Windows installer for {app} to {origin.public('bundles')}/")
    if (setup := installer_here(bundles, app)) is None:
        msg = (
            f"no {bundles}/{installer_name(app)} and .sha256\n"
            "  lb release ship bundles --only windows-x86_64 brings both here."
        )
        raise RefusedError(msg)
    put_windows(origin, setup, app, token=token, dry=dry)
    step("nothing was uploaded (--dry-run)" if dry else "published")
