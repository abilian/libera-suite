"""How a CSV is written, read off the file itself.

x2t will not open a CSV without an encoding and a delimiter, and writes one
with whatever it is given, so both have to come from the file: guessed on the
way in, and the same on the way out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from libera.host.convert import (
    DELIMITERS,
    UTF_8,
    WINDOWS_1252,
    read_csv,
    read_csv_options,
)

if TYPE_CHECKING:
    import pathlib

LATIN = "Nom;Ville\nÉlodie;Besançon\n"


def write(path: pathlib.Path, text: str, encoding: str = "utf-8") -> pathlib.Path:
    path.write_bytes(text.encode(encoding))
    return path


def test_a_utf8_csv_with_commas(tmp_path):
    f = write(tmp_path / "a.csv", "Nom,Ville\nÉlodie,Besançon\n")

    assert read_csv(f)[1:] == (UTF_8, ",")


def test_a_windows_1252_csv_with_semicolons(tmp_path):
    """What a French Excel writes."""
    f = write(tmp_path / "a.csv", LATIN, "cp1252")

    text, encoding, delimiter = read_csv(f)

    assert (encoding, delimiter) == (WINDOWS_1252, ";")
    assert text == LATIN


def test_a_tsv_is_tabs_without_asking(tmp_path):
    f = write(tmp_path / "a.tsv", "one, two\tthree\n")

    assert read_csv(f)[2] == "\t"


def test_one_column_has_no_delimiter_to_find(tmp_path):
    f = write(tmp_path / "a.csv", "Nom\nÉlodie\n")

    assert read_csv(f)[2] == ","


def test_a_save_writes_the_way_the_open_file_was(tmp_path):
    like = write(tmp_path / "a.csv", LATIN, "cp1252")

    assert read_csv_options(tmp_path / "saved.csv", like) == {
        "m_nCsvTxtEncoding": WINDOWS_1252,
        "m_nCsvDelimiter": DELIMITERS[";"],
    }


def test_a_tsv_gets_tabs_whatever_it_came_from(tmp_path):
    """x2t puts the delimiter it is given into a TSV too, commas included."""
    like = write(tmp_path / "a.csv", LATIN, "cp1252")

    assert read_csv_options(tmp_path / "saved.tsv", like)["m_nCsvDelimiter"] == 1
    assert read_csv_options(tmp_path / "saved.tsv", None)["m_nCsvDelimiter"] == 1


def test_a_csv_from_a_tsv_gets_commas(tmp_path):
    like = write(tmp_path / "a.tsv", "a\tb\n")

    assert read_csv_options(tmp_path / "saved.csv", like)["m_nCsvDelimiter"] == 4


def test_anything_else_gets_utf8_and_commas(tmp_path):
    like = tmp_path / "a.xlsx"
    like.write_bytes(b"PK")

    assert read_csv_options(tmp_path / "saved.csv", like) == {
        "m_nCsvTxtEncoding": UTF_8,
        "m_nCsvDelimiter": DELIMITERS[","],
    }
