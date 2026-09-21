"""Failures a user hits from the shell must read as sentences, not tracebacks.

Both cases here came from real use: a glob expanding to several documents, and
a payload download against an origin that does not exist yet.
"""

from __future__ import annotations

import pathlib
import urllib.error

import pytest
from support import repo_root

from libera import cli, payload
from libera.cli import commands
from libera.payload import PayloadError


def run(argv, capsys):
    code = cli.main(argv)
    return code, capsys.readouterr()


class FakePayload:
    """Enough of a payload for cmd_words, which only wants its root."""

    root = pathlib.Path("/nonexistent/payload")


@pytest.fixture
def no_window(monkeypatch):
    """Stop before the GUI loop, and record what it would have opened."""
    opened = {}

    def fake_run(_root, _work, documents, **_kw):
        opened["documents"] = documents

    # main() asks whether a window is possible before it does anything else,
    # and on Linux the honest answer depends on what is installed: without the
    # GTK typelibs it returns a paragraph of advice and returns 1, so all three
    # tests below failed on the "no such file" and "one window per document"
    # assertions with a message about apt. macOS never sees it -- why_no_window
    # returns None there unconditionally -- which is why this was invisible
    # until the suite was first run on Linux.
    monkeypatch.setattr(cli.commands.gui, "why_no_window", lambda: None)
    monkeypatch.setattr(cli.commands, "_payload_or_offer", FakePayload)
    monkeypatch.setattr(cli.commands.app, "run", fake_run)
    return opened


def test_several_documents_each_get_a_window(tmp_path, capsys, no_window):
    """`libera *.docx` is a plausible thing to type, and the answer is one
    window per document."""
    docs = [tmp_path / "a.docx", tmp_path / "b.docx"]
    for d in docs:
        d.write_bytes(b"x")

    code, out = run([*map(str, docs)], capsys)

    assert code == 0
    assert "usage:" not in out.err
    assert no_window["documents"] == [d.resolve() for d in docs]


def test_a_missing_file_is_named(tmp_path, capsys, no_window):
    code, out = run([str(tmp_path / "gone.docx")], capsys)

    assert code == 1
    assert "no such file" in out.err
    assert "documents" not in no_window


def test_unreachable_origin_prints_a_message(monkeypatch, tmp_path, capsys):
    """The public origin does not exist yet, so this is what most people who
    type `libera payload install` today will see."""
    dns = urllib.error.URLError("nodename nor servname provided")

    def boom(*args, **kwargs):
        raise dns

    # A manifest that covers whatever machine this is. Without it the install
    # stops before it ever reaches the network -- "manifest has no core
    # artifact for linux-arm64" on Linux, and on a clean checkout "this build
    # ships no manifest" everywhere, because src/libera/manifest.json is
    # written by dist.sh and is not in git. This test passed only on a machine
    # that happened to have run a macOS dist.
    monkeypatch.setattr(
        payload.installer,
        "bundled_manifest",
        lambda: {
            "payload_version": payload.PAYLOAD_VERSION,
            "artifacts": [
                {
                    "kind": "core",
                    "platform": payload.current_platform(),
                    "name": "core.tar.gz",
                    "sha256": "0" * 64,
                    "size": 1,
                }
            ],
        },
    )
    monkeypatch.setattr(payload.installer.urllib.request, "urlopen", boom)
    monkeypatch.setattr(payload.locate, "data_dir", lambda: tmp_path / "data")

    code, out = run(["--payload-install"], capsys)

    assert code != 0
    assert "Traceback" not in out.err
    assert "nodename" in out.err
    assert "--from DIR" in out.err


def test_the_app_launcher_invokes_a_command_that_exists(capsys, no_window):
    """The .app passes fixed arguments to `python -m libera`, in Objective-C.

    It passed `words` until the subcommands were removed, which made
    double-clicking the icon fail with "no such file: words" -- in a file no
    Python test reads, so nothing noticed.
    """
    import re

    launcher = (repo_root() / "build/macos/launcher.m").read_text()
    marker = 'addObject:@"libera"];'
    block = launcher[launcher.index(marker) + len(marker) :]
    block = block[: block.index("addObjectsFromArray:gDocuments")]
    extra = re.findall(r'addObject:@"([^"]+)"', block)

    assert extra == [], f"the launcher passes {extra}, which the CLI no longer takes"

    # And the shape it does use -- no arguments at all -- opens the start
    # window rather than erroring.
    code, out = run([], capsys)
    assert code == 0
    assert "usage:" not in out.err


