"""The desktop a test acts on as a person would: its windows, and a real mouse.

X on Linux, through xdotool. On Windows the session someone is logged on to, which
`build/windows/gui-test.sh` reaches. `desktop` is whichever this platform has, and
a test that can only run on one asks `why_no_drag`.
"""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from ctypes import wintypes

# Above the middle of the screen by this much is the editor's toolbar: the
# window is 900 tall and centred, measured on 1000 and 1100 tall screens.
TOOLBAR_ABOVE_MIDDLE = 320
# Below the top of what the page draws, in the page's pixels: the same place, in
# a window with a title bar of its own and scaled by the display.
TOOLBAR_BELOW_PAGE_TOP = 130


class X:
    def why_no_drag(self) -> str | None:
        if sys.platform.startswith("linux") and shutil.which("xdotool"):
            return None
        return "a real drag needs X and xdotool, or Windows: `lb linux gui-test`"

    def _xdotool(self, *args: object) -> str:
        return subprocess.run(
            ["xdotool", *map(str, args)], capture_output=True, text=True, check=True
        ).stdout

    def window_names(self) -> list[str]:
        tree = subprocess.run(
            ["xwininfo", "-root", "-tree"], capture_output=True, text=True, check=True
        ).stdout
        return [
            line.split('"')[1] for line in tree.splitlines() if line.count('"') >= 2
        ]

    def page_middle(self, _title: str) -> tuple[int, int]:
        """The windows are centred, so the middle of the screen is in them."""
        width, height = self._xdotool("getdisplaygeometry").split()
        return int(width) // 2, int(height) // 2

    def toolbar(self, title: str) -> tuple[int, int]:
        x, y = self.page_middle(title)
        return x, y - TOOLBAR_ABOVE_MIDDLE

    def move(self, x: int, y: int) -> None:
        self._xdotool("mousemove", x, y)

    def press(self) -> None:
        self._xdotool("mousedown", 1)

    def release(self) -> None:
        self._xdotool("mouseup", 1)


class Windows:
    """In physical pixels throughout, as the application is."""

    WORK_AREA = 0x30
    MOVE, LEFT_DOWN, LEFT_UP, ABSOLUTE = 0x0001, 0x0002, 0x0004, 0x8000

    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32
        self.user32.SetProcessDPIAware()

    def why_no_drag(self) -> str | None:
        """A window opens and paints behind the lock screen, and a real mouse
        never reaches it: all four drags failed that way, on 2026-11-04 and again
        on 2026-11-05, for no fault of the application's.

        LogonUI is what is on the screen then. `query user` says Active all the
        same, and OpenInputDesktop still answers with Default (measured on
        2026-11-05)."""
        running = subprocess.run(
            ["tasklist", "/fi", "imagename eq LogonUI.exe"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        if "LogonUI" in running:
            return "the screen is locked, and a real drag needs a real mouse"
        return None

    def _windows(self) -> dict[str, int]:
        """The visible windows with a title, and their handles."""
        found = {}

        def visit(handle: int, _param: int) -> bool:
            size = self.user32.GetWindowTextLengthW(handle)
            if size and self.user32.IsWindowVisible(handle):
                text = ctypes.create_unicode_buffer(size + 1)
                self.user32.GetWindowTextW(handle, text, size + 1)
                found[text.value] = handle
            return True

        self.user32.EnumWindows(
            ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(visit), 0
        )
        return found

    def _window(self, title: str) -> int:
        (handle, *_) = [h for name, h in self._windows().items() if title in name]
        return handle

    def rect(self, title: str) -> wintypes.RECT:
        """Where the window whose title has this in it is."""
        rect = wintypes.RECT()
        self.user32.GetWindowRect(self._window(title), ctypes.byref(rect))
        return rect

    def work_area(self) -> wintypes.RECT:
        """The main monitor, less its taskbar."""
        area = wintypes.RECT()
        self.user32.SystemParametersInfoW(self.WORK_AREA, 0, ctypes.byref(area), 0)
        return area

    def window_names(self) -> list[str]:
        return list(self._windows())

    def page_middle(self, title: str) -> tuple[int, int]:
        rect = self.rect(title)
        return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2

    def toolbar(self, title: str) -> tuple[int, int]:
        handle = self._window(title)
        rect = self.rect(title)
        page_top = wintypes.POINT(0, 0)
        self.user32.ClientToScreen(handle, ctypes.byref(page_top))
        scale = self.user32.GetDpiForWindow(handle) / 96
        return (
            (rect.left + rect.right) // 2,
            page_top.y + int(TOOLBAR_BELOW_PAGE_TOP * scale),
        )

    def move(self, x: int, y: int) -> None:
        self.user32.mouse_event(
            self.MOVE | self.ABSOLUTE,
            x * 65535 // (self.user32.GetSystemMetrics(0) - 1),
            y * 65535 // (self.user32.GetSystemMetrics(1) - 1),
            0,
            0,
        )

    def press(self) -> None:
        self.user32.mouse_event(self.LEFT_DOWN, 0, 0, 0, 0)

    def release(self) -> None:
        self.user32.mouse_event(self.LEFT_UP, 0, 0, 0, 0)


desktop = Windows() if sys.platform == "win32" else X()
