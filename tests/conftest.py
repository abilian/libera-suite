"""Shared pytest fixtures and configuration.

Test Pyramid Structure:
- tests/a_unit/        - Unit tests (fast, isolated, no I/O)
- tests/b_integration/ - Integration tests (component interactions, file I/O)
- tests/c_e2e/         - End-to-end tests (full app/CLI workflows)

Run specific test types:
    uv run pytest -m unit              # Run only unit tests
    uv run pytest -m integration       # Run only integration tests
    uv run pytest -m e2e               # Run only e2e tests
    uv run pytest tests/a_unit/        # Run by directory
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from support import make_sample_docx

from libera import logs, payload
from libera.host import session


def _built_payload() -> Path | None:
    """The tree build/payload.sh writes, if this checkout has built one.

    Tests need *a* working payload, not the one a user would be given. The
    shipping resolution is deliberately strict -- an installed payload has to
    match PAYLOAD_VERSION exactly -- and that strictness is right for a user
    and pure friction here: bumping the payload version made every box that
    had built one skip the top two tiers until somebody moved a directory,
    regenerated its absolute paths and exported a variable. None of that is a
    test's business, and a CI job should not have to know the sequence.

    So the suite falls back to the build tree, which is where a payload is
    after `make payload-all` and needs no install step. `payload.resolve` is
    untouched.

    The candidates are build/common.sh's, in its order, because a fallback
    that only fires on one platform is worse than none: it works on the box
    you tried it on and skips silently on the other.
    """
    roots = [os.environ["BUILD_ROOT"]] if os.environ.get("BUILD_ROOT") else []
    roots += ["/Volumes/T7-EXT-2T/euro-office-build", Path.home() / "euro-office-build"]
    for root in roots:
        tree = Path(root) / "out" / "payload"
        if payload.looks_complete(tree):
            return tree
    return None


try:
    PAYLOAD = payload.resolve()
except payload.PayloadError:
    built = _built_payload()
    if built is not None:
        # Ahead of any import that resolves it, so the host under test agrees
        # with the fixtures about which payload this is.
        os.environ["LIBERA_PAYLOAD"] = str(built)
    PAYLOAD = payload.resolve() if built is not None else None

NEEDS_PAYLOAD = pytest.mark.skip(
    reason=(
        "needs a payload: `make payload-all` builds one, or "
        "`libera --payload-install` installs one, or set LIBERA_PAYLOAD"
    )
)


def pytest_runtest_teardown(item):
    """A session bound by one test must not still be bound for the next.

    `H` is thread-local and pytest runs every test on one thread, so a leaked
    binding makes code that reads `H` where it must not look fine. That is
    exactly how a live bug hid: the save panel's format popup reads `H` from
    the GUI thread, where nothing is bound and `H` raises, and the suite stayed
    green because an earlier test had left a session behind -- run on its own,
    that file failed eighteen times.

    The rule this keeps: every test file has to pass on its own.
    """
    session.forget()
    # And the logging any test turned up, so the next one is not louder than
    # it asked to be.
    logs.setup(0)


def pytest_collection_modifyitems(config, items):
    """Mark each test by the level it sits at, and skip what cannot run here."""
    for item in items:
        parts = Path(item.fspath).parts
        if "a_unit" in parts:
            item.add_marker(pytest.mark.unit)
            continue
        item.add_marker(
            pytest.mark.integration if "b_integration" in parts else pytest.mark.e2e
        )
        # Everything above a_unit serves files out of a payload and runs x2t
        # from it. Without one there is nothing to test, which is not the same
        # as something that passes.
        if PAYLOAD is None:
            item.add_marker(NEEDS_PAYLOAD)


# -----------------------------------------------------------------------------
# Shared Fixtures
# -----------------------------------------------------------------------------


def make_sample(tmp_path_factory, name: str, *, with_image: bool) -> Path:
    out = tmp_path_factory.mktemp("doc") / name
    make_sample_docx.main(str(out), with_image=with_image)
    return out


@pytest.fixture(scope="session")
def sample_document(tmp_path_factory) -> Path:
    """The harness's own test document: four lines of text, no pictures.

    render.py's thresholds were measured against exactly this, so leave it
    alone -- a picture in it reads as text lines printed on top of each other.

    Session-scoped: it costs a zip rewrite and nothing here edits it on disk;
    the editor works on the copy the host converts.
    """
    return make_sample(tmp_path_factory, "sample.docx", with_image=False)


@pytest.fixture(scope="session")
def illustrated_document(tmp_path_factory) -> Path:
    """The same, with a picture in it.

    Media the host fails to redirect never reaches the network and never
    raises: no request, no console error, just a missing picture. Nothing
    without a picture in it can catch that.
    """
    return make_sample(tmp_path_factory, "illustrated.docx", with_image=True)
