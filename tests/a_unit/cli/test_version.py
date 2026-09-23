"""`libera --version` names both versions, and exits.

It did not exist at all until somebody typed it on a Linux builder and got a
usage error, which is a poor first impression from a command whose whole job is
to be installed by strangers.
"""

from __future__ import annotations

import pytest

from libera import cli
from libera.cli import dispatch
from libera.payload import locate


def test_version_names_the_application_and_the_payload():
    """Both, because they move independently.

    A host fix should not force a 170 MB re-download, and a payload rebuilt
    from new upstream pins should not need a host release -- so a bug report
    naming only one of them does not say which halves were in play.
    """
    text = dispatch.version_string()
    assert text.startswith("libera ")
    assert f"payload {locate.PAYLOAD_VERSION}" in text


@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version_prints_and_exits_cleanly(flag, capsys):
    """argparse's version action raises SystemExit(0); it must stay a 0.

    A non-zero exit from --version breaks the `libera --version || echo old`
    shape that install scripts use.
    """
    with pytest.raises(SystemExit) as exit_info:
        cli.main([flag])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == dispatch.version_string()


def test_the_two_v_flags_stay_distinct(capsys):
    """-V is the version and -v is still verbosity.

    -v is documented as `-v what it is doing, -vv how, -vvv every request`. A
    flag that silently changed meaning is worse than one that never existed,
    and argparse would have accepted `-v` for version without complaint.
    """
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    help_text = capsys.readouterr().out
    assert "-V, --version" in help_text
    assert "-v, --verbose" in help_text
