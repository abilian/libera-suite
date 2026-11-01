"""The payload manifest: which artifacts make a payload, their sizes and hashes,
and the source they were built from.

One definition for everyone who reads or writes it. build/engine/dist.sh writes it
(`python3 -m libera.manifest stamp`), `lb release` reads it before publishing,
and the installer verifies every download against the copy shipped in the
wheel, which is what makes the origin untrusted storage. Each used to have its
own idea of the format.

Python 3.10 and the standard library only, on purpose: dist.sh runs inside the
build container, Ubuntu 22.04, whose Python is 3.10, and imports this from the
checkout with nothing installed. Hence also its place, at the top of `libera`
and not under `libera.payload`, whose __init__ imports tomllib (3.11). ruff's
target-version holds the syntax to 3.10; nothing holds the library to it, so
check what you import. See notes/plans/build-tooling.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Where the corresponding source lives, per AGPL: a pinned SHA plus a patch
# series that applies to it cleanly. Repositories are public; we do not host
# tarballs.
#
REPOSITORIES = ("https://github.com/abilian/libera-suite",)
UPSTREAM = "https://github.com/Euro-Office"


class ManifestError(ValueError):
    """A manifest that cannot be used as it is, said so that it can be fixed."""


@dataclass(frozen=True)
class Artifact:
    name: str
    kind: str  # "core", or what the name starts with: "editors", "fonts"
    platform: str | None  # for a core; None for the shared ones
    size: int
    sha256: str

    def problem_with(self, path: Path) -> str | None:
        """Why the file at `path` is not this artifact, or None if it is."""
        digest = hash_file(path)
        if digest != self.sha256:
            return (
                f"{self.name} failed verification\n"
                f"  expected {self.sha256}\n  got      {digest}"
            )
        return None


@dataclass(frozen=True)
class Manifest:
    payload_version: str
    artifacts: tuple[Artifact, ...]
    built: str | None = None
    font_set: str | None = None
    # pins, libera_commit, libera_dirty, repositories, upstream. Kept as the
    # mapping it is in the file: `libera --payload-status` prints it whole.
    source: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, doc: dict) -> Manifest:
        try:
            return cls(
                payload_version=doc["payload_version"],
                artifacts=tuple(Artifact(**a) for a in doc["artifacts"]),
                built=doc.get("built"),
                font_set=doc.get("font_set"),
                source=doc.get("source", {}),
            )
        except (KeyError, TypeError) as e:
            msg = f"not a payload manifest: {e}"
            raise ManifestError(msg) from e

    @classmethod
    def read(cls, path: Path) -> Manifest:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def to_json(self) -> str:
        """The file, keys in the order it has always had them."""
        doc = {
            "payload_version": self.payload_version,
            "built": self.built,
            "font_set": self.font_set,
            "artifacts": [asdict(a) for a in self.artifacts],
            "source": self.source,
        }
        return json.dumps(doc, indent=2) + "\n"

    @property
    def commit(self) -> str:
        return self.source.get("libera_commit") or ""

    @property
    def dirty(self) -> bool:
        return bool(self.source.get("libera_dirty"))

    @property
    def core_platforms(self) -> list[str]:
        return sorted(a.platform or "" for a in self.artifacts if a.kind == "core")

    def select(self, platform: str) -> list[Artifact]:
        """What a machine of `platform` installs: its own core, and the shared
        artifacts. A manifest with no core for it is refused here, before any
        download."""
        chosen = [
            a for a in self.artifacts if a.kind != "core" or a.platform == platform
        ]
        if not any(a.kind == "core" for a in chosen):
            msg = f"manifest has no core artifact for {platform}"
            raise ManifestError(msg)
        return chosen


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(path: Path) -> Artifact:
    """An artifact, from its file. The platform comes from the name, not from
    the machine doing the describing. A release's directory holds every
    platform's core, each built on its own platform and collected onto one
    machine; labelling them all with whichever machine wrote the manifest last
    would hand macOS users a Linux build."""
    if path.name.startswith("core-"):
        kind, platform = "core", path.name[len("core-") : -len(".tar.gz")]
    else:
        kind, platform = path.name.split(".")[0].split("-")[0], None
    return Artifact(path.name, kind, platform, path.stat().st_size, hash_file(path))


def read_pins(pins_toml: Path) -> dict[str, str]:
    """The [repos] table of build/upstream/pins.toml, read by hand: there is no
    tomllib in 3.10."""
    pins = {}
    section = None
    for raw in pins_toml.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("["):
            section = line.strip("[]")
        elif section == "repos" and "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            pins[key.strip()] = value.split("#")[0].strip().strip('"')
    return pins


def _git(repo: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def stamp(
    dist: Path,
    *,
    payload_version: str,
    font_set: str,
    repo: Path,
    now: float | None = None,
) -> Manifest:
    """A manifest over every artifact in `dist`, not just this run's: a release
    needs one core per platform, built on each and collected into one
    directory."""
    return Manifest(
        payload_version=payload_version,
        built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        font_set=font_set,
        artifacts=tuple(describe(p) for p in sorted(dist.glob("*.tar.gz"))),
        source={
            "pins": read_pins(repo / "build" / "upstream" / "pins.toml"),
            "libera_commit": _git(repo, "rev-parse", "HEAD"),
            "libera_dirty": bool(_git(repo, "status", "--porcelain")),
            "repositories": list(REPOSITORIES),
            "upstream": UPSTREAM,
        },
    )


def main(argv: list[str] | None = None) -> int:
    """`python3 -m libera.manifest stamp DIST ...`: what dist.sh runs."""
    parser = argparse.ArgumentParser(prog="python3 -m libera.manifest")
    sub = parser.add_subparsers(dest="command", required=True)
    stamp_ = sub.add_parser(
        "stamp", help="write DIST/manifest.json over DIST's tarballs"
    )
    stamp_.add_argument("dist", type=Path)
    stamp_.add_argument("--payload-version", required=True)
    stamp_.add_argument("--font-set", required=True)
    stamp_.add_argument("--repo", type=Path, required=True, help="the checkout's root")
    args = parser.parse_args(argv)

    manifest = stamp(
        args.dist,
        payload_version=args.payload_version,
        font_set=args.font_set,
        repo=args.repo,
    )
    (args.dist / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    for a in manifest.artifacts:
        print(f"    {a.name:26} {a.size / 1e6:7.1f} MB  {a.sha256[:16]}…")
    if manifest.dirty:
        print("    WARNING: built from a dirty tree; provenance is not reproducible")
    print(f"    platforms: {', '.join(manifest.core_platforms)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
