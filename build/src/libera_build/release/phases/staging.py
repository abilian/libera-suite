"""stage: the release, every file of it, installed as users will install it,
before any of it is published.

0.7.0b1 and 0.7.0 both went to PyPI before anything had installed them, and
both were broken there for an hour: the first without its components, the
second before them. So every file `publish` uploads is gathered first into
one directory, `staged/` in the run's (artifacts.run_dir, named by the
commit), and from there:

- on every builder and here, libera, libera-core and libera-web install into
  a new environment from that directory and nowhere else, and convert a
  document;
- on every Linux builder the Flatpak bundle, and on the Windows builder the
  installer, install and open a document in a window (released_gui);

and only when all of that passed is the directory stamped, with each file's
hash. `publish` uploads that directory and refuses anything else: a file
changed or added after the stamp. Another commit's stage is another
directory, so nothing from it can be published. `stage` runs as often as
wanted; nothing leaves the builders.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from libera.manifest import hash_file
from libera_build import inventory, released_gui, repo, versions
from libera_build.artifacts import (
    app_wheel_name,
    bundle_name,
    core_wheel_name,
    installer_name,
    run_bundles,
    run_dir,
    web_wheel_name,
)
from libera_build.components import TAGS
from libera_build.hosts import LocalHost, facts_from
from libera_build.release.phases import publishing
from libera_build.released_gui import ReleasedGuiOptions
from libera_build.report import RefusedError, problems, say, step

if TYPE_CHECKING:
    from libera_build.hosts import Host
    from libera_build.inventory import Builder
    from libera_build.release.context import Context

# A window's picture of a page with a document on it; an empty canvas posts a
# few kilobytes. The GUI tests measure the ink; this has no imaging library.
MIN_SHOT_BYTES = 20_000
STAMP = "STAGED.json"


def folder(root: Path) -> Path:
    return run_dir(root) / "staged"


def bundle_files(ctx: Context) -> list[Path]:
    """The bundles the builders of this run make, as `bundles` left them here."""
    app = versions.app_version(ctx.root)
    bundles = run_bundles(ctx.root)
    found = []
    for b in ctx.builders:
        if b.os == "linux":
            found.append(bundles / bundle_name(app, b.arch))
        elif b.os == "windows":
            setup = bundles / installer_name(app)
            found += [setup, setup.with_name(setup.name + ".sha256")]
    return found


def run(ctx: Context) -> None:
    app = versions.app_version(ctx.root)
    step(f"staging {app}")
    components, own = publishing.upload_files(ctx)
    files = [*components, *own, *bundle_files(ctx)]
    problems(
        [
            f"{f} is not here: run the phase that makes it"
            for f in files
            if not f.is_file()
        ],
        "nothing was staged.",
    )
    head = repo.head(ctx.root)
    dest = folder(ctx.root)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for f in files:
        shutil.copy2(f, dest / f.name)
        say(f"    {f.name:56} {f.stat().st_size / 1e6:6.1f} MB")

    deps = [
        r
        for r in publishing.requires_of(dest / own[0].name)
        if not r.startswith("libera-")
    ]
    found = []
    for b in ctx.builders:
        host = ctx.host_for(b) if b.remote else LocalHost(Path.home())
        found += installs(host, b, dest, app, deps)
    for b in inventory.gui_remotes(ctx.builders):
        options = ReleasedGuiOptions(staged=dest, root=ctx.root)
        if not released_gui.on_host(ctx.host_for(b), b.platform, options):
            found.append(f"{b.platform}: the staged bundle did not draw a window")
    problems(found, "nothing was stamped, and publish will refuse.")

    stamp = {
        "commit": head,
        "files": {
            f.name: hash_file(f) for f in sorted(dest.iterdir()) if f.name != STAMP
        },
    }
    (dest / STAMP).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    step(f"staged: {dest}")


def installs(
    host: Host, b: Builder, dest: Path, app: str, deps: list[str]
) -> list[str]:
    """libera and this platform's components, sent there and installed from
    there alone; a problem, or nothing. The components are the version libera
    pins, which is `app` unless an exception was made by hand."""
    pins = publishing.requires_of(dest / app_wheel_name(app))
    components = {r.split("==")[0]: r.split("==")[1] for r in pins if "==" in r}
    stage = f"libera-stage/{app}"
    wanted = [
        app_wheel_name(app),
        core_wheel_name(components["libera-core"], TAGS[b.platform]),
        web_wheel_name(components["libera-web"]),
    ]
    # Overwritten file by file: the names carry the version, so nothing left
    # from another one can stand in for these.
    host.capture(f'mkdir -p "$HOME/{stage}"')
    for name in wanted:
        # scp's relative paths are the home directory, on Windows too.
        there = f"{stage}/{name}" if b.remote else f"~/{stage}/{name}"
        if host.send(dest / name, there)[0]:
            return [f"{b.platform}: could not copy {name} there"]
    # A window here too, on the Mac: no builder opens one of this platform's.
    window = b.os == "macos"
    script = publishing.install_script(app, staged=stage, deps=deps, window=window)
    out = host.capture(script)
    facts = facts_from(out)
    drawn = not window or int(facts.get("WINDOW", "0")) >= MIN_SHOT_BYTES
    if facts.get("INSTALLED") == app and facts.get("CONVERTED") == "1" and drawn:
        version = facts.get("VERSION", "?")
        kb = int(facts.get("WINDOW", "0")) // 1000
        shown = f", and a window drew it ({kb} KB)" if window else ""
        say(f"    {b.platform:<14} {version}, installed from the stage{shown}")
        return []
    tail = "\n".join(f"       | {line}" for line in out.splitlines()[-12:])
    return [f"{b.platform}: libera {app} did not install from the stage\n{tail}"]


def stamp_problems(root: Path) -> list[str]:
    """Why the staged directory is not what `publish` may upload, if it is not."""
    dest = folder(root)
    stamped = dest / STAMP
    if not stamped.is_file():
        return [f"nothing is staged at {repo.head(root)[:9]}: run stage"]
    stamp = json.loads(stamped.read_text(encoding="utf-8"))
    found = []
    # The bundles' signatures are made by `publish`, beside them, after.
    now = {f.name: f for f in dest.iterdir() if f.name != STAMP and f.suffix != ".asc"}
    for name in sorted(set(now) - set(stamp["files"])):
        found.append(f"{name} was added after the stage")
    for name, sha in sorted(stamp["files"].items()):
        if name not in now:
            found.append(f"{name} was staged and is gone")
        elif hash_file(now[name]) != sha:
            found.append(f"{name} changed after the stage")
    return found


def publish(ctx: Context) -> None:
    """What `stage` stamped, uploaded; refused if it no longer holds."""
    publishing.publish(ctx, folder(ctx.root), staged(ctx.root))


def staged(root: Path) -> list[Path]:
    """The staged files, refused unless the stamp still holds."""
    found = stamp_problems(root)
    if found:
        raise RefusedError("\n  ".join(["the stage does not hold:", *found]))
    return sorted(
        f for f in folder(root).iterdir() if f.name != STAMP and f.suffix != ".asc"
    )
