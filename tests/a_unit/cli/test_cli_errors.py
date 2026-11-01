"""Failures a user hits from the shell must read as sentences, not tracebacks.

Both cases here came from real use: a glob expanding to several documents, and
a payload download against an origin that does not exist yet.
"""

from __future__ import annotations

import pathlib

import pytest
from support import repo_root

from libera import cli, launcher
from libera.cli import commands
from libera.host import app
from libera.host.session import NotReadyError
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

    def fake_run(_root, _work, documents, **kw):
        opened["documents"] = documents
        opened["shot"] = kw.get("shot")

    # main() asks whether a window is possible before it does anything else,
    # and on Linux the honest answer depends on what is installed: without the
    # GTK typelibs it returns a paragraph of advice and returns 1, so all three
    # tests below failed on the "no such file" and "one window per document"
    # assertions with a message about apt. macOS never sees it -- explain_why_no_window
    # returns None there unconditionally -- which is why this was invisible
    # until the suite was first run on Linux.
    monkeypatch.setattr(cli.commands.gui, "explain_why_no_window", lambda: None)
    monkeypatch.setattr(cli.commands, "_resolve_payload", FakePayload)
    monkeypatch.setattr(app, "run", fake_run)
    return opened


def test_the_shot_option_arms_a_windowed_run_too(tmp_path, capsys, no_window):
    """`libera --shot FILE DOC` was refused as an option belonging to --serve.

    A window arms it as well, and that is the only way to measure what the
    engine that ships actually drew: Chromium, which --serve and the e2e tier
    use, is not WKWebView, WebKitGTK or WebView2. See tests/d_gui.
    """
    document = tmp_path / "a.docx"
    document.write_bytes(b"x")

    code, out = run([str(document), "--shot", str(tmp_path / "shot.png")], capsys)

    assert code == 0, out.err
    assert no_window["shot"] == tmp_path / "shot.png"


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
    used to print a paragraph about GTK and exit, because open_documents checked
    whether a window was possible before it looked at its arguments. The name
    is the thing the user can fix by retyping, so it is checked first.

    Three e2e tests found this, and only on Linux: explain_why_no_window() returns None
    on macOS unconditionally, so the order never mattered here.
    """
    monkeypatch.setattr(
        cli.commands.gui,
        "explain_why_no_window",
        lambda: "Libera Suite needs GTK and WebKit",
    )
    # Should the order of the checks break, a failure rather than a window.
    monkeypatch.setattr(app, "run", lambda *_a, **_k: pytest.fail("opened a window"))

    code, out = run(["/nope/missing.docx"], capsys)

    assert code == 1
    # As the platform spells the path: backslashes on Windows.
    assert f"no such file: {pathlib.Path('/nope/missing.docx')}" in out.err
    assert "GTK" not in out.err, "the environment buried the typo"


def test_the_window_is_still_reported_when_the_file_is_fine(
    monkeypatch, tmp_path, capsys
):
    """The other half: a real file, and a machine that cannot show it."""
    document = tmp_path / "real.docx"
    document.write_bytes(b"x")
    monkeypatch.setattr(
        cli.commands.gui,
        "explain_why_no_window",
        lambda: "Libera Suite needs GTK and WebKit",
    )
    monkeypatch.setattr(app, "run", lambda *_a, **_k: pytest.fail("opened a window"))

    code, out = run([str(document)], capsys)

    assert code == 1
    assert "GTK" in out.err


# --- refusing to start, where there is no terminal to refuse into ------------


def no_components(monkeypatch):
    def refuse():
        msg = "Libera Suite's components are not installed\n  pip install libera-core"
        raise PayloadError(msg)

    monkeypatch.setattr(commands.payload_mod, "resolve", refuse)


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
    no_components(monkeypatch)

    assert commands._resolve_payload() is None

    assert shown, "nothing on screen, and nobody reading the terminal"
    _heading, body, _command = shown[0]
    assert "pip install libera-core" in body[0]
    assert "pip install libera-core" in capsys.readouterr().err, "the printing stays"


def test_a_windowed_windows_build_has_no_stdin_at_all(monkeypatch, capsys):
    """sys.stdin is None there, and `sys.stdin.isatty()` raised AttributeError:
    the silent exit the window exists to prevent."""
    shown = []
    monkeypatch.setattr(commands.gui, "show_problem", lambda *a: shown.append(a))
    monkeypatch.setattr(commands.sys, "stdin", None)
    no_components(monkeypatch)

    assert commands._resolve_payload() is None
    assert shown, "nothing on screen"


def test_any_refusal_to_start_is_shown_when_there_is_no_terminal(
    monkeypatch, tmp_path, capsys, no_window
):
    """Not only the two messages about the payload: a session that cannot be
    served exited silently from a launcher too."""
    document = tmp_path / "a.docx"
    document.write_bytes(b"x")
    shown = []
    monkeypatch.setattr(commands.gui, "show_problem", lambda *a: shown.append(a))
    monkeypatch.setattr(commands.sys.stdin, "isatty", lambda: False)

    def not_ready(*_a, **_k):
        msg = "missing: AllFonts.js"
        raise NotReadyError(msg)

    monkeypatch.setattr(app, "run", not_ready)

    code, out = run([str(document)], capsys)

    assert code == 1
    assert "missing: AllFonts.js" in out.err
    assert [paragraphs for _, paragraphs, _ in shown] == [["missing: AllFonts.js"]]


@pytest.mark.parametrize(
    ("argv", "said"),
    [
        (["--port", "1234", "--payload-status"], "--port goes with --serve"),
    ],
)
def test_an_option_of_another_command_is_refused(argv, said, capsys, no_window):
    """`libera --from ./dist` opened the start window and offered a download
    from the default origin, ignoring the directory it was given.

    `no_window`, because that is what this does when it is broken: without it,
    the bug coming back opens a real start window and the suite waits on it.
    """
    with pytest.raises(SystemExit) as refused:
        cli.main(argv)

    assert refused.value.code == 2
    assert said in capsys.readouterr().err


def test_payload_status_names_the_root_where_the_scripts_read_it(
    monkeypatch, tmp_path, capsys
):
    """runtime-smoke.py, released-gui.sh and windows-app.sh take the root off
    the `payload:` line; respelled once, the Flatpak checks stopped finding it."""
    monkeypatch.setattr(
        commands.payload_mod,
        "resolve",
        lambda: commands.payload_mod.Payload.found(tmp_path, "LIBERA_PAYLOAD"),
    )

    code, out = run(["--payload-status"], capsys)

    assert code == 0
    read = [
        line.removeprefix("payload:").strip()
        for line in out.out.splitlines()
        if line.startswith("payload:")
    ]
    assert read == [str(tmp_path)]


@pytest.mark.parametrize(("why", "listed"), [(None, True), ("not Linux", False)])
def test_the_launcher_options_are_in_the_help_only_where_they_work(
    monkeypatch, capsys, why, listed
):
    """A Windows or macOS user read about "the Linux launcher" in their help.
    The options stay everywhere, so that they still say why they do nothing."""
    monkeypatch.setattr(launcher, "explain_unsupported", lambda: why)
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    assert ("--launcher-install" in capsys.readouterr().out) is listed


def test_what_earlier_versions_downloaded_is_listed_then_removed(
    monkeypatch, tmp_path, capsys
):
    """0.6 and earlier downloaded a payload per version, 400 MB each, which
    this version never reads: the status says so, and the removal takes them."""
    old = tmp_path / "payload"
    (old / "0.6" / "bin").mkdir(parents=True)
    (old / "0.6" / "bin" / "x2t").write_bytes(b"x" * 2_000_000)
    monkeypatch.setattr(commands.leftovers.locate, "get_data_dir", lambda: old)
    monkeypatch.setattr(
        commands.payload_mod,
        "resolve",
        lambda: commands.payload_mod.Payload.found(tmp_path, "LIBERA_PAYLOAD"),
    )

    _, status = run(["--payload-status"], capsys)
    assert "0.6         2 MB" in status.out
    code, removal = run(["--payload-remove"], capsys)

    assert code == 0
    assert "(2 MB)" in removal.out
    assert not old.exists()
