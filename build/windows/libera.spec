# PyInstaller spec for Libera Suite on Windows. Run by build/windows-app.sh,
# which sets the environment variables read below.
#
# Two executables over one tree: Libera.exe (windowed) is what users run,
# libera-cli.exe (console) is the same program for a terminal and for the
# installer's payload step. Both come from entry.py.
#
# collect_all for pywebview and its .NET bridge, because neither is found by
# following imports: pywebview picks its platform module at run time, and
# pythonnet/clr_loader load Python.Runtime.dll and their own native helpers by
# path. Missing any of them is a Libera.exe that starts and draws nothing.
# pyinstaller-hooks-contrib covers some of this; saying it here means the build
# does not depend on which version of the hooks happened to be installed.

import os

from PyInstaller.utils.hooks import collect_all, copy_metadata

ICON = os.environ["LIBERA_ICON"]
SRC = os.environ["LIBERA_SRC"]
VERSION_FILE = os.environ["LIBERA_VERSION_FILE"]

datas, binaries, hiddenimports = [], [], []
for package in ("libera", "webview", "pythonnet", "clr_loader"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
# `libera -V` reads its own version with importlib.metadata, which needs the
# dist-info that a frozen tree does not carry unless asked.
datas += copy_metadata("libera") + copy_metadata("pywebview")

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[SRC],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    # The other platforms' toolkits. The host imports them inside
    # `sys.platform` branches, which the analysis cannot see past.
    excludes=["tkinter", "gi", "AppKit", "Foundation", "PyObjCTools", "objc"],
    noarchive=False,
)
pyz = PYZ(a.pure)

windowed = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Libera",
    icon=ICON,
    version=VERSION_FILE,
    console=False,
)
console = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="libera-cli",
    icon=ICON,
    version=VERSION_FILE,
    console=True,
)
COLLECT(windowed, console, a.binaries, a.datas, name="Libera Suite")
