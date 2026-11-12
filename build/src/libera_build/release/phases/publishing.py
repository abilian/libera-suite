"""publish and verify: PyPI, then the bundles and install scripts on the CDN."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from libera_build import report, versions
from libera_build.artifacts import core_sdist_name, core_wheel_name, web_wheel_name
from libera_build.components import TAGS
from libera_build.hosts import LocalHost, facts_from
from libera_build.origin import place, publish as cdn
from libera_build.process import run_here
from libera_build.release import plan
from libera_build.release.phases import components
from libera_build.report import problems, say, step

# PyPI's simple index: `uv publish --check-url` reads it to skip a file
# already up, and the install check installs from it and nothing else.
PYPI_SIMPLE = "https://pypi.org/simple/"
CHECK_END = "__LIBERA_CHECK_END__"

if TYPE_CHECKING:
    from collections.abc import Sequence

    from libera_build.release.context import Context


def publish(ctx: Context, staged: list[Path]) -> None:
    """PyPI, then the bundles and the install scripts: the staged files and
    nothing else. The one phase with no undo.

    PyPI refuses a version it has already seen, even after a yank, so a
    mistaken publish costs a version number. It asks unless told not to, and it
    asks on /dev/tty: this is sometimes run under tmux with its output
    redirected, and a prompt nobody can see is a hang.
    """
    app = versions.app_version(ctx.root)
    step(f"publishing libera {app}")
    components = [
        f for f in staged if f.name.startswith(("libera_core-", "libera_web-"))
    ]
    own = [
        f
        for f in staged
        if f.name.startswith(f"libera-{app}") and f.suffix != ".flatpak"
    ]
    for f in [*components, *own]:
        say(f"    {f.name}")
    if not ctx.yes:
        confirm(app)
    # The components first: `libera` names them, and a `libera` up without
    # them is what 0.7.0b1 and 0.7.0 were, a release nothing could install.
    # Files PyPI already holds, byte for byte, are skipped, so a publish that
    # broke part way is run again rather than repaired by hand.
    for files in (components, own):
        run_here(
            ["uv", "publish", "--check-url", PYPI_SIMPLE, *map(str, files)],
            "publish",
            cwd=ctx.root,
        )
    cdn.extras(ctx.root, place.here(ctx.root), dry=False, bundles=staged[0].parent)


def upload_files(ctx: Context) -> tuple[list[Path], list[Path]]:
    """The components and `libera` itself, as files here, or a refusal that
    names what is missing before anything is staged."""
    app = versions.app_version(ctx.root)
    payload = versions.payload_version(ctx.root)
    pypi = components.folder(ctx)
    dist = ctx.root / "dist"
    names = [core_wheel_name(payload, TAGS[b.platform]) for b in ctx.builders]
    names += [core_sdist_name(payload), web_wheel_name(payload)]
    own = [dist / f"libera-{app}-py3-none-any.whl", dist / f"libera-{app}.tar.gz"]
    present = {p.name for p in pypi.glob("*")} | {p.name for p in dist.glob("*")}
    found = plan.upload_problems(
        present,
        wanted=[*names, *(p.name for p in own)],
        payload_version=payload,
        requires=requires_of(own[0]),
    )
    problems(found, "nothing was staged.")
    return [pypi / name for name in names], own


def requires_of(wheel: Path) -> list[str]:
    """The Requires-Dist lines of a wheel's METADATA, without their markers."""
    if not zipfile.is_zipfile(wheel):
        return []
    with zipfile.ZipFile(wheel) as package:
        metadata = next(
            n for n in package.namelist() if n.endswith(".dist-info/METADATA")
        )
        text = package.read(metadata).decode("utf-8")
    return [
        line.split(":", 1)[1].split(";", 1)[0].strip()
        for line in text.splitlines()
        if line.startswith("Requires-Dist:")
    ]


def confirm(app: str) -> None:
    say("    PyPI accepts a version once. There is no undo, and a yank")
    say("    does not free the number.")
    report.confirm(f"publish {app} to PyPI?", "nothing was published.")


def verify(ctx: Context) -> None:
    """What PyPI serves, installed as a user installs it, on every platform."""
    installed(ctx)


