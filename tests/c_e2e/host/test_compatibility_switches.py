"""A document's compatibility switches (`w:compat`), through an edit and a save.

x2t hands the editor the switches as three words of bits, and the editor kept
only the five it lays out by: a save wrote every other one as off, and the
third word not at all, so Word laid the document out differently once it had
been edited here (sdkjs 0016, after ElixirOffice 0.7.3).
"""

from __future__ import annotations

from support.settings import blank, edited_and_saved

# One switch from each word the editor does not model, and one it does.
KEPT = ("noLeading", "growAutofit", "cachedColBalance", "ulTrailSpace")


def test_switches_the_editor_does_not_model_are_kept(editor_with, tmp_path):
    switches = "".join(f"<w:{name}/>" for name in KEPT)
    document = blank(tmp_path, switches, before="<w:compatSetting")

    settings = edited_and_saved(editor_with, document)

    assert [name for name in KEPT if f"<w:{name}" not in settings] == []
