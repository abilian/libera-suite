"""The desktop a test acts on as a person would: its windows, a real mouse, and
another application to drag a file from.

X on Linux, through xdotool, with a window of ours offering the file as Thunar
does. On Windows the session someone is logged on to, which
`build/windows/gui-test.sh` reaches, and File Explorer. `desktop` is whichever this
platform has, and a test that can only run on one asks `why_no_drag`.
"""

from __future__ import annotations

import ctypes
import pathlib
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

# Above the middle of the screen by this much is the editor's toolbar: the
# window is 900 tall and centred, measured on 1000 and 1100 tall screens.
TOOLBAR_ABOVE_MIDDLE = 320
# Below the top of what the page draws, in the page's pixels: the same place, in
# a window with a title bar of its own and scaled by the display.
TOOLBAR_BELOW_PAGE_TOP = 130
# Explorer, kept on top at the left of the screen while a file is dragged from it.
EXPLORER_SIZE = (600, 800)


class X:
    SOURCE = pathlib.Path(__file__).parent / "drag_source.py"
    # The middle of the source window, which is at the top left of the screen.
    GRAB = (75, 75)

    def __init__(self) -> None:
        self.sources: list[subprocess.Popen[bytes]] = []

    def offer(self, file: pathlib.Path) -> tuple[int, int]:
        """Another application showing this file: where to grab it."""
        self.sources.append(
            subprocess.Popen([sys.executable, str(self.SOURCE), str(file)])
        )
        wait_for_window("drag-source")
        return self.GRAB

    def withdraw(self) -> None:
        """Close what `offer` opened."""
        for source in self.sources:
            source.terminate()
            source.wait(timeout=10)
        self.sources.clear()

    def why_no_drag(self) -> str | None:
        if sys.platform.startswith("linux") and shutil.which("xdotool"):
            return None
        return "a real drag needs X and xdotool, or Windows: `lb linux test --gui`"

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
        self.explorers: list[int] = []

    def offer(self, file: pathlib.Path) -> tuple[int, int]:
        """File Explorer showing this file, in front: where to grab it. Its folder
        names the window, so give it a name no other window has."""
        # Exits with 1 when it has done it, having handed over to the shell.
        subprocess.run(["explorer.exe", str(file.parent)], check=False)
        wait_for_window(file.parent.name)
        handle = self._window(file.parent.name)
        self.explorers.append(handle)
        width, height = EXPLORER_SIZE
        topmost = wintypes.HWND(-1)
        self.user32.SetWindowPos(handle, topmost, 0, 0, width, height, 0)
        return self._item(handle, file)

    def _item(self, handle: int, file: pathlib.Path) -> tuple[int, int]:
        """A point on the file's row, from UI Automation. By its name with or
        without the extension, which Explorer hides for a type it knows."""
        import clr

        # In full: pythonnet does not find these by their short names.
        wpf = "{}, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35"
        clr.AddReference(wpf.format("UIAutomationClient"))
        clr.AddReference(wpf.format("UIAutomationTypes"))
        from System import IntPtr
        from System.Windows.Automation import (
            AutomationElement,
            PropertyCondition,
            TreeScope,
        )

        window = AutomationElement.FromHandle(IntPtr(handle))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            for name in (file.name, file.stem):
                found = window.FindFirst(
                    TreeScope.Descendants,
                    PropertyCondition(AutomationElement.NameProperty, name),
                )
                if found is not None:
                    rect = found.Current.BoundingRectangle
                    return int(rect.X) + 20, int(rect.Y + rect.Height / 2)
            time.sleep(0.5)
        msg = f"Explorer does not show {file.name}"
        raise AssertionError(msg)

    def withdraw(self) -> None:
        """Close what `offer` opened."""
        wm_close = 0x0010
        for handle in self.explorers:
            self.user32.PostMessageW(handle, wm_close, 0, 0)
        self.explorers.clear()

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
        return self._beside_explorer(rect), (rect.top + rect.bottom) // 2

    def toolbar(self, title: str) -> tuple[int, int]:
        handle = self._window(title)
        rect = self.rect(title)
        page_top = wintypes.POINT(0, 0)
        self.user32.ClientToScreen(handle, ctypes.byref(page_top))
        scale = self.user32.GetDpiForWindow(handle) / 96
        return (
            self._beside_explorer(rect),
            page_top.y + int(TOOLBAR_BELOW_PAGE_TOP * scale),
        )

    def _beside_explorer(self, rect: wintypes.RECT) -> int:
        """The window's middle, or further right if Explorer covers that."""
        return max((rect.left + rect.right) // 2, EXPLORER_SIZE[0] + 100)

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


def wait_for_window(name: str) -> None:
    deadline = time.monotonic() + 30
    while not any(name in found for found in desktop.window_names()):
        assert time.monotonic() < deadline, (
            f"no window {name}: {desktop.window_names()}"
        )
        time.sleep(0.2)
