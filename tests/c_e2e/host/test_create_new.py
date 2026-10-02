"""The editor's File > Create New offers every kind, and makes the one chosen.

It has been wrong twice. It made only the editor's own kind, since that is all
the editor knows to ask for, so there was no way from Words to a spreadsheet.
Then it put up the start window, which offers Open and Recent besides, and
"Create New" means create new. The bridge now draws a chooser over the editor:
a button per kind the host can make.

The server here has no window opener, like `libera --serve`: the editor's own
kind is made in place, and another kind is refused with a message, which these
see as a browser dialog.
"""

from __future__ import annotations

from libera.host import apps

CHOOSER = "#libera-create-new"


def open_chooser(editor) -> None:
    editor.frame.click("#file")
    editor.frame.click("#fm-btn-create")
    editor.page.wait_for_selector(CHOOSER, timeout=10_000)


def test_create_new_offers_every_kind_there_is_to_make(editor_with):
    editor = editor_with([])
    open_chooser(editor)

    buttons = editor.page.eval_on_selector_all(
        f"{CHOOSER} button",
        "bs => bs.map(b => [b.innerText.trim(), b.querySelector('img').naturalWidth])",
    )

    assert [label for label, _ in buttons] == [
        app.noun for app in apps.ALL if app.blank
    ]
    assert all(width > 0 for _, width in buttons), "an icon did not load"
    # Only a choice so far: nothing has been made.
    assert editor.asked_for("new") == 0


def test_escape_leaves_everything_as_it_was(editor_with):
    editor = editor_with([])
    open_chooser(editor)

    editor.page.keyboard.press("Escape")

    assert editor.page.query_selector(CHOOSER) is None
    assert editor.asked_for("new") == 0


def test_the_kind_chosen_is_the_kind_asked_for(editor_with):
    editor = editor_with([])
    asked: list[str] = []
    said: list[str] = []
    editor.page.on(
        "request", lambda r: "/__host__/new" in r.url and asked.append(r.url)
    )
    editor.page.on("dialog", lambda d: (said.append(d.message), d.dismiss()))
    open_chooser(editor)

    editor.page.click(f"{CHOOSER} button[data-doctype=cell]")
    editor.page.wait_for_timeout(1000)

    assert len(asked) == 1
    assert "type=cell" in asked[0]
    # No window to put a spreadsheet in, and the page is a word processor.
    assert said == ["A new spreadsheet needs a window of its own"]
    assert editor.page.query_selector(CHOOSER) is None
