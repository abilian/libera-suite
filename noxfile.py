"""Nox configuration."""

from __future__ import annotations

import nox

PYTHONS = ["3.12", "3.13", "3.14"]


@nox.session(python=PYTHONS)
def tests(session: nox.Session):
    """Run the test suite."""
    uv_sync(session)
    session.run("pytest")
    # Or:
    # session.run("uv", "run", "--active", "make", "test")


@nox.session
def check(session: nox.Session):
    """Run all checks (lint, typecheck, tests)."""
    uv_sync(session)
    session.run("ruff", "check")
    session.run("ruff", "format", "--check")
    session.run("ty", "check", "src")
    # session.run("pyrefly", "check", "src")
    # session.run("mypy", "src")
    # session.run("mypy", "--strict", "src")
    # Or:
    # session.run("uv", "run", "--active", "make", "check")


#
# Utils
#
def uv_sync(session: nox.Session):
    # Not the payload's components (libera-core, libera-web): uv builds them
    # from source, which is the converter compiled, hours; CI has no container
    # engine to do it in. The tiers that need a payload skip, or find one
    # through LIBERA_PAYLOAD or a build tree.
    session.run(
        "uv",
        "sync",
        "-q",
        "--active",
        "--no-install-package",
        "libera-core",
        "--no-install-package",
        "libera-web",
        external=True,
    )
    # session.run(
    #     "uv", "sync", "-q", "--all-groups", "--all-extras", "--active",
    #     external=True,
    # )
