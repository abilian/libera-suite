"""Can this machine put a window on screen, and what to install if not.

`pip install libera` brings pywebview, and pywebview then needs GTK and
WebKit *from the system*, which pip cannot provide. Without them it raises

    You must have either QT or GTK with Python extensions installed
    in order to use pywebview.

which is true, names no packages, and arrives as a traceback after the install
looked like it worked. On Linux that is the first thing a beta tester will
meet, so it is worth one check and one sentence.

macOS needs nothing: pyobjc comes with pywebview as a wheel.

**There are two ways to fail here and they need different answers.** The
packages can be absent -- and the second is that they are present and
unreachable, because the application is in a virtualenv that cannot see them.
PyGObject is not a wheel: it is `/usr/lib/python3/dist-packages/gi`, installed
by the distribution, and an isolated environment does not have it on sys.path
however thoroughly apt has run. Measured in a Debian container with every
package from PACKAGES installed:

    pipx install libera                          window NOT AVAILABLE
    pipx install --system-site-packages libera   window ok
    uv tool install libera                       window NOT AVAILABLE

`uv tool` has no such flag at all, so on Linux there is no spelling of it that
works. Telling somebody in that position to apt-install what they already have
sends them round the same loop a second time, which is why the message below
asks the system interpreter before deciding what to say.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

# What the GTK backend asks for -- see pywebview's platforms/gtk.py, which
# requires Gtk 3.0 and Gdk 3.0, then WebKit2 4.1 with Soup 3.0, falling back
# to WebKit2 4.0 with Soup 2.4.
PACKAGES = {
    "debian": "sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1",
    "fedora": "sudo dnf install python3-gobject gtk3 webkit2gtk4.1",
    "arch": "sudo pacman -S python-gobject webkit2gtk-4.1",
    "suse": "sudo zypper install python3-gobject typelib-1_0-Gtk-3_0 "
    "typelib-1_0-WebKit2-4_1",
}

# What pywebview's GTK backend requires, in the order it requires it, and the
# WebKit/Soup pairs it will accept. Two checks read these: gtk_is_available in
# this process, and the probe it hands another interpreter. They have to agree
# -- when they did not, a Fedora box with python3-gobject and no typelibs was
# told the packages were installed and its virtualenv was at fault.
NAMESPACES = (("Gtk", "3.0"), ("Gdk", "3.0"))
WEBKIT = (("4.1", "3.0"), ("4.0", "2.4"))

# ID and ID_LIKE in os-release, mapped to the family whose package names apply.
FAMILIES = {
    "debian": "debian",
    "ubuntu": "debian",
    "fedora": "fedora",
    "rhel": "fedora",
    "centos": "fedora",
    "arch": "arch",
    "suse": "suse",
    "opensuse": "suse",
}


def family(os_release: str) -> str | None:
    """Which package manager's names to quote, from /etc/os-release.

    ID first, then ID_LIKE, which is what a derivative sets: Mint says
    `ID=linuxmint` and `ID_LIKE=ubuntu`, and the answer is Debian's either way.
    """
    fields: dict[str, str] = {}
    for line in os_release.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip().strip('"')

    for key in ("ID", "ID_LIKE"):
        for name in fields.get(key, "").split():
            if name in FAMILIES:
                return FAMILIES[name]
    return None


# What to ask for where we have no line to give. NixOS, Gentoo, Alpine, Void
# and anything built from source land here, and on those four commands of which
# none exists, printing them all is four wrong answers rather than one honest
# one. The component names are the ones distributions actually use.
COMPONENTS = """  Libera Suite needs three things your distribution packages:

    PyGObject             python3-gi, python-gobject, pygobject3
    the GTK 3 typelib     gir1.2-gtk-3.0, gtk3
    the WebKitGTK typelib gir1.2-webkit2-4.1, webkit2gtk4.1 (4.1, or 4.0)

  The Flatpak brings all three with it and needs none of this."""


def install_hint(os_release: str) -> str:
    """The line to type, or what to ask for where there is no line."""
    known = family(os_release)
    if known:
        return PACKAGES[known]
    return COMPONENTS


def _system_python_that_can_start_gtk() -> tuple[str, str] | None:
    """The distribution's own interpreter that could open a window, and its version.

    ("/usr/bin/python3", "3.12"), or None where no system interpreter could.
    That is the difference between "not installed" and "installed where this
    process cannot reach it", which is the difference between two pieces of
    advice.

    **It runs the whole check, not just `import gi`.** Asking the easier
    question is how this told a Fedora user with python3-gobject and no
    typelibs that the packages were installed and their virtualenv was at
    fault: `import gi` succeeded there, `gi.require_version("Gtk", "3.0")` did
    not, and the two halves of this module disagreed about what "installed"
    meant. They read the same tables now.

    **The version is the other half of the answer.** PyGObject is a compiled
    extension built for one Python, and on Debian it lives in
    /usr/lib/python3/dist-packages, which only the distribution's own
    interpreter puts on sys.path. A virtualenv built on a different Python
    therefore cannot reach it whatever flags it was made with, and telling
    somebody in that position to add --system-site-packages sends them round
    the same loop again. It has happened: `pipx install --system-site-packages
    libera` on a box whose pipx defaulted to Python 3.14 installed cleanly and
    then printed the advice to do exactly what had just been done.

    A subprocess, and only ever on the path where the application is about to
    refuse to start, so its cost is measured against a traceback.
    """
    probe = probe_source()
    for interpreter in ("/usr/bin/python3", "/usr/bin/python"):
        if not pathlib.Path(interpreter).exists():
            continue
        try:
            done = subprocess.run(
                [interpreter, "-c", probe],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode == 0:
            return interpreter, done.stdout.strip()
    return None


def gtk_is_available() -> bool:
    """Whether pywebview's GTK backend can actually start.

    Asks for what it asks for, in the order it asks: importing `gi` proves
    PyGObject, and require_version proves the typelibs are installed, which is
    the half a pip install cannot bring.
    """
    try:
        # Imported here and not at module scope: it exists only where the
        # system packages are, which is the thing being tested.
        import gi
    except ImportError:
        return False

    try:
        for namespace, version in NAMESPACES:
            gi.require_version(namespace, version)
    except ValueError:
        return False

    for webkit, soup in WEBKIT:
        try:
            gi.require_version("WebKit2", webkit)
            gi.require_version("Soup", soup)
        except ValueError:
            continue
        return True
    return False


def probe_source() -> str:
    """gtk_is_available, written out for another interpreter to run.

    Prints that interpreter's "major.minor" and exits 0 when the backend could
    start there; exits non-zero otherwise. Built from the same two tables as
    the function above, because the whole point of asking is to compare the
    two answers, and a probe that asks an easier question produces a confident
    wrong diagnosis rather than no diagnosis.
    """
    return (
        "import gi, sys\n"
        f"for ns, v in {NAMESPACES!r}:\n"
        "    gi.require_version(ns, v)\n"
        f"for webkit, soup in {WEBKIT!r}:\n"
        "    try:\n"
        "        gi.require_version('WebKit2', webkit)\n"
        "        gi.require_version('Soup', soup)\n"
        "        break\n"
        "    except ValueError:\n"
        "        continue\n"
        "else:\n"
        "    raise SystemExit(1)\n"
        "print('%d.%d' % sys.version_info[:2])\n"
    )


_PROBLEM_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><title>Libera Suite</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; background: #f6f1e9; color: #1e1a17;
         font: 13px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .bar {{ height: 4px; background: #b5462b; }}
  main {{ padding: 26px 30px; }}
  h1 {{ font-size: 16px; margin: 0 0 12px; }}
  p {{ margin: 0 0 12px; max-width: 46em; }}
  code {{ display: block; margin: 16px 0 0; padding: 11px 13px;
          background: #fff; border: 1px solid #e0d8cc; border-radius: 3px;
          font: 12px/1.5 ui-monospace, Menlo, Consolas, monospace;
          user-select: all; overflow-wrap: anywhere; }}
</style></head>
<body><div class="bar"></div><main>
<h1>{heading}</h1>
{body}
{command}
</main></body></html>
"""


