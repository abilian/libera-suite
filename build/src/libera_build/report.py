"""What `lb` says while it works, and how it refuses.

A refusal is `RefusedError`, raised with a sentence that says what is wrong and what
to do about it. `lb` prints it and exits 1; nothing else catches it. The
scripts this replaces called `die()`, which exited from wherever it was, so no
caller, and no test, could see a refusal happen.
"""

from __future__ import annotations

import contextvars
import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

# Where say and step write in this thread, when `held` collects it.
_held: contextvars.ContextVar[io.StringIO | None] = contextvars.ContextVar(
    "held", default=None
)


class RefusedError(Exception):
    """A refusal: what is wrong, said so that the next step is obvious."""


def say(message: str = "") -> None:
    print(message, file=_held.get() or sys.stdout, flush=True)


def step(message: str) -> None:
    say(f"\n==> {message}")


def held(work: Callable[[], T]) -> tuple[T, str]:
    """`work`'s result and what it said, said nowhere yet: for work run
    beside other work, whose lines would otherwise interleave."""
    out = io.StringIO()
    token = _held.set(out)
    try:
        return work(), out.getvalue()
    finally:
        _held.reset(token)


def confirm(question: str, refused: str) -> None:
    """Ask on /dev/tty, and refuse with `refused` unless the answer is yes.

    On the terminal, not stdin: this is sometimes run under tmux with its
    output redirected, and a prompt nobody can see is a hang. With no terminal
    (`lb on`, a pipe), it refuses and says to pass --yes.
    """
    try:
        with Path("/dev/tty").open(encoding="utf-8") as tty:
            say()
            print(f"    {question} [y/N] ", end="", flush=True)
            answer = tty.readline().strip().lower()
    except OSError as e:
        msg = "no terminal to ask on. Re-run with --yes when you mean it."
        raise RefusedError(msg) from e
    if answer not in {"y", "yes"}:
        raise RefusedError(refused)


def problems(found: list[str], verdict: str) -> None:
    """Say every problem, then refuse with the verdict, or do nothing."""
    if not found:
        return
    say()
    for problem in found:
        say(f"    - {problem}")
    raise RefusedError(verdict)
