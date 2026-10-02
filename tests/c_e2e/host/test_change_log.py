"""An edit the change log does not take is said, not dropped in silence.

The bridge sends every edit with a synchronous XHR, and an XHR answers a 500
without throwing. So the editor went on showing an edit that the log never
held and no save would ever write, with nothing said anywhere.
"""

from __future__ import annotations

# The editor batches its edits: typing reaches the host within a few seconds,
# not on the keystroke. Measured at under five.
FLUSH = 15_000


def type_until_sent(editor) -> None:
    """Type, then wait for the editor to hand the edit to the bridge.

    Waits on LocalFileSaveChanges in the page's own call log, which is the
    thing being waited for, and not on the host having received it: in the
    test that refuses the request, the host never does.
    """
    editor.press("x")
    editor.page.keyboard.type("hello")
    for _ in range(FLUSH // 250):
        if "LocalFileSaveChanges" in editor.report()["calls"]:
            return
        editor.page.wait_for_timeout(250)
    msg = "the editor never sent its edits"
    raise AssertionError(msg)


def test_typing_reaches_the_change_log(editor_with):
    """The baseline, and the page's own origin getting past the host's check."""
    editor = editor_with([])

    type_until_sent(editor)

    assert editor.asked_for("changes") > 0, "the edits never reached the host"


def test_an_edit_the_host_refuses_is_reported(editor_with):
    editor = editor_with([])
    editor.page.route("**/__host__/changes*", lambda route: route.fulfill(status=500))

    type_until_sent(editor)
    # The report goes up on the page's one-second tick.
    editor.page.wait_for_timeout(2500)

    errors = [e["text"] for e in editor.report()["errors"]]
    assert any("change log did not take an edit" in text for text in errors), errors