def show_problem(heading: str, paragraphs: list[str], command: str = "") -> None:
    """Say why Libera Suite is not starting, on screen rather than on stdout.

    A launch from a Dock icon, a desktop file or a Flatpak has no terminal.
    Everything this application says when it refuses to start went to stdout
    and stderr, so from the launcher it looked like nothing happened at all --
    the icon appeared for a moment and the process exited 1. That was the whole
    of the symptom reported on Fedora, and it is what a first run looks like
    for anyone who has not installed the payload.

    So this is the channel of last resort, and it only makes sense where a
    window is possible: every caller is already past `why_no_window`, because
    a machine that cannot open one cannot be told in a window either.

    It says what is wrong and the line to type. **A button that did the install
    is the better answer and is a separate piece of work** -- it needs
    progress, cancellation and somewhere to put a failure. This is the part
    that stops a silent exit, which is worth having first.
    """
    # Imported here: pywebview pulls in the platform toolkit, and every other
    # path through the CLI has no reason to pay for it.
    import html as html_mod

    import webview

    page = _PROBLEM_PAGE.format(
        heading=html_mod.escape(heading),
        body="\n".join(f"<p>{html_mod.escape(p)}</p>" for p in paragraphs),
        command=f"<code>{html_mod.escape(command)}</code>" if command else "",
    )
    webview.create_window("Libera Suite", html=page, width=560, height=340)
    webview.start()


