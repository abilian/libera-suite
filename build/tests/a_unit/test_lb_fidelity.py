"""The fidelity harness: what counts as the same pages, and which files it trusts."""

from __future__ import annotations

import hashlib

import pytest
from libera_build import cli, fidelity


def test_the_same_pages_are_the_same():
    assert fidelity.compare([b"a", b"b"], [b"a", b"b"]) is None


def test_a_page_that_moved_is_named_by_its_number():
    assert fidelity.compare([b"a", b"b", b"c"], [b"a", b"x", b"y"]) == (
        "page 2, 3 differs"
    )


def test_a_page_count_that_changed_is_said_first():
    assert fidelity.compare([b"a"], [b"a", b"b"]) == "1 page, then 2"


def write_manifest(tmp_path, content: bytes, recorded: bytes):
    (tmp_path / "t01.docx").write_bytes(content)
    sha = hashlib.sha256(recorded).hexdigest()
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        f'id,file,notes\nt01,t01.docx,"Polices absentes ; sha256={sha}"\n',
        encoding="utf-8",
    )
    return manifest


def test_a_corpus_file_is_measured_only_if_it_is_the_one_described(tmp_path):
    manifest = write_manifest(tmp_path, b"docx", b"docx")
    assert fidelity.read_manifest(manifest) == [("t01", tmp_path / "t01.docx")]

    manifest = write_manifest(tmp_path, b"docx", b"another")
    with pytest.raises(SystemExit, match="not the file the manifest describes"):
        fidelity.read_manifest(manifest)


def test_a_users_document_is_named_by_its_content(tmp_path):
    report = tmp_path / "Rapport confidentiel.docx"
    report.write_bytes(b"docx")
    ((name, _),) = fidelity.name_documents([report])
    assert name == "doc-" + hashlib.sha256(b"docx").hexdigest()[:12]
    assert "Rapport" not in name


def test_fidelity_passes_its_options_on():
    (call,) = cli.plan(["fidelity", "doc.docx", "--runs", "3"])
    assert call == cli.Call(fidelity.main, (["doc.docx", "--runs", "3"],))


def test_the_score_compares_the_candidates_with_the_references(tmp_path):
    command = fidelity.score_command(tmp_path / "eo", tmp_path / "ref", tmp_path)
    tools = tmp_path / "eo" / "tools" / "fidelity"
    assert command[command.index("--with-requirements") + 1] == str(
        tools / "requirements.txt"
    )
    assert str(tools / "compare.py") in command
    for option, path in (
        ("--ref-dir", tmp_path / "ref"),
        ("--cand-dir", tmp_path / "candidates"),
        ("--corpus", tmp_path / "eo" / "corpus" / "provisional"),
        ("--out", tmp_path / "score"),
    ):
        assert command[command.index(option) + 1] == str(path)


def test_a_missing_reference_is_named_before_anything_runs(tmp_path):
    (tmp_path / "ref").mkdir()
    (tmp_path / "ref" / "t01.pdf").write_bytes(b"%PDF")
    documents = [("t01", tmp_path / "t01.docx"), ("t02", tmp_path / "t02.docx")]
    with pytest.raises(SystemExit, match=r"no reference for t02$"):
        fidelity.score(documents, tmp_path / "ref", tmp_path)
    assert not (tmp_path / "candidates").exists()


def test_only_the_corpus_is_scored(capsys):
    with pytest.raises(SystemExit):
        fidelity.main(["doc.docx", "--ref", "refs"])
    assert "the corpus only" in capsys.readouterr().err
