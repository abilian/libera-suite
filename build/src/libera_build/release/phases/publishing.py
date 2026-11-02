"""collect, push, check, publish and verify: the origin and PyPI."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from libera_build import versions
from libera_build.artifacts import core_sdist_name, core_wheel_name, web_wheel_name
from libera_build.components import TAGS
from libera_build.hosts import LocalHost, facts_from
from libera_build.origin.verbs import OriginOptions, run
from libera_build.process import run_here
from libera_build.release import plan
from libera_build.release.phases import components
from libera_build.report import RefusedError, problems, say, step

# PyPI's simple index: `uv publish --check-url` reads it to skip a file
# already up, and the install check installs from it and nothing else.
PYPI_SIMPLE = "https://pypi.org/simple/"
CHECK_END = "__LIBERA_CHECK_END__"

if TYPE_CHECKING:
    from libera_build.release.context import Context


def origin(ctx: Context, verb: str, *, wheel: str | None = None) -> None:
    run(OriginOptions(verb, wheel=wheel, root=ctx.root, host_for=ctx.host_for))


def publish(ctx: Context) -> None:
    """PyPI, then the bundles and the install scripts. The one phase with no undo.

    PyPI refuses a version it has already seen, even after a yank, so a
    mistaken publish costs a version number. It asks unless told not to, and it
    asks on /dev/tty: this is sometimes run under tmux with its output
    redirected, and a prompt nobody can see is a hang.
    """
    app = versions.app_version(ctx.root)
    step(f"publishing libera {app}")
    components, own = upload_files(ctx)
    if not ctx.yes:
        confirm(app)
    # The components first: `libera` names them, and a `libera` up without
    # them is what 0.7.0b1 was, a release nothing could install. Files PyPI
    # already holds, byte for byte, are skipped, so a publish that broke part
    # way is run again rather than repaired by hand. The wheel `wheel` built,
    # not a new one: `make publish` built it again first, and a second build
    # of a version already up is a file PyPI refuses.
    for files in (components, own):
        run_here(
            ["uv", "publish", "--check-url", PYPI_SIMPLE, *map(str, files)],
            "publish",
            cwd=ctx.root,
        )
    origin(ctx, "extras")


def upload_files(ctx: Context) -> tuple[list[Path], list[Path]]:
    """The components and `libera` itself, as files here, or a refusal that
    names what is missing before anything is asked or uploaded."""
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
    problems(found, "nothing was published.")
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
    try:
        with Path("/dev/tty").open(encoding="utf-8") as tty:
            say("")
            print(f"    publish {app} to PyPI? [y/N] ", end="", flush=True)
            answer = tty.readline().strip().lower()
    except OSError as e:
        msg = "no terminal to ask on. Re-run with --yes when you mean it."
        raise RefusedError(msg) from e
    if answer not in {"y", "yes"}:
        msg = "nothing was published."
        raise RefusedError(msg)


def verify(ctx: Context) -> None:
    """Read the *published* wheel back and check it against the origin.

    Not the manifest in this tree, which is correct by construction. `libera`
    0.1.0 went up naming a payload that was rebuilt two days later, and every
    check that existed passed, because each read the copy that agreed with it.
    """
    step("the published wheel against the published payload")
    try:
        origin(ctx, "check", wheel="pypi")
    except RefusedError as e:
        msg = (
            "what PyPI serves and what the origin serves do not agree.\n"
            "       This is the check 0.1.0 never had; believe it."
        )
        raise RefusedError(msg) from e
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


def install_script(app: str) -> str:
    """bash, the same on every builder, that installs `app` from PyPI alone
    into a new environment and converts a line of text to a .docx."""
    return f"""
T=$(mktemp -d); cd "$T" || exit
uv venv -q -p 3.12 v || exit
bin=v/bin; [ -d "$bin" ] || bin=v/Scripts
installed=0
for try in $(seq 10); do
    if uv pip install -q --python "$bin/python" --refresh --no-cache \\
        --prerelease allow --index-url {PYPI_SIMPLE} "libera=={app}" > pip.log 2>&1
    then installed=1; break
    fi
    echo "try $try: not installable yet"; sleep 30
done
# What uv said is the reason, and the last thing a refusal shows.
[ "$installed" = 1 ] || {{ cat pip.log; echo "INSTALLED=none"; exit; }}
cat > check.py <<'{CHECK_END}'
import importlib.metadata, sys, zipfile
print("INSTALLED=" + importlib.metadata.version("libera"))
text = zipfile.ZipFile(sys.argv[1]).read("word/document.xml")
print("CONVERTED=" + str(int(b"installed from PyPI" in text)))
{CHECK_END}
printf 'Libera Suite, installed from PyPI\\n' > note.txt
"$bin/libera" --convert note.txt -t docx -o note.docx -q
"$bin/python" check.py note.docx
echo "VERSION=$("$bin/libera" -V)"
"""
