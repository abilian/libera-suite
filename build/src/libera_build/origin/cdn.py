"""Writing to the CDN: one PUT per object, which is the whole of its upload API.

No `cdn` binary and no curl: five named files need none of what a sync tool
adds, and its skip-if-matching compares MD5 while the manifest beside them
already carries SHA-256.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http import HTTPStatus
from typing import TYPE_CHECKING

from libera_build.report import RefusedError, say

if TYPE_CHECKING:
    from pathlib import Path

    from libera_build.origin.place import Origin

# The PowerShell installer and the pointers are read before they are run or
# followed. text/plain and not application/x-sh: a browser that offers to
# download install.sh instead of showing it has made `curl URL | sh` harder to
# audit than it needed to be.
CONTENT_TYPES = (
    (".sh", "text/plain; charset=utf-8"),
    (".ps1", "text/plain; charset=utf-8"),
    (".sha256", "text/plain; charset=utf-8"),
    (".asc", "text/plain; charset=utf-8"),
    (".flatpak", "application/vnd.flatpak"),
    (".exe", "application/vnd.microsoft.portable-executable"),
)
POINTERS = ("latest", "latest-windows")


def content_type(name: str) -> str:
    if name in POINTERS:
        return "text/plain; charset=utf-8"
    for suffix, kind in CONTENT_TYPES:
        if name.endswith(suffix):
            return kind
    return "application/octet-stream"


def key_for(prefix: str, name: str) -> str:
    """The object's key. An empty prefix is the zone root, where install.sh
    goes; joining it with a slash anyway stored the object under a directory
    called "", which the CDN accepts and nothing then finds."""
    return f"{prefix}/{name}" if prefix else name


def answer_problem(status: int, body: str, *, sent: int, zone: str) -> str | None:
    """What the CDN's answer to a PUT says went wrong, or None.

    Asserted on what came back, not on the transfer's status: the answer says
    what was stored, and a size that disagrees with the file means the body did
    not arrive whole, which is the failure that would otherwise be a success.
    """
    if status == HTTPStatus.NOT_FOUND:
        return (
            f"the CDN has no zone called '{zone}' ({body})\n"
            "  It is created on the CDN host, where the database is:\n"
            f"    cdn create-zone {zone} --org <org>"
        )
    if status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
        return f"the token was refused ({status}): {body}"
    if status not in {HTTPStatus.OK, HTTPStatus.CREATED}:
        return f"{status}: {body}"
    try:
        stored = json.loads(body).get("size")
    except (ValueError, AttributeError):
        stored = None
    if stored != sent:
        kept = "nothing" if stored is None else stored
        return f"sent {sent} bytes, the CDN stored {kept}"
    return None


def put(origin: Origin, src: Path, key: str, *, token: str | None, dry: bool) -> None:
    """Upload one file to `key`, and refuse unless the CDN says it stored it all."""
    size = src.stat().st_size
    url = origin.api(key)
    if dry:
        say(f"    would PUT {key} ({size // 1_000_000} MB) -> {url}")
        return
    print(f"    {key:<40} {size // 1_000_000:6} MB  ", end="", flush=True)
    with src.open("rb") as body:
        request = urllib.request.Request(
            url,
            data=body,
            method="PUT",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type(key.rsplit("/", 1)[-1]),
                "Content-Length": str(size),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as r:
                status, answer = r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, answer = e.code, e.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            say("FAILED")
            msg = f"upload failed: {key}: {getattr(e, 'reason', e)}"
            raise RefusedError(msg) from e
    if problem := answer_problem(status, answer, sent=size, zone=origin.zone):
        say("FAILED")
        msg = f"{key}: {problem}"
        raise RefusedError(msg)
    say("stored")