def venv_kind(prefix: str | None = None) -> str:
    """How this copy was installed: "pipx", "uv-tool" or "venv".

    Which decides the advice, and getting it wrong wastes somebody's afternoon.
    A developer running `uv run libera` from a checkout was told to
    `pipx uninstall libera` and reinstall it -- there was nothing to uninstall,
    and the package is not on PyPI yet either, so the advice failed twice for
    two different reasons before it could have helped.

    Read from what each installer leaves behind rather than guessed from the
    path: pipx writes `pipx_metadata.json` into every venv it makes and uv
    writes `uv-receipt.toml`. Anything else is an ordinary virtualenv, which
    for this project means a checkout.
    """
    root = pathlib.Path(prefix or sys.prefix)
    if (root / "pipx_metadata.json").exists() or "/pipx/venvs/" in str(root):
        return "pipx"
    if (root / "uv-receipt.toml").exists():
        return "uv-tool"
    return "venv"


def _how_to_open_the_virtualenv(interpreter: str | None = None) -> str:
    """The lines to type, for the way this copy was actually installed.

    `interpreter` is the system Python that has PyGObject, and is passed only
    when it is a different version from ours. The virtualenv then has to be
    built on that one; a flag cannot reach across versions.
    """
    on = f" --python {interpreter}" if interpreter else ""
    kind = venv_kind()
    if kind == "pipx":
        return (
            f"  pipx uninstall libera\n  pipx install{on} --system-site-packages libera"
        )
    if kind == "uv-tool":
        return (
            "`uv tool install` has no --system-site-packages, so on Linux there "
            "is no\nspelling of it that works. Install it with pipx instead:\n\n"
            "  uv tool uninstall libera\n"
            f"  pipx install{on} --system-site-packages libera"
        )
    # A plain virtualenv, which for this project means somebody's checkout.
    if interpreter:
        # Not `uv venv --python ... --system-site-packages` followed by a sync,
        # which is what this said first and what sent somebody round the loop:
        # uv rebuilds the environment whenever the interpreter it wants differs
        # from the one the venv is on, so the sync threw that venv away, put
        # the project's pinned version back, and lost both flags on the way.
        #
        # UV_PYTHON is read ahead of .python-version, so setting it stops the
        # environment being rebuilt underneath you -- and the pyvenv.cfg line
        # then survives, because uv only rewrites that file when it makes the
        # virtualenv again.
        return (
            f"  export UV_PYTHON={interpreter}\n"
            "  uv sync\n"
            "  sed -i 's/^include-system-site-packages = false/"
            f"include-system-site-packages = true/' \\\n      {sys.prefix}/pyvenv.cfg"
        )
    # Name the file rather than describe it: this is the one case where the
    # fix is a single line and the user is already in a terminal.
    return (
        f"  sed -i 's/^include-system-site-packages = false/"
        f"include-system-site-packages = true/' \\\n      {sys.prefix}/pyvenv.cfg\n\n"
        "`uv sync` rewrites that file, so a fresh sync needs the line again."
    )


def why_no_window() -> str | None:
    """None when a window can be opened; otherwise what to tell the user.

    Only Linux is checked. macOS ships its backend with pywebview, and
    Windows does not exist yet.
    """
    if not sys.platform.startswith("linux"):
        return None
    if gtk_is_available():
        return None

    system = _system_python_that_can_start_gtk()
    if system:
        interpreter, theirs = system
        ours = f"{sys.version_info.major}.{sys.version_info.minor}"
        if theirs and theirs != ours:
            return (
                "Libera Suite needs GTK and WebKit. This machine has them, for "
                f"Python {theirs} --\nand this copy of Libera Suite is running on "
                f"Python {ours}. PyGObject is a compiled\nextension built for one "
                f"Python, so nothing on {ours} can reach it, whatever flags\nthe "
                "virtualenv was made with.\n\n"
                f"{_how_to_open_the_virtualenv(interpreter)}\n\n"
                "The Flatpak avoids the whole question: it brings its own GTK and "
                "WebKit."
            )
        return (
            "Libera Suite needs GTK and WebKit, which are installed on this "
            "machine -- but\nthis copy of Libera Suite is in a virtualenv that "
            "cannot see them. PyGObject is\nnot a wheel, so an isolated "
            "environment never finds it.\n\n"
            f"{_how_to_open_the_virtualenv()}\n\n"
            "The Flatpak avoids the whole question: it brings its own GTK and "
            "WebKit."
        )

    try:
        os_release = pathlib.Path("/etc/os-release").read_text(encoding="utf-8")
    except OSError:
        os_release = ""

    return (
        "Libera Suite needs GTK and WebKit, which pip cannot install.\n\n"
        f"{install_hint(os_release)}\n\n"
        "Then run the same command again -- and if you installed with pipx, "
        "reinstall\nit as `pipx install --system-site-packages libera`, "
        "because an isolated\nvirtualenv cannot see the packages above."
    )
