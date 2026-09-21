"""Save As is the export path, so its format popup is load-bearing.

Upstream hides "Download As" for an offline desktop application -- FileMenu.js
swaps it for "Save As" -- so this popup is the only way to reach another
format. The panel itself runs out of process and cannot be inspected once it is
up, which is why it is built separately from being shown.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from libera.host import apps, window

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="the native save panel is macOS only"
)


WORDS = apps.WORDS.save_formats
# What the popup deals in. with_format replaces one of these and appends to
# anything else -- it is the dialog's own list, not the session's, because it
# runs on the GUI thread where no session is bound.
KNOWN = [ext for _, ext in WORDS]


def popup_titles(popup):
    return [str(popup.itemTitleAtIndex_(i)) for i in range(popup.numberOfItems())]


def choose(popup, index):
    """Select a format the way a click does.

    Calling the watcher's method directly would pass even if the action were
    never wired to it, which is most of what there is to get wrong here.
    """
    popup.selectItemAtIndex_(index)
    assert popup.sendAction_to_(popup.action(), popup.target()), "action not delivered"


def test_the_panel_offers_every_format_the_host_can_write():
    panel, popup = window.build_save_panel("Report.docx", WORDS)

    assert panel.accessoryView() is not None
    assert popup_titles(popup) == [label for label, _ in WORDS]


def test_it_starts_on_the_format_the_document_already_is():
    _, popup = window.build_save_panel("Report.odt", WORDS)
    assert "OpenDocument" in popup_titles(popup)[popup.indexOfSelectedItem()]


def test_an_unknown_extension_falls_back_to_the_first_format():
    _, popup = window.build_save_panel("Report.pages", WORDS)
    assert popup.indexOfSelectedItem() == 0


def test_choosing_a_format_renames_the_file():
    """The name field has to follow, or the dialog says .docx while the popup
    says PDF and the user has no idea which wins."""
    panel, popup = window.build_save_panel("Report.docx", WORDS)
    assert str(panel.nameFieldStringValue()) == "Report.docx"

    pdf = next(i for i, (label, _) in enumerate(WORDS) if "PDF" in label)
    popup.selectItemAtIndex_(pdf)
    choose(popup, pdf)

    assert str(panel.nameFieldStringValue()) == "Report.pdf"


def test_the_popup_target_survives():
    """setTarget_ does not retain, so an uncollected watcher is the difference
    between the popup working and doing nothing."""
    _, popup = window.build_save_panel("Report.docx", WORDS)
    assert popup.target() is not None


def test_renaming_keeps_a_name_the_user_typed():
    """The format popup changes the format, not the name. Resetting to the
    name the dialog opened with throws away what the user just typed."""
    panel, popup = window.build_save_panel("Dear Onno.docx", WORDS)
    panel.setNameFieldStringValue_("Quarterly report.docx")

    pdf = next(i for i, (label, _) in enumerate(WORDS) if "PDF" in label)
    popup.selectItemAtIndex_(pdf)
    choose(popup, pdf)

    assert str(panel.nameFieldStringValue()) == "Quarterly report.pdf"


def test_a_dotted_name_keeps_all_of_itself():
    """ "Minutes 2026.03.11" has no extension -- ".11" is part of the name."""
    panel, popup = window.build_save_panel("Dear Onno.docx", WORDS)
    panel.setNameFieldStringValue_("Minutes 2026.03.11")

    choose(popup, 0)

    assert str(panel.nameFieldStringValue()) == "Minutes 2026.03.11.docx"


@pytest.mark.parametrize(
    ("typed", "extension", "expected"),
    [
        ("/Documents/Report.docx", "pdf", "/Documents/Report.pdf"),
        ("/Documents/Report", "docx", "/Documents/Report.docx"),
        # not an extension we know: part of the name, not something to replace
        ("/Documents/Minutes 2026.03.11", "docx", "/Documents/Minutes 2026.03.11.docx"),
        ("/Documents/archive.tar", "txt", "/Documents/archive.tar.txt"),
    ],
)
def test_the_chosen_format_decides_the_extension(typed, extension, expected):
    from pathlib import Path

    assert str(window.with_format(Path(typed), extension, KNOWN)) == expected


def test_the_name_can_never_disagree_with_the_format():
    """An ODT file called .docx is the thing this popup exists to prevent, so
    whatever is in the name field, the path that comes back carries the
    chosen format's extension."""
    for index, (_, extension) in enumerate(WORDS):
        panel, popup = window.build_save_panel("Dear Onno.docx", WORDS)
        # the worst case: a contradicting extension typed after the choice
        choose(popup, index)
        panel.setNameFieldStringValue_("mydoc.docx")

        picked = window.with_format(
            Path(str(panel.nameFieldStringValue())),
            KNOWN[popup.indexOfSelectedItem()],
            KNOWN,
        )
        assert picked.suffix == f".{extension}"


def test_the_name_field_follows_every_format():
    panel, popup = window.build_save_panel("Dear Onno.docx", WORDS)
    for index, (_, extension) in enumerate(WORDS):
        choose(popup, index)
        assert str(panel.nameFieldStringValue()) == f"Dear Onno.{extension}"


def test_the_panel_itself_enforces_the_extension():
    """setAllowedFileTypes_ is what makes the path the panel returns already
    carry the chosen extension -- so the overwrite it confirms, and the access
    macOS grants, are for the file we are about to write. Without it the host
    has to rewrite the path afterwards, and both of those are then for a
    different file."""
    panel, popup = window.build_save_panel("mydoc.docx", WORDS)

    for index, (_, extension) in enumerate(WORDS):
        choose(popup, index)
        assert list(panel.allowedFileTypes()) == [extension]


def test_a_typed_extension_cannot_override_the_format():
    panel, _ = window.build_save_panel("mydoc.docx", WORDS)
    assert panel.allowsOtherFileTypes() is False


@pytest.mark.parametrize(
    "app", [a for a in apps.ALL if a.editable], ids=lambda a: a.name
)
def test_the_popup_offers_what_that_editor_can_write(app):
    """Tables has no .docx and Words no .xlsx.

    Viewers are not in this list on purpose: a save panel for one is a
    programming error, refused by save_document before it gets here, and
    guarding for it twice would only hide which check is doing the work.
    """
    _, popup = window.build_save_panel(f"Report.{app.ext}", app.save_formats)
    assert popup_titles(popup) == [label for label, _ in app.save_formats]
