"""A document double-clicked in Finder while Libera.app runs opens a window.

Finder launches Libera.app only when it is not running. Once it is, the same
double-click is an "open documents" Apple Event sent to the running process,
and nothing answered it: AppKit's fallback said "Libera cannot open files in
the PowerPoint Presentation (.pptx) format" about a file the application opens
at launch. So a Words document open meant no second document from Finder.

These build the event Finder sends, with real descriptors, and hand it to the
handler the application installs. No window is involved: the question is what
reaches the window opener.
"""

from __future__ import annotations

import sys
import threading

import pytest
from support import ScriptedShell

from libera.host import hooks

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Apple Events")

if sys.platform == "darwin":
    from libera.host.window import macos


def finder_event(*paths):
    """The kAEOpenDocuments event, as Finder sends it: a list of file URLs."""
    import Foundation

    event = Foundation.NSAppleEventDescriptor.appleEventWithEventClass_eventID_targetDescriptor_returnID_transactionID_(
        macos._pack_fourcc(b"aevt"), macos._pack_fourcc(b"odoc"), None, -1, 0
    )
    listed = Foundation.NSAppleEventDescriptor.listDescriptor()
    for path in paths:
        url = Foundation.NSURL.fileURLWithPath_(str(path))
        listed.insertDescriptor_atIndex_(
            Foundation.NSAppleEventDescriptor.descriptorWithFileURL_(url), 0
        )
    event.setParamDescriptor_forKeyword_(listed, macos._pack_fourcc(b"----"))
    return event


@pytest.fixture
def opened(monkeypatch):
    """What reaches the window opener, and an event set once it has."""
    seen, done = [], threading.Event()

    def opener(document, _app=None):
        seen.append(document)
        done.set()

    monkeypatch.setattr(hooks, "shell", ScriptedShell(open_window=opener))
    return seen, done


def test_every_document_in_the_event_reaches_the_window_opener(tmp_path, opened):
    seen, done = opened
    words, slides = tmp_path / "notes.docx", tmp_path / "Thematic Roadmap.pptx"

    macos.OPEN_DOCUMENTS.handleOpen_withReply_(finder_event(words, slides), None)

    assert done.wait(5)
    # The opener runs on a thread of its own; give it the second document too.
    for _ in range(50):
        if len(seen) == 2:
            break
        threading.Event().wait(0.02)
    assert [p.resolve() for p in seen] == [words.resolve(), slides.resolve()]


def test_an_event_naming_nothing_opens_nothing(tmp_path, opened):
    """Through the handler, which this used to skip for `_read_documents`, so
    nothing could reach the opener and `seen == []` held whatever happened.

    A second event naming one document follows, so there is something to wait
    for; anything the empty one opened would be in `seen` beside it.
    """
    import Foundation

    seen, done = opened
    empty = Foundation.NSAppleEventDescriptor.appleEventWithEventClass_eventID_targetDescriptor_returnID_transactionID_(
        macos._pack_fourcc(b"aevt"), macos._pack_fourcc(b"odoc"), None, -1, 0
    )
    words = tmp_path / "notes.docx"

    macos.OPEN_DOCUMENTS.handleOpen_withReply_(empty, None)
    macos.OPEN_DOCUMENTS.handleOpen_withReply_(finder_event(words), None)

    assert done.wait(5)
    assert [p.resolve() for p in seen] == [words.resolve()]
