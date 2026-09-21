"""What the application says for itself, and how much of it.

One logger per module -- `logger = logging.getLogger(__name__)` -- and one
place that decides what reaches the terminal.

Named `logger`, not `log`. "The change log" is a thing here, and the first
version of this called the logger `log`: three functions already had a local
of that name holding the change log's path, and each shadowed it silently.

Everything the host does used to print unconditionally, which meant the
interesting line -- an editor error, a refused URL, a conversion that failed
-- arrived in the middle of a paragraph about saving.

    libera FILE          warnings and errors only
    libera -v FILE       what it is doing: opening, saving, windows
    libera -vv FILE      and how: HTTP routes, x2t command lines
    libera -vvv FILE     and every request, as it starts and finishes
    libera -q FILE       errors only

Levels, so a new message lands in the right place:

    error    it failed and the user is affected -- a conversion, a save
    warning  something was refused, or the editor reported a fault
    info     the narrative: opened this, saved that, made a window
    debug    the detail you want when the narrative is not enough

`libera --serve` takes the same flags; the regression harness runs it at the
default and reads the bridge report rather than the log.
"""

from __future__ import annotations

import logging
import sys

# -vvv turns on the per-request trace: two lines for every asset the editor
# fetches, which is thousands during a load and useless until it is not.
# -vvv. Three is the count, not a level.
MOST_VERBOSE = 3

# Mutated rather than rebound, so setup() needs no `global` and nothing can
# hold a stale copy by importing the name.
_STATE = {"trace_requests": False}


def tracing_requests() -> bool:
    """Two lines for every request, which is -vvv and nothing less.

    During a document load that is thousands of lines, and useless until the
    question is "did the server stop answering, or did the editor stop
    asking?" -- which look identical from the outside.
    """
    return _STATE["trace_requests"]


MARKS = {
    logging.WARNING: "! ",
    logging.ERROR: "!! ",
    logging.CRITICAL: "!! ",
}


class Terse(logging.Formatter):
    """Two spaces and the message, which is what this already looked like.

    The host's output is read next to the editor's own, in a terminal someone
    is also using for other things, so it stays quiet and shaped: indented,
    marked when it matters, and told where it came from only in debug, where
    that is the question being asked.
    """

    def format(self, record: logging.LogRecord) -> str:
        mark = MARKS.get(record.levelno, "")
        # The module only in debug, where "which part said this" is the
        # question being asked.
        module = record.name.rpartition(".")[2]
        where = f"[{module}] " if record.levelno <= logging.DEBUG else ""
        text = f"  {mark}{where}{record.getMessage()}"
        if record.exc_info:
            text += "\n" + self.formatException(record.exc_info)
        return text


def setup(verbosity: int = 0, *, quiet: bool = False) -> None:
    """Point the `libera` logger at stderr, at the level asked for.

    stderr, not stdout: `libera --serve` prints the editor's URL on stdout
    and something reads it.
    """
    # -v, -vv, -vvv. Past DEBUG there is no quieter dial, so the third one
    # turns on the request trace instead.
    by_count = {0: logging.WARNING, 1: logging.INFO}
    level = logging.ERROR if quiet else by_count.get(verbosity, logging.DEBUG)
    _STATE["trace_requests"] = not quiet and verbosity >= MOST_VERBOSE

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(Terse())

    log = logging.getLogger("libera")
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(level)
    # Ours alone. Nothing here should reconfigure logging for whatever
    # imported us.
    log.propagate = False
