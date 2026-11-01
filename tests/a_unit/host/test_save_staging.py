"""Where a save is converted before it is copied out, and what it answers.

Every save shared one staging file, out/saved.<ext>: an export that wrote
nothing found the previous save's file there and passed, and a save on close
during a Cmd-S wrote the same path.
"""

from __future__ import annotations

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from libera.host import convert, saving, session as sessions
from libera.host.saving import SaveRequest
from libera.host.server import document as server_document
from libera.host.server.api import Refused, Request
from libera.host.session import Session


@pytest.fixture
def note(tmp_path):
    """A session with note.docx open, its Editor.bin in place."""
    host = Session(payload=tmp_path / "payload", work=tmp_path / "state" / "s")
    sessions.configure(host)
    host.doc.mkdir(parents=True, exist_ok=True)
    (host.doc / "Editor.bin").write_bytes(b"DOCY;v10;0;")
    document = tmp_path / "note.docx"
    document.write_bytes(b"the document as it was")
    host.write_current_document(document)
    return host, document


def exporting(content: bytes):
    """An export that writes `content` where it is asked to."""

    def export(_session, staged, _fmt, _like):
        staged.write_bytes(content)

    return export


def test_a_save_leaves_nothing_staged(note, monkeypatch):
    host, document = note
    monkeypatch.setattr(convert, "export", exporting(b"the saved document"))

    result = saving.save_document(host, SaveRequest())

    assert result == {"error": saving.SaveOutcome.SAVED, "path": str(document)}
    assert document.read_bytes() == b"the saved document"
    assert list(host.out_dir.iterdir()) == []


def test_a_failed_save_leaves_the_document_and_nothing_staged(note, monkeypatch):
    host, document = note

    def fails(*_a):
        msg = "x2t could not write saved.docx (exit status 1)"
        raise convert.ConversionError(msg)

    monkeypatch.setattr(convert, "export", fails)

    result = saving.save_document(host, SaveRequest())

    assert result == {"error": saving.SaveOutcome.FAILED}
    assert document.read_bytes() == b"the document as it was"
    assert list(host.out_dir.iterdir()) == []


def test_two_saves_never_share_a_staging_file(note, monkeypatch):
    host, _ = note
    staged: list = []

    def export(_session, path, _fmt, _like):
        staged.append(path)
        path.write_bytes(b"x")

    monkeypatch.setattr(convert, "export", export)

    saving.save_document(host, SaveRequest())
    saving.save_document(host, SaveRequest())

    assert staged[0] != staged[1]


def test_an_export_that_writes_an_empty_file_failed(note, monkeypatch):
    """x2t's exit status has said 0 over nothing before."""
    host, _ = note
    staged = host.work / "out.docx"

    def x2t_writes_nothing(_session, _job):
        staged.touch()
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(convert, "run_x2t", x2t_writes_nothing)

    with pytest.raises(convert.ConversionError):
        convert.export(host, staged, 65, None)


def test_a_save_whose_format_is_not_an_id_is_a_bad_request(note):
    """Read once, at the endpoint: the body used to reach the core as a dict."""
    host, document = note

    with pytest.raises(Refused) as refused:
        server_document.save(Request(host, body=b'{"fileType": "65"}'))

    assert refused.value.status == 400
    assert document.read_bytes() == b"the document as it was"


def test_a_save_that_fails_part_way_leaves_the_document_whole(note, monkeypatch):
    """Copied over in place, a full disk part way through left half a file
    where the good one had been."""
    host, document = note
    monkeypatch.setattr(convert, "export", exporting(b"the saved document"))

    def disk_full(_src, dst):
        dst.write(b"the sa")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(saving.shutil, "copyfileobj", disk_full)

    with pytest.raises(OSError, match="No space left"):
        saving.save_document(host, SaveRequest())

    assert document.read_bytes() == b"the document as it was"
    assert sorted(p.name for p in document.parent.iterdir()) == ["note.docx", "state"]


def test_a_save_through_a_symlink_keeps_the_link(note, monkeypatch, tmp_path):
    host, document = note
    link = tmp_path / "shortcut.docx"
    link.symlink_to(document)
    host.write_current_document(link)
    monkeypatch.setattr(convert, "export", exporting(b"the saved document"))

    saving.save_document(host, SaveRequest())

    assert link.is_symlink()
    assert document.read_bytes() == b"the saved document"


def test_a_save_keeps_the_documents_mode(note, monkeypatch):
    host, document = note
    # 0o666 on Windows, which keeps only a read-only bit.
    document.chmod(0o640)
    before = document.stat().st_mode
    monkeypatch.setattr(convert, "export", exporting(b"the saved document"))

    saving.save_document(host, SaveRequest())

    assert document.stat().st_mode == before


def test_a_new_document_gets_the_mode_a_new_file_gets(tmp_path):
    """Not mkstemp's 0600, which would have made every new document private."""
    staged = tmp_path / "staged.docx"
    staged.write_bytes(b"new")
    umask = os.umask(0)
    os.umask(umask)

    saving.replace_document(staged, tmp_path / "new.docx")

    assert (tmp_path / "new.docx").stat().st_mode & 0o777 == 0o666 & ~umask


XATTR = "/usr/bin/xattr"
FINDER_TAGS = "com.apple.metadata:_kMDItemUserTags"
# Any bytes will do: what is checked is that the attribute is still there.
RED_TAG = b"bplist00 a red tag"


@pytest.mark.skipif(sys.platform != "darwin", reason="Finder tags")
def test_a_save_keeps_the_documents_finder_tags(note, monkeypatch):
    """A rename alone gave the document the new file's attributes: none."""
    host, document = note
    subprocess.run(
        [XATTR, "-wx", FINDER_TAGS, RED_TAG.hex(), str(document)], check=True
    )
    subprocess.run(
        [XATTR, "-w", "eu.liberasuite.test", "kept", str(document)], check=True
    )
    monkeypatch.setattr(convert, "export", exporting(b"the saved document"))

    saving.save_document(host, SaveRequest())

    names = subprocess.run(
        [XATTR, str(document)], capture_output=True, text=True, check=True
    ).stdout.split()
    assert document.read_bytes() == b"the saved document"
    assert FINDER_TAGS in names
    assert "eu.liberasuite.test" in names


@pytest.mark.skipif(sys.platform != "linux", reason="Linux extended attributes")
def test_a_save_keeps_the_documents_extended_attributes(note, monkeypatch):
    host, document = note
    try:
        os.setxattr(document, "user.liberasuite", b"kept")
    except OSError:
        pytest.skip("this file system takes no user attributes")
    monkeypatch.setattr(convert, "export", exporting(b"the saved document"))

    saving.save_document(host, SaveRequest())

    assert os.getxattr(document, "user.liberasuite") == b"kept"
