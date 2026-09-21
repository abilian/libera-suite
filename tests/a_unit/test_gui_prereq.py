"""What to tell someone whose `pip install` worked and whose window will not.

pywebview installs from PyPI and then needs GTK and WebKit from the system.
Its own message -- "You must have either QT or GTK with Python extensions
installed" -- is true and names no packages, which on Linux is the first thing
a new user meets.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from libera import gui


@pytest.mark.parametrize(
    ("os_release", "expected"),
    [
        ("ID=ubuntu\nID_LIKE=debian\n", "debian"),
        ("ID=debian\n", "debian"),
        # A derivative names itself and points at what it is built on.
        ("ID=linuxmint\nID_LIKE=ubuntu\n", "debian"),
        ('ID="fedora"\nVERSION_ID=42\n', "fedora"),
        ('ID=rocky\nID_LIKE="rhel centos fedora"\n', "fedora"),
        ("ID=arch\n", "arch"),
        ('ID=opensuse-tumbleweed\nID_LIKE="opensuse suse"\n', "suse"),
        ("", None),
        ("ID=plan9\n", None),
    ],
)
def test_the_distribution_decides_which_packages_to_name(os_release, expected):
    assert gui.family(os_release) == expected


def test_an_unknown_distribution_is_told_what_to_ask_for():
    """It used to print all four commands, which is worse on the distributions
    it is for.

    NixOS, Gentoo, Alpine and anything built from source land here, and none of
    them has apt, dnf, pacman or zypper. Four commands of which none exists is
    four wrong answers; the component names are something a reader can look up
    in whatever their own package manager is.
    """
    hint = gui.install_hint("ID=nixos\n")

    assert "apt install" not in hint
    assert "dnf install" not in hint
    assert "pacman" not in hint
    assert "PyGObject" in hint
    assert "typelib" in hint
    assert "Flatpak" in hint, "the one route that needs none of it"


def test_a_distribution_we_do_know_is_matched_through_id_like():
    """openSUSE Tumbleweed says ID="opensuse-tumbleweed", which is in no table.

    Read from a real image rather than assumed: its ID_LIKE is "opensuse
    suse", and that is what carries it to the zypper line.
    """
    hint = gui.install_hint('ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"\n')

    assert hint.strip().startswith("sudo zypper install")


def test_a_known_distribution_gets_one_line():
    hint = gui.install_hint("ID=fedora\n")
    assert hint.strip().startswith("sudo dnf install")
    assert "apt install" not in hint


def test_the_packages_are_the_ones_pywebview_asks_for():
    """platforms/gtk.py requires Gtk 3.0 and WebKit2 4.1, falling back to 4.0.

    If this drifts, the advice sends people to install the wrong thing, which
    is worse than no advice.
    """
    for line in gui.PACKAGES.values():
        assert "gtk" in line.lower()
        assert "webkit2" in line.lower().replace("-", "").replace("_", "")


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="the Linux case")
def test_nothing_to_say_where_the_backend_ships_with_pywebview():
    """macOS gets pyobjc as a wheel; there is nothing to install and nothing
    to warn about."""
    assert gui.why_no_window() is None


def test_a_virtualenv_that_cannot_see_the_system_packages_is_told_so(
    monkeypatch, tmp_path
):
    """The failure that sends people round the loop twice.

    Measured in a Debian container with every package in PACKAGES installed:
    `pipx install libera` reports no window and `pipx install
    --system-site-packages libera` reports one. Advice to apt-install what is
    already installed is worse than no advice at all.

    The environment is pinned to a pipx one here because the *answer* depends
    on it -- a checkout is told to edit its own pyvenv.cfg instead, which is
    the test below. Leaving it unpinned meant this asserted on whatever
    virtualenv the suite happened to be running in.
    """
    (tmp_path / "pipx_metadata.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(gui, "gtk_is_available", lambda: False)
    monkeypatch.setattr(
        gui,
        "_system_python_that_can_start_gtk",
        lambda: (
            "/usr/bin/python3",
            f"{sys.version_info.major}.{sys.version_info.minor}",
        ),
    )

    message = gui.why_no_window()

    assert message is not None
    assert "--system-site-packages" in message, "the flag is the whole answer"
    assert "apt install" not in message, "they have the packages; that is the point"


def test_the_same_failure_in_a_checkout_is_told_something_it_can_act_on(
    monkeypatch, tmp_path
):
    """Same diagnosis, different fix, and the wrong one wastes an afternoon."""
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(gui, "gtk_is_available", lambda: False)
    monkeypatch.setattr(
        gui,
        "_system_python_that_can_start_gtk",
        lambda: (
            "/usr/bin/python3",
            f"{sys.version_info.major}.{sys.version_info.minor}",
        ),
    )

    message = gui.why_no_window()

    assert message is not None
    assert "pyvenv.cfg" in message
    assert "pipx uninstall" not in message, "there is nothing installed to remove"


def test_a_virtualenv_on_another_python_is_told_that_instead(monkeypatch, tmp_path):
    """The flag is not the answer when the interpreter is the problem.

    Reported from an arm64 box: `pipx install --system-site-packages libera`
    installed cleanly on Python 3.14 and the application then printed the
    advice to run that exact command. The system has PyGObject, built for the
    distribution's own Python, and no flag reaches a compiled extension across
    versions.
    """
    (tmp_path / "pipx_metadata.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(gui, "gtk_is_available", lambda: False)
    # 3.9 because the package requires 3.12 and up, so it can never be the
    # version the suite is running on and the branch is pinned either way.
    monkeypatch.setattr(
        gui, "_system_python_that_can_start_gtk", lambda: ("/usr/bin/python3", "3.9")
    )

    message = gui.why_no_window()

    assert message is not None
    assert "--python /usr/bin/python3" in message, "the interpreter is the fix"
    assert "3.9" in message, "say which Python has it"
    ours = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert ours in message, "and which one this copy is on"


def test_a_checkout_on_another_python_is_not_told_to_uv_venv(monkeypatch, tmp_path):
    """The advice has to survive the next command in it.

    `uv venv --python X --system-site-packages` followed by `uv sync` was the
    first answer here and it undid itself: uv rebuilds the environment when the
    interpreter it wants differs from the one the venv is on, so the sync threw
    the venv away, restored the project's pinned version, and cleared
    include-system-site-packages. Measured -- the venv came back on 3.12 with
    the flag off. UV_PYTHON is read ahead of .python-version, so nothing gets
    rebuilt and the pyvenv.cfg line stays.
    """
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(gui, "gtk_is_available", lambda: False)
    monkeypatch.setattr(
        gui, "_system_python_that_can_start_gtk", lambda: ("/usr/bin/python3", "3.9")
    )

    message = gui.why_no_window()

    assert message is not None
    assert "UV_PYTHON=/usr/bin/python3" in message
    assert "pyvenv.cfg" in message, "and the flag, which uv does not set for you"
    assert "uv venv" not in message, "that is the advice that undid itself"


def test_the_probe_asks_the_same_question_as_the_check(monkeypatch):
    """Run the probe against this very interpreter and compare the answers.

    The two disagreed once and it produced a confident wrong diagnosis: the
    probe asked whether `gi` imports, the check asked whether the typelibs are
    there too, and a Fedora box with python3-gobject and no gtk3 was told its
    virtualenv was the problem. This is the assertion that would have caught
    it -- on any machine, whichever way the answer comes out.
    """
    done = subprocess.run(
        [sys.executable, "-c", gui.probe_source()],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert (done.returncode == 0) is gui.gtk_is_available(), done.stderr[-400:]


def test_the_probe_reports_the_version_it_ran_on(monkeypatch):
    """Because the caller compares it against ours, and a blank never differs."""
    if not gui.gtk_is_available():
        pytest.skip("the probe only prints a version when it succeeds")
    done = subprocess.run(
        [sys.executable, "-c", gui.probe_source()],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert done.stdout.strip() == f"{sys.version_info.major}.{sys.version_info.minor}"


def test_packages_actually_missing_still_names_them(monkeypatch):
    """The other branch, and the one that was there first.

    It used not to patch _system_python_has_pygobject, and so asked the
    machine running the tests which branch to take -- passing on a Mac and
    failing on any Linux box that has the packages. Both branches are pinned
    now.
    """
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(gui, "gtk_is_available", lambda: False)
    monkeypatch.setattr(gui, "_system_python_that_can_start_gtk", lambda: None)

    message = gui.why_no_window()

    assert message is not None
    assert "pip cannot install" in message
    assert "again" in message, "a message with no next step is half a message"
    # Both halves: the packages, and the reason installing them may not be
    # enough on its own.
    assert "--system-site-packages" in message


# --- which advice, for how this copy was installed ---------------------------
#
# The message used to say "pipx uninstall libera" whatever the environment was.
# A developer running `uv run libera` from a checkout got that, and it failed
# twice for two different reasons: there was nothing to uninstall, and the
# package is not on PyPI yet.


def test_a_checkout_is_told_to_open_its_own_virtualenv(tmp_path):
    """Nothing pipx about a `.venv` -- the one-line fix is its pyvenv.cfg."""
    assert gui.venv_kind(str(tmp_path)) == "venv"


def test_a_pipx_install_is_recognised_by_what_pipx_leaves(tmp_path):
    (tmp_path / "pipx_metadata.json").write_text("{}", encoding="utf-8")
    assert gui.venv_kind(str(tmp_path)) == "pipx"


def test_a_uv_tool_install_is_recognised_by_its_receipt(tmp_path):
    (tmp_path / "uv-receipt.toml").write_text("", encoding="utf-8")
    assert gui.venv_kind(str(tmp_path)) == "uv-tool"


def test_the_advice_names_the_file_to_edit_for_a_checkout(monkeypatch, tmp_path):
    """A path the reader can paste, not a description of one."""
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    advice = gui._how_to_open_the_virtualenv()
    assert f"{tmp_path}/pyvenv.cfg" in advice
    assert "pipx" not in advice, "a checkout has nothing to uninstall"


def test_the_advice_for_uv_tool_sends_you_somewhere_that_works(monkeypatch, tmp_path):
    """`uv tool` has no --system-site-packages, so the answer is another tool."""
    (tmp_path / "uv-receipt.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    advice = gui._how_to_open_the_virtualenv()
    assert "pipx install --system-site-packages libera" in advice
