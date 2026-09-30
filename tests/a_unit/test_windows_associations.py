"""The Windows installer's file associations come from the editors' own list.

build/windows/associations.py writes them from src/libera/host/apps.py at build
time, so a type an editor opens reaches Explorer's "Open with" with nothing
else to edit. What can go wrong is a type left out, and a command line that
Inno Setup's own quoting mangles -- which is what it did first: an unescaped
quote inside ValueData is "Mismatched or misplaced quotes", at compile time.
"""

from __future__ import annotations

import importlib.util

from support import repo_root

from libera.host import apps


def load():
    path = repo_root() / "build" / "windows" / "associations.py"
    spec = importlib.util.spec_from_file_location("associations", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_type_an_editor_opens_is_offered_to_windows():
    text = "\n".join(load().lines())
    for app in apps.ALL:
        for ext in app.opens:
            assert f'Subkey: "Software\\Classes\\.{ext}\\OpenWithProgids"' in text, ext


def test_the_open_command_survives_inno_setups_quoting():
    """Doubled quotes inside ValueData are one quote in the registry."""
    text = "\n".join(load().lines())
    assert 'ValueData: """{app}\\Libera.exe"" ""%1"""' in text
