"""The command line, run as a user runs it.

No fixtures reaching into the package: these check that `python -m libera`
exits the way the shell expects and says why on stderr.
"""

from __future__ import annotations

from c_e2e.conftest import libera


def test_it_says_what_it_is():
    assert "office suite" in libera("--help").stdout


def test_it_refuses_a_file_that_is_not_there():
    run = libera("/nope/missing.docx")
    assert run.returncode == 1
    assert "no such file: /nope/missing.docx" in run.stderr


def test_it_takes_several_documents(tmp_path):
    """`libera *.docx` is a glob by the time we see it, not one name."""
    run = libera(str(tmp_path / "a.docx"), str(tmp_path / "b.docx"))
    # Both names reached the command; the first missing one is what it reports.
    assert run.returncode == 1
    assert "a.docx" in run.stderr


def test_serve_refuses_a_file_that_is_not_there():
    run = libera("--serve", "/nope/missing.docx")
    assert run.returncode == 1
    assert "no such file" in run.stderr


def test_payload_status_says_where_the_payload_came_from():
    run = libera("--payload-status")
    assert run.returncode == 0
    assert run.stdout.strip()


def test_a_command_is_not_a_filename():
    """There is no `libera words` any more, and it must not look like a file."""
    run = libera("words")
    assert run.returncode == 1
    assert "no such file: words" in run.stderr


def test_serve_takes_exactly_one_document(tmp_path):
    run = libera("--serve")
    assert run.returncode == 2
    assert "exactly one document" in run.stderr
