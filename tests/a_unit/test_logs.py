"""How much the application says, and where it says it."""

from __future__ import annotations

import logging

import pytest

from libera import logs


@pytest.mark.parametrize(
    ("verbosity", "quiet", "expected"),
    [
        (0, False, logging.WARNING),
        (1, False, logging.INFO),
        (2, False, logging.DEBUG),
        (3, False, logging.DEBUG),
        (9, False, logging.DEBUG),
        (0, True, logging.ERROR),
        (3, True, logging.ERROR),
    ],
)
def test_the_count_picks_the_level(verbosity, quiet, expected):
    logs.setup(verbosity, quiet=quiet)
    assert logging.getLogger("libera").level == expected


def test_the_request_trace_needs_three_and_no_quiet():
    """Two lines per asset, thousands during a load. It is its own step."""
    logs.setup(2)
    assert not logs.tracing_requests()

    logs.setup(3)
    assert logs.tracing_requests()

    logs.setup(3, quiet=True)
    assert not logs.tracing_requests()


def test_nothing_is_said_by_default(caplog):
    """The narrative is opt-in. Warnings are not."""
    logs.setup(0)
    libera = logging.getLogger("libera.host.test")
    assert not libera.isEnabledFor(logging.INFO)
    assert libera.isEnabledFor(logging.WARNING)


def test_it_goes_to_stderr_because_stdout_is_output():
    """`libera --serve` prints the editor's URL on stdout, and the harness
    reads it."""
    import sys

    logs.setup(1)
    streams = [
        h.stream for h in logging.getLogger("libera").handlers if hasattr(h, "stream")
    ]
    assert streams
    assert all(s is sys.stderr for s in streams)


def test_setting_up_twice_does_not_double_every_line():
    logs.setup(1)
    logs.setup(2)
    assert len(logging.getLogger("libera").handlers) == 1


def test_the_level_marks_what_matters(caplog):
    record = logging.LogRecord(
        "libera.host.server", logging.WARNING, "f", 1, "open-url refused", None, None
    )
    assert logs.Terse().format(record) == "  ! open-url refused"

    record.levelno = logging.ERROR
    assert logs.Terse().format(record) == "  !! open-url refused"

    record.levelno = logging.INFO
    assert logs.Terse().format(record) == "  open-url refused"

    # Debug says which part is talking, because that is the question then.
    record.levelno = logging.DEBUG
    assert logs.Terse().format(record) == "  [server] open-url refused"
