"""A shell with windows, for tests of what the host does when it has them."""

from __future__ import annotations

from libera.host import hooks


class ScriptedShell(hooks.HeadlessShell):
    """WindowedShell, answering what a test hands it and declining the rest."""

    windowed = True

    def __init__(self, **answers) -> None:
        for name, answer in answers.items():
            setattr(self, name, answer)
