"""Text files are read and written in the encoding they were written in.

`read_text()` and `write_text()` with no encoding use
`locale.getpreferredencoding(False)`, which is the *machine's*, not the
file's. The host writes `current.txt` from three places and reads it from one,
and two of the writers had no encoding while the rest had utf-8 -- so a
document path with an accent in it round-tripped correctly only where the
locale happened to agree.

Measured in a container under the C locale, which is what a systemd service,
a cron job and an unset-LANG ssh session all have:

    preferred encoding: ANSI_X3.4-1968
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 36

That is `Rapport financier — déjà vu.docx`, which is not an exotic filename
here. And UnicodeDecodeError is a ValueError, so opening.has_unsaved_edits's
handler catches it and reports "no unsaved edits" -- the recovery prompt never
appears and the edits go.

The static check is the one that matters: it computes the answer over the
whole tree rather than asserting a list somebody kept up to date.
"""

from __future__ import annotations

import ast

import pytest
from support import repo_root

from libera.host.session import Session

SRC = repo_root() / "src" / "libera"


def text_io_without_encoding() -> list[str]:
    """Every read_text/write_text call in the host that names no encoding."""
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"read_text", "write_text"}:
                continue
            if not any(kw.arg == "encoding" for kw in node.keywords):
                offenders.append(f"{path.name}:{node.lineno} .{node.func.attr}()")
    return offenders


def test_no_text_io_relies_on_the_machines_locale():
    offenders = text_io_without_encoding()
    assert offenders == [], (
        "these read or write text in whatever encoding the machine prefers:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "name",
    [
        "Rapport financier — déjà vu.docx",
        "Кириллица.docx",
        "日本語.docx",
    ],
)
def test_a_documents_path_survives_being_written_and_read_back(tmp_path, name):
    """The round trip current.txt actually makes, through the code that makes it.

    It was pathlib with the encoding pinned in the test, which passes whatever
    Session does: what has to be pinned is Session's own read and write.
    """
    found = Session(payload=tmp_path / "payload", work=tmp_path / "session")
    found.work.mkdir()
    document = tmp_path / name

    found.write_current_document(document)

    assert found.read_current_document() == document
