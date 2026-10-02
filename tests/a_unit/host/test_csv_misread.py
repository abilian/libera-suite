"""Which rows of a CSV x2t reads wrongly, worked out without running it.

x2t's reader drops the text it has read every 500,000 characters, and never
looks at the first character after the cut (payload 0.4 carries the fix, patch
0029 in build/patches/core). find_misread_rows walks the text the way x2t does;
tests/b_integration checks it against x2t itself. Here the block is shrunk to
100 characters: the same walk, in a few hundred characters instead of half a
million.
"""

from __future__ import annotations

import pytest
from support import ScriptedShell

from libera.host import convert, hooks, opening
from libera.host.session import Session

BLOCK = 100
# Ten rows of ten characters: the last newline is character 99, so the first
# boundary past the block is the one after "k".
PREFIX = ("x" * 9 + "\n") * 10


@pytest.fixture
def small_blocks(monkeypatch):
    monkeypatch.setattr(convert, "X2T_CSV_BLOCK", BLOCK)


pytestmark = pytest.mark.usefixtures("small_blocks")


def csv_file(tmp_path, text: str, name: str = "list.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("after_the_cut", "misread"),
    [
        pytest.param('k,"a,b",z\n', [11], id="a quoted cell splits"),
        pytest.param("k,,z\n", [11], id="an empty cell merges"),
        pytest.param('k\n"a,b",z\n', [12], id="a quoted row splits"),
        pytest.param("k\n\nlast\n", [12], id="a blank line merges"),
        pytest.param("k,yes,z\n", [], id="a letter is harmless"),
    ],
)
def test_the_character_after_the_cut_decides(tmp_path, after_the_cut, misread):
    assert convert.find_misread_rows(csv_file(tmp_path, PREFIX + after_the_cut)) == (
        misread
    )


def test_a_small_file_is_never_cut(tmp_path):
    assert convert.find_misread_rows(csv_file(tmp_path, 'a,"b,c"\n' * 5)) == []


def test_a_byte_order_mark_is_not_counted(tmp_path):
    """x2t drops it before it counts; counted, every cut would be one off."""
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbf" + (PREFIX + 'k,"a,b",z\n').encode("utf-8"))

    assert convert.find_misread_rows(path) == [11]


def test_a_quote_inside_a_quoted_cell_does_not_end_it(tmp_path):
    """The cut has to land where x2t's does, so the walk keeps its quoting:
    a delimiter inside quotes is not a boundary, and so not a cut."""
    quoted_comma = '"x,xxxxxx"\n'  # 11 characters, its comma inside the quotes
    # 11 + 80 + 9: the last newline is again character 99.
    text = quoted_comma + ("x" * 9 + "\n") * 8 + "x" * 8 + "\n" + 'k,"a,b",z\n'

    assert convert.find_misread_rows(csv_file(tmp_path, text)) == [11]


@pytest.fixture
def opened_with(tmp_path, monkeypatch):
    """Open a CSV in a session, with x2t stood in for, recording what is said."""
    told: list[tuple[str, str]] = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(tell=lambda heading, detail: told.append((heading, detail))),
    )
    monkeypatch.setattr(convert, "convert_to_editor_bin", lambda *_: True)

    def open_csv(text: str):
        document = csv_file(tmp_path, text)
        session = Session(payload=tmp_path / "payload", work=tmp_path / "s")
        session.work.mkdir(exist_ok=True)
        opening.open_document(session, document)
        return told

    return open_csv


def test_opening_a_csv_x2t_misreads_says_which_rows(opened_with):
    told = opened_with(PREFIX + 'k,"a,b",z\n')

    assert len(told) == 1
    heading, detail = told[0]
    assert "list.csv" in heading
    assert "row 11:" in detail


def test_opening_a_csv_x2t_reads_whole_says_nothing(opened_with):
    assert opened_with(PREFIX + "k,yes,z\n") == []


@pytest.mark.parametrize(
    ("rows", "said"),
    [
        ([3, 9], "rows 3 and 9:"),
        ([1, 2, 3], "rows 1, 2 and 3:"),
        ([1, 2, 3, 4, 5, 6, 7], "rows 1, 2, 3, 4, 5 and 2 more:"),
    ],
)
def test_the_rows_are_named_and_then_counted(opened_with, monkeypatch, rows, said):
    monkeypatch.setattr(convert, "find_misread_rows", lambda _path: rows)

    told = opened_with("a,b\n")

    assert said in told[0][1]