def test_a_missing_file_is_reported_even_when_no_window_can_be_opened(
    monkeypatch, capsys
):
    """A typo is answered as a typo, not as an environment problem.

    `libera reprot.docx` on a Linux box whose virtualenv cannot see PyGObject
    used to print a paragraph about GTK and exit, because cmd_open checked
    whether a window was possible before it looked at its arguments. The name
    is the thing the user can fix by retyping, so it is checked first.

    Three e2e tests found this, and only on Linux: why_no_window() returns None
    on macOS unconditionally, so the order never mattered here.
    """
    monkeypatch.setattr(
        cli.commands.gui, "why_no_window", lambda: "Libera Suite needs GTK and WebKit"
    )

    code, out = run(["/nope/missing.docx"], capsys)

    assert code == 1
    assert "no such file: /nope/missing.docx" in out.err
    assert "GTK" not in out.err, "the environment buried the typo"


def test_the_window_is_still_reported_when_the_file_is_fine(
    monkeypatch, tmp_path, capsys
):
    """The other half: a real file, and a machine that cannot show it."""
    document = tmp_path / "real.docx"
    document.write_bytes(b"x")
    monkeypatch.setattr(
        cli.commands.gui, "why_no_window", lambda: "Libera Suite needs GTK and WebKit"
    )

    code, out = run([str(document)], capsys)

    assert code == 1
    assert "GTK" in out.err


# --- refusing to start, where there is no terminal to refuse into ------------


def test_a_launch_with_no_terminal_is_told_in_a_window(monkeypatch, capsys):
    """The Fedora symptom: click the icon, it flashes, nothing happens.

    Everything this application says when it will not start went to stdout and
    stderr. Launched from a desktop file, a Dock icon or a Flatpak there is
    neither, so a first run without a payload exited 1 in silence. The printing
    stays -- a terminal run should not lose it -- and a window is added.
    """
    shown = []
    monkeypatch.setattr(commands.gui, "show_problem", lambda *a: shown.append(a))
    monkeypatch.setattr(commands.sys.stdin, "isatty", lambda: False)

    assert commands._agreed_to_install() is False

    assert shown, "nothing on screen, and nobody reading the terminal"
    heading, _body, command = shown[0]
    assert "payload" in heading
    assert "--payload-install" in command
    assert "--payload-install" in capsys.readouterr().err, "the printing stays too"


def test_a_terminal_run_is_asked_rather_than_shown_a_window(monkeypatch):
    """A window in front of somebody who is already looking at a prompt is rude."""
    shown = []
    monkeypatch.setattr(commands.gui, "show_problem", lambda *a: shown.append(a))
    monkeypatch.setattr(commands.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    assert commands._agreed_to_install() is False
    assert not shown


def test_inside_the_flatpak_the_command_is_the_flatpak_one(monkeypatch):
    """`libera` is not on the host's PATH when the application is a sandbox."""
    monkeypatch.setenv("FLATPAK_ID", "eu.liberasuite.Libera")
    assert (
        commands._install_command()
        == "flatpak run eu.liberasuite.Libera --payload-install"
    )


def test_outside_it_is_just_libera(monkeypatch):
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    assert commands._install_command() == "libera --payload-install"


def test_a_build_that_cannot_fetch_does_not_offer_to(monkeypatch, capsys):
    """The question was being asked and then refused.

    `Download and install it now? [Y/n]` took a yes and answered "this build
    ships no manifest, so downloads cannot be verified" -- which reads as a
    failure rather than as something that was never available. Only a released
    wheel carries the hashes a download is checked against; a checkout has
    none, and that is knowable before anybody is asked anything.
    """
    asked = []
    monkeypatch.setattr(
        commands.payload_mod,
        "resolve",
        lambda: (_ for _ in ()).throw(PayloadError("no editor payload found")),
    )
    monkeypatch.setattr(commands.payload_mod, "can_fetch", lambda: False)
    monkeypatch.setattr(commands, "_agreed_to_install", lambda: asked.append(1))
    # capsys leaves stdin without a tty, which is the launcher case: the
    # message goes into a window as well as onto stderr. Opening one here
    # would block the suite on webview.start().
    monkeypatch.setattr(commands.gui, "show_problem", lambda *_a, **_k: None)

    assert commands._payload_or_offer() is None
    assert asked == [], "it asked a question it could not honour"

    said = capsys.readouterr().err
    assert "cannot fetch one" in said
    assert "LIBERA_PAYLOAD" in said, "the cheapest way out is named"
    assert "--payload-install --from" in said
