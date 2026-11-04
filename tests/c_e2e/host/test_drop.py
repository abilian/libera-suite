"""Files dropped on the editor, with the drop made in the page.

A browser cannot drag a file from the desktop, so the drop is dispatched in
the page, and the shell stands in for what pywebview's native layer recorded
of the drag. What is tested is everything after that: the page asking the host,
the editor inserting an image through GetDropFiles, a document opening in a
window of its own, and no drop navigating the window away.

What a synthetic drop skips is the dragover before it, where the browser
decides whether a drop happens at all. Over the canvas sdkjs answers "none" for
any file that is not an image (CanDropFiles), so a document dropped there never
became a drop. A browser ignores dropEffect on a DataTransfer a script made, so
the dragover test can only read what the page claims; whether WebKit honours
it is for a real drag to show.

Measured before the change: a drop on the canvas inserted nothing (GetDropFiles
answered []), and a drop on the toolbar was left uncancelled, which in a
webview opens the file in place of the editor.
"""

from __future__ import annotations

import pytest
from support import ScriptedShell
from support.make_sample_docx import solid_png

from libera.host import hooks
from libera.host.session import SESSIONS

DROP = """([selector, name]) => {
  const target = document.querySelector(selector);
  const box = target.getBoundingClientRect();
  const data = new DataTransfer();
  data.items.add(new File(['x'], name));
  const at = {bubbles: true, cancelable: true, dataTransfer: data,
              clientX: box.x + box.width / 2, clientY: box.y + box.height / 2};
  target.dispatchEvent(new DragEvent('dragover', at));
  const drop = new DragEvent('drop', at);
  target.dispatchEvent(drop);
  return drop.defaultPrevented;
}"""


def dropping(monkeypatch, path) -> list:
    """A shell whose drag record holds `path`, and what it was asked to open."""
    opened: list = []
    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            take_dropped=lambda names: [path] if path.name in names else [],
            open_window=lambda document, _app=None: opened.append(document) or True,
        ),
    )
    return opened


def test_an_image_dropped_on_the_page_is_inserted(editor_with, monkeypatch, tmp_path):
    image = tmp_path / "photo.png"
    image.write_bytes(solid_png(40, 30, (200, 30, 30)))
    opened = dropping(monkeypatch, image)
    editor = editor_with([])

    # The page asks for the dropped file by its path, which copies it in.
    with editor.answered("media-import"):
        prevented = editor.frame.evaluate(DROP, ["#id_main_view", "photo.png"])

    assert prevented
    assert opened == []
    media = SESSIONS["0"].media
    assert [p.read_bytes() for p in media.iterdir()] == [image.read_bytes()], (
        "the image never reached the document's media"
    )


def test_a_document_dropped_anywhere_opens_in_a_window(
    editor_with, monkeypatch, tmp_path
):
    report = tmp_path / "report.docx"
    report.write_bytes(b"a document")
    opened = dropping(monkeypatch, report)
    editor = editor_with([])

    # Nothing to wait for: the drop handler asks the host by synchronous XHR,
    # so the window has been asked for by the time the event returns.
    prevented = editor.frame.evaluate(DROP, ["#toolbar", "report.docx"])

    assert prevented, "the webview would open the file in place of the editor"
    assert opened == [report]


def test_a_file_nobody_can_use_is_still_cancelled(editor_with, monkeypatch, tmp_path):
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"PK")
    opened = dropping(monkeypatch, archive)
    editor = editor_with([])

    prevented = editor.frame.evaluate(DROP, ["#toolbar", "archive.zip"])

    assert prevented
    assert opened == []


# As WebKitGTK tells a drag from a file manager: a URI list that reads back
# empty, no files, and a text/html naming the file. tests/d_gui has the real one.
DROP_UNNAMED = """([selector, list]) => {
  const target = document.querySelector(selector);
  const data = new DataTransfer();
  data.setData('text/uri-list', list);
  data.setData('text/html', '<a href="file:///a/report.docx">report</a>');
  const drop = new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: data});
  target.dispatchEvent(drop);
  return [drop.defaultPrevented, data.getData('text/html')];
}"""


def asked_for_names(monkeypatch, found: list) -> tuple[list, list]:
    """What the host was asked for, and what it was asked to open."""
    asked: list = []
    opened: list = []

    def take_dropped(names):
        asked.append(names)
        return found

    monkeypatch.setattr(
        hooks,
        "shell",
        ScriptedShell(
            take_dropped=take_dropped,
            open_window=lambda document, _app=None: opened.append(document) or True,
        ),
    )
    return asked, opened


def test_a_drop_with_no_names_takes_what_the_drag_carried(
    editor_with, monkeypatch, tmp_path
):
    report = tmp_path / "report.docx"
    report.write_bytes(b"a document")
    asked, opened = asked_for_names(monkeypatch, [report])
    editor = editor_with([])

    prevented, html = editor.frame.evaluate(DROP_UNNAMED, ["#toolbar", ""])

    assert prevented, "the webview would open the file in place of the editor"
    assert asked == [None]
    assert opened == [report]
    assert not html, "sdkjs would paste a link to the file into the document"


def test_a_link_is_left_to_the_page(editor_with, monkeypatch):
    asked, _opened = asked_for_names(monkeypatch, [])
    editor = editor_with([])

    prevented, html = editor.frame.evaluate(
        DROP_UNNAMED, ["#toolbar", "https://example.org/"]
    )

    assert prevented, "the webview would go to the link in place of the editor"
    assert asked == []
    assert html, "sdkjs pastes it"


DRAG_OVER = """([selector, name, type]) => {
  const target = document.querySelector(selector);
  const box = target.getBoundingClientRect();
  const data = new DataTransfer();
  data.items.add(new File(['x'], name, {type}));
  target.dispatchEvent(new DragEvent('dragover', {
    bubbles: true, cancelable: true, dataTransfer: data,
    clientX: box.x + box.width / 2, clientY: box.y + box.height / 2}));
  return data.dropEffect;
}"""


def test_a_file_drag_is_accepted_as_it_enters_an_element(editor_with):
    """A move onto a new element fires only dragenter, and WebKit answers that
    position from it: a release after one was no drop at all on GTK."""
    editor = editor_with([])

    assert editor.frame.evaluate(
        """() => {
          const data = new DataTransfer();
          data.items.add(new File(['x'], 'report.docx'));
          const enter = new DragEvent('dragenter',
              {bubbles: true, cancelable: true, dataTransfer: data});
          document.querySelector('#toolbar').dispatchEvent(enter);
          return enter.defaultPrevented;
        }"""
    )


@pytest.mark.parametrize("selector", ["#id_main_view", "#toolbar"])
@pytest.mark.parametrize(
    ("name", "kind"),
    [
        (
            "report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("photo.png", "image/png"),
    ],
)
def test_every_file_drag_is_accepted(editor_with, selector, name, kind):
    """The page claims every file drag before sdkjs can say "none" to it,
    which it does over the canvas for a document: then the drop never
    happens. Read through the pinned property, since a script-made
    DataTransfer keeps its own dropEffect at "none" whatever is set."""
    editor = editor_with([])

    assert editor.frame.evaluate(DRAG_OVER, [selector, name, kind]) == "copy"
