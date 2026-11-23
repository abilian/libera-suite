"""A wheel of the release given another version, and nothing else changed.

The version is a label on a build: in the three packages it is in their
dist-info (its name, METADATA, RECORD), in libera's pins on the other two, in
libera's payload.version, which the host compares with the components at
start-up, and in libera-web's payload.json; the binaries and the editors do
not carry it. So `check` builds once and labels what it built as a candidate
(0.7.4+69906cd, a version PyPI refuses), and `publish` labels the same files
as the release, in seconds, rather than building them again under a new name.
"""

from __future__ import annotations

import base64
import hashlib
import shutil
import zipfile
from typing import TYPE_CHECKING

from libera_build.report import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

# The files inside a package that say its version, besides its dist-info, and
# how; each must say it exactly once.
INSIDE = {
    "libera/payload/payload.version": 'version = "{}"',
    "libera_web/payload.json": '"payload_version": "{}"',
}
# In METADATA: its own version, and libera's pins on the components.
METADATA = (
    "Version: {}",
    "Requires-Dist: libera-core=={}",
    "Requires-Dist: libera-web=={}",
)


def version_of(wheel: Path) -> str:
    """The version in a wheel's file name."""
    return wheel.name.split("-")[1]


def relabel(wheel: Path, version: str, into: Path) -> Path:
    """`wheel` as `version`, written into `into`; the new file."""
    name, old, rest = wheel.name.split("-", 2)
    into.mkdir(parents=True, exist_ok=True)
    made = into / f"{name}-{version}-{rest}"
    if old == version:
        shutil.copy2(wheel, made)
        return made
    old_info, new_info = f"{name}-{old}.dist-info/", f"{name}-{version}.dist-info/"
    record = []
    # Dated as the wheel's own RECORD below, or as zip's epoch: a bare name
    # is dated now, and the same wheel relabelled twice would be two files.
    kept = zipfile.ZipInfo(date_time=(1980, 1, 1, 0, 0, 0))
    with zipfile.ZipFile(wheel) as src, zipfile.ZipFile(made, "w") as dst:
        for item in src.infolist():
            if item.filename == f"{old_info}RECORD":
                kept = item
                continue
            data = src.read(item)
            path = item.filename
            if path.startswith(old_info):
                path = new_info + path[len(old_info) :]
            if path == f"{new_info}METADATA":
                data = rewritten(data, METADATA, old, version, path)
            elif path in INSIDE:
                data = rewritten(data, (INSIDE[path],), old, version, path)
            item.filename = path
            dst.writestr(item, data)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest())
            record.append(f"{path},sha256={digest.rstrip(b'=').decode()},{len(data)}")
        record.append(f"{new_info}RECORD,,")
        kept.filename = f"{new_info}RECORD"
        dst.writestr(kept, "\n".join(record) + "\n")
    return made


def rewritten(
    data: bytes, patterns: tuple[str, ...], old: str, new: str, path: str
) -> bytes:
    """`data` with each pattern's old version made the new one; refused when
    the first, the one every such file has, is not there exactly once: a
    file that says its version some other way would keep the old one."""
    text = data.decode("utf-8")
    for i, pattern in enumerate(patterns):
        found = text.count(pattern.format(old))
        if i == 0 and found != 1:
            msg = f"{path}: {pattern.format(old)} is there {found} times, not once"
            raise RefusedError(msg)
        text = text.replace(pattern.format(old), pattern.format(new))
    return text.encode("utf-8")
