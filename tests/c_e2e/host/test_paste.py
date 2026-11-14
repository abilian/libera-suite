"""Pasting a picture into the editor.

The editor turns a picture on the clipboard into a data: URL inside HTML
(sdkjs common/clipboard_base.js) and hands that to LocalFileGetImageUrl, as it
does a web address. The host refused both, and the picture was lost. It now
takes the data: URL; a web address stays refused, so nothing is fetched.

The paste here is an event a script dispatched, with HTML on it: a real
clipboard's file is turned into that same HTML by the editor before it
reaches anything this tests.
"""

from __future__ import annotations

import base64
import time
import zipfile

from support.make_sample_docx import solid_png

from libera.host.saving import SaveRequest, save_document
from libera.host.session import SESSIONS

PASTE = """(html) => {
    const data = new DataTransfer();
    data.setData('text/html', html);
    data.setData('text/plain', 'Before after');
    document.dispatchEvent(new ClipboardEvent('paste',
        {clipboardData: data, bubbles: true, cancelable: true}));
}"""

PICTURES = """() => Asc.editor.WordControl.m_oLogicDocument.GetAllDrawingObjects()
    .filter(o => o.GraphicObj && o.GraphicObj.isImage && o.GraphicObj.isImage())
    .length"""

# The paste is done once the picture's object is in the document.
PASTED = 30


def pictures_after_pasting(editor, src: str) -> int:
    editor.page.locator("iframe").first.click(position={"x": 300, "y": 300}, force=True)
    editor.frame.wait_for_function("() => document.hasFocus()")
    html = f'<html><body><p>Before <img src="{src}" width="40" height="40"> after</p></body></html>'
    editor.frame.evaluate(PASTE, html)
    deadline = time.monotonic() + PASTED
    while time.monotonic() < deadline:
        if found := editor.frame.evaluate(PICTURES):
            return found
        time.sleep(0.5)
    return 0


def test_a_picture_pasted_from_the_clipboard_is_inserted(editor_with):
    editor = editor_with([])
    picture = solid_png(40, 40, (220, 0, 0))
    src = "data:image/png;base64," + base64.b64encode(picture).decode()

    assert pictures_after_pasting(editor, src) == 1
    session = SESSIONS["0"]
    assert (session.media / "pasted.png").read_bytes() == picture

    # Kept by a save, which is x2t merging Editor.bin and the change log the
    # page sends on its own time: wait for the log to hold the paste.
    deadline = time.monotonic() + PASTED
    log = session.change_log.path
    while not (log.exists() and log.stat().st_size) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert save_document(session, SaveRequest())["error"] == 0
    with zipfile.ZipFile(session.document) as saved:
        media = [saved.read(n) for n in saved.namelist() if n.startswith("word/media/")]
    assert picture in media
