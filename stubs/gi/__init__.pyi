from typing import Any

# PyGObject, which exists on Linux and not on macOS -- so a checker running on
# a Mac reports the import as unresolvable, which is true there and says
# nothing about the code. gui.py imports it inside a try/except precisely
# because it may be absent; that is the runtime check, and this is what a
# checker needs to read the rest of the function.
def require_version(namespace: str, version: str) -> None: ...
def __getattr__(name: str) -> Any: ...
