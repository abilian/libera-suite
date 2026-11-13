"""The staged origin: the stage laid out as the CDN zone, and served on each
test machine's own loopback, so that it runs the install page's command with
one setting changed, LIBERA_ORIGIN, against files no user can reach yet.

The zone is what `publish` puts on the CDN (origin.publish.extras): the two
install scripts at its root, the bundles and their pointers under bundles/.
Beside them, pypi/ holds the three packages, which pip reads as a page of
links (PIP_FIND_LINKS) while everything else comes from PyPI, as it will.

Served by each machine to itself rather than by this Mac to all of them: a
builder is reached over ssh and need not be able to reach back. Served as the
CDN serves it, the scripts and the pointers as text/plain, since that is what
install.ps1's Invoke-RestMethod reads them as.
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from libera_build import versions
from libera_build.artifacts import bundle_name, installer_name

if TYPE_CHECKING:
    from pathlib import Path

PYPI = "pypi"
POINTERS = ("latest", "latest-windows")


def lay_out(files: list[Path], zone: Path, app: str, root: Path) -> Path:
    """`files`, the staged release, linked into `zone` as the CDN holds them,
    with the install scripts of this tree and the pointers naming `app`."""
    if zone.exists():
        shutil.rmtree(zone)
    (zone / "bundles").mkdir(parents=True)
    (zone / PYPI).mkdir()
    for f in files:
        package = f.name.endswith((".whl", ".tar.gz"))
        os.link(f, zone / (PYPI if package else "bundles") / f.name)
    for script in ("install.sh", "install.ps1"):
        shutil.copy2(root / "build" / "install" / script, zone / script)
    for pointer in POINTERS:
        (zone / "bundles" / pointer).write_text(f"{app}\n", encoding="utf-8")
    return zone


def for_platform(platform: str, app: str) -> list[str]:
    """What a machine of `platform` reads from the zone, as paths in it: its
    install script, its pointer and its download."""
    if platform.startswith("windows-"):
        setup = f"bundles/{installer_name(app)}"
        return ["install.ps1", "bundles/latest-windows", setup, f"{setup}.sha256"]
    arch = platform.rpartition("-")[2].replace("x86_64", "amd64")
    return ["install.sh", "bundles/latest", f"bundles/{bundle_name(app, arch)}"]


def remote(app: str) -> str:
    """Where a builder is sent its part of the zone, under its home."""
    return f"libera-stage/{app}/origin"


# A directory served on 127.0.0.1, its address in $ORIGIN, stopped on exit.
# Python, which every test machine has: the builders run lb with it. The port
# is the system's choice, so two runs never meet; Git Bash's paths are
# rewritten into Windows' for a native Python by `pwd -W`.
SERVE = """
served=$(cd {directory} && (pwd -W 2>/dev/null || pwd))
log="${{TMPDIR:-/tmp}}/libera-origin-$$.log"
python3 -u - "$served" > "$log" 2>&1 <<'__LIBERA_SERVE__' &
import functools, http.server, sys
class Zone(http.server.SimpleHTTPRequestHandler):
    extensions_map = {{
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        "": "text/plain; charset=utf-8",
        ".sh": "text/plain; charset=utf-8",
        ".ps1": "text/plain; charset=utf-8",
        ".sha256": "text/plain; charset=utf-8",
    }}
    def log_message(self, *args):
        pass
handler = functools.partial(Zone, directory=sys.argv[1])
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
print(f"PORT={{server.server_address[1]}}", flush=True)
server.serve_forever()
__LIBERA_SERVE__
server=$!
trap 'kill $server 2>/dev/null' EXIT
port=
for i in $(seq 50); do
    port=$(sed -n 's/^PORT=//p' "$log")
    [ -n "$port" ] && break
    sleep 0.2
done
[ -n "$port" ] || {{
    cat "$log"; echo "__LIBERA__=the staged origin did not start"; exit
}}
export LIBERA_ORIGIN="http://127.0.0.1:$port"
"""


def serve(directory: str, app: str) -> str:
    """bash that serves `directory` (a shell expression) and exports what the
    install scripts read: LIBERA_ORIGIN, and LIBERA_VERSION for a
    pre-release, which no pointer ever names."""
    script = SERVE.format(directory=directory)
    if versions.is_prerelease(app):
        script += f"export LIBERA_VERSION={app}\n"
    return script