def installed(ctx: Context) -> None:
    """`libera` from PyPI alone, on every platform, as a user gets it: a
    clean environment, nothing from this tree or a builder's, the version
    asked for by name, then a document converted and its text read back.

    The check 0.7.0b1 needed: everything else read what it had built, and
    every one of its installs failed, PyPI having no libera-core. PyPI's
    index can lag an upload by minutes, so each platform tries for a while.
    """
    app = versions.app_version(ctx.root)
    step(f"libera {app} installed from PyPI, on each platform")
    script = install_script(app)
    found = []
    for b in ctx.builders:
        host = ctx.host_for(b) if b.remote else LocalHost(Path.home())
        out = host.capture(script)
        facts = facts_from(out)
        if facts.get("INSTALLED") == app and facts.get("CONVERTED") == "1":
            version = facts.get("VERSION", "?")
            say(f"    {b.platform:<14} {version}, a document converted")
        else:
            tail = "\n".join(f"       | {line}" for line in out.splitlines()[-12:])
            found.append(
                f"{b.platform}: libera {app} did not install and convert\n{tail}"
            )
    problems(found, "a published release a user cannot install.")


# A window on this machine, from the staged install: its page photographs its
# own canvas (`--shot`), which needs no screen-recording permission, under a
# home of its own, so it cannot hand the document to a Libera Suite already
# running here. Then the size of what it posted, settled, or nothing.
WINDOW = """
mkdir -p home shots
HOME="$T/home" "$bin/libera" -v --shot "$T/shots/window.png" note.docx \\
    > window.log 2>&1 &
app=$!
last=0
for i in $(seq 120); do
    sleep 1
    f=$(ls shots/window*.png 2>/dev/null | head -1)
    size=$([ -n "$f" ] && wc -c < "$f" | tr -d ' ' || echo 0)
    [ "$size" -gt 0 ] && [ "$size" = "$last" ] && break
    last=$size
done
kill $app 2>/dev/null; wait $app 2>/dev/null
echo "WINDOW=${size:-0}"
"""


def install_script(
    app: str, *, staged: str = "", deps: Sequence[str] = (), window: bool = False
) -> str:
    """bash, the same on every builder, that installs `app` into a new
    environment and converts a line of text to a .docx.

    From PyPI alone, or, given `staged` (a directory under $HOME there),
    libera and its components from that directory and nothing else: `deps`,
    its other requirements, come from PyPI first, then the three with no
    index at all, so a file that is not staged cannot stand in for one."""
    if staged:
        third_party = " ".join(f'"{d}"' for d in deps)
        install = f"""
dir=$(cd "$HOME/{staged}" && (pwd -W 2>/dev/null || pwd))
uv pip install -q --python v --index-url {PYPI_SIMPLE} {third_party} > pip.log 2>&1 &&
uv pip install -q --python v --no-cache --no-index --find-links "$dir" \\
    "libera=={app}" >> pip.log 2>&1 && installed=1"""
    else:
        install = f"""
for try in $(seq 10); do
    if uv pip install -q --python v --refresh --no-cache \\
        --prerelease allow --index-url {PYPI_SIMPLE} "libera=={app}" > pip.log 2>&1
    then installed=1; break
    fi
    echo "try $try: not installable yet"; sleep 30
done"""
    return f"""
T=$(mktemp -d); cd "$T" || exit
uv venv -q -p 3.12 v || exit
bin=v/bin; [ -d "$bin" ] || bin=v/Scripts
installed=0
{install}
# What uv said is the reason, and the last thing a refusal shows.
[ "$installed" = 1 ] || {{ cat pip.log; echo "INSTALLED=none"; exit; }}
cat > check.py <<'{CHECK_END}'
import importlib.metadata, sys, zipfile
print("INSTALLED=" + importlib.metadata.version("libera"))
text = zipfile.ZipFile(sys.argv[1]).read("word/document.xml")
print("CONVERTED=" + str(int(b"installed as a user installs it" in text)))
{CHECK_END}
printf 'Libera Suite, installed as a user installs it\\n' > note.txt
"$bin/libera" --convert note.txt -t docx -o note.docx -q
"$bin/python" check.py note.docx
echo "VERSION=$("$bin/libera" -V)"
""" + (WINDOW if window else "")
