"""A list whose bullet is a picture, in the editor.

The print path draws the picture from its address (tests/b_integration); the
editor draws it from its image loader, which loads the pictures the document
names, the bullet's among them (ElixirOffice's #66, core 0203 and sdkjs 0011).
"""

from __future__ import annotations

import time

from support import render
from support.pictures import write_pic_bullet_docx

from libera import payload as payload_mod

# The bullets are drawn once their picture has loaded, a moment after the page.
DRAWN = 30


def test_a_picture_bullet_is_drawn_in_the_editor(editor_with, tmp_path):
    document = tmp_path / "bullets.docx"
    write_pic_bullet_docx(payload_mod.resolve().root, document)
    editor = editor_with([], document=document)
    shot = tmp_path / "page.png"

    deadline = time.monotonic() + DRAWN
    red = 0
    while time.monotonic() < deadline:
        editor.frame.locator("#id_main_view").screenshot(path=str(shot))
        red = render.red_pixels(str(shot))
        if red > 100:
            break
        time.sleep(1)

    assert red > 100, "no red bullet was drawn"


# A level written to the change log and read back, by the editor's own code.
# Before picture bullets a level ended with IsLgl, a byte of 0 or 1; a level
# without one still does, so the Long after it here stands for whatever
# followed the level in a change log written then, and must be read next.
ROUND_TRIP = """() => {
    const out = [];
    for (const [isLgl, picBulletId] of [[true, undefined], [false, 3], [true, 7]]) {
        const lvl = new AscWord.CNumberingLvl();
        lvl.IsLgl = isLgl;
        lvl.PicBulletId = picBulletId;
        const memory = new AscCommon.CMemory(true);
        lvl.WriteToBinary(memory);
        const last = memory.data[memory.GetCurPosition() - 1];
        memory.WriteLong(424242);
        const stream = new AscCommon.FT_Stream2(memory.data, memory.GetCurPosition());
        const read = new AscWord.CNumberingLvl();
        read.ReadFromBinary(stream);
        out.push([read.IsLgl, read.PicBulletId === undefined ? null : read.PicBulletId,
                  stream.GetLong(), last]);
    }
    return out;
}"""


def test_a_level_reads_back_from_the_change_log_as_it_was_written(editor_with):
    """sdkjs 0011 puts a level's picture bullet id after IsLgl only when there
    is one, and says so in IsLgl's byte; ElixirOffice appended an id to every
    level, which a change log written before could not be read past."""
    editor = editor_with([])

    # The last byte a level writes: IsLgl's, 1, when it has no picture, as
    # before; the id's last byte, 0, when it has one.
    assert editor.frame.evaluate(ROUND_TRIP) == [
        [True, None, 424242, 1],
        [False, 3, 424242, 0],
        [True, 7, 424242, 0],
    ]
