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

import atexit
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from support import build_roots, make_sample_docx

from libera import logs, payload
from libera.host import instance, language, session
from libera.host.server import diagnostics
from libera.payload import fonts

# The payload's fonts alone, in this process and in every `libera` it starts:
# with the machine's counted, the same document lays out differently on two
# machines, and the render checks compare pixels. A test of the machine's
# fonts turns them back on for itself.
os.environ.setdefault(fonts.SWITCH, "0")

# No user's configuration either: a ui_language, installed_fonts or
# payload_dir in someone's config.toml changed what the tests saw, machine by
# machine. An empty one of the suite's own, before anything reads one (a
# named file has to exist); the tests of the configuration name their own.
_NO_CONFIG = Path(tempfile.mkdtemp(prefix="libera-tests-")) / "config.toml"
_NO_CONFIG.write_text("", encoding="utf-8")
os.environ["LIBERA_CONFIG"] = str(_NO_CONFIG)
atexit.register(shutil.rmtree, _NO_CONFIG.parent, ignore_errors=True)


def _built_payload() -> Path | None:
    """The tree `make payload` wrote from this checkout, used in place.

    It records no version, so it is trusted as this checkout's own. A
    container build's tree is not one of these: its `bin` links to
    /build/out/core/bin and its generated files name /build, paths that exist
    only inside the container. Its artifacts are, below.

    The candidates are build/engine/common.sh's, in its order
    (`support.build_roots`), because a fallback that fires on one platform
    only works on the box you tried it on and skips silently on the other.
    """
    for root in build_roots():
        tree = root / "out" / "payload"
        if payload.is_complete(tree):
            return tree
    return None


def _built_dists() -> list[Path]:
    """This checkout's build artifacts for the version it wants, native or
    from the container: tarballs and their manifest, which install anywhere."""
    arch = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine(), platform.machine()
    )
    version = payload.PAYLOAD_VERSION
    candidates = [
        dist
        for root in build_roots()
        for dist in (
            root / "out" / "dist" / version,
            root / f"linux-{arch}" / "out" / "dist" / version,
        )
    ]
    return [dist for dist in candidates if (dist / "manifest.json").is_file()]


def _installed_for_the_tests() -> Path | None:
    """The payload this tree wants, installed into the suite's own cache.

    The suite brings what it needs. It used to take any payload installed on
    the machine, whatever its version: a checkout wanting 0.4.1 ran against a
    0.2 left over in the data directory and reported its converter's old bugs
    as failures. Installed by the same code as `libera --payload-install`,
    which also writes this machine's paths, from this checkout's build
    artifacts when there are some and from the origin otherwise, checked
    against the manifest either way, in a directory no user's install
    shares. Installed again when the artifacts were rebuilt under the same
    version. None when there is nothing to install from: the tiers that need
    it then skip, and the header says why.
    """
    cache_home = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    cache = cache_home / "libera-tests" / "payload" / payload.PAYLOAD_VERSION
    record = cache / "payload.json"
    installed = (
        json.loads(record.read_text(encoding="utf-8")).get("built")
        if payload.is_complete(cache) and record.is_file()
        else None
    )
    sources: list[Path | None] = [*_built_dists(), None]  # None: the origin
    for source in sources:
        if source is not None:
            built = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
            if installed and installed == built.get("built"):
                return cache
        elif installed:
            return cache
        print(
            f"installing payload {payload.PAYLOAD_VERSION} for the tests into"
            f" {cache}, from {source or 'the origin'}",
            file=sys.stderr,
        )
        try:
            payload.install(
                source=source, dest=cache, trust_manifest=True, say=lambda *_: None
            )
        except payload.PayloadError as e:
            print(f"  not installed: {str(e).splitlines()[0]}", file=sys.stderr)
            continue
        if payload.is_complete(cache):
            return cache
    return None


try:
    PAYLOAD = payload.resolve()
except payload.PayloadError:
    # The build tree first: it is what this checkout built, so it is the
    # closest thing to the code under test.
    found = _built_payload() or _installed_for_the_tests()
    if found is not None:
        # Ahead of any import that resolves it, so the host under test agrees
        # with the fixtures about which payload this is.
        os.environ["LIBERA_PAYLOAD"] = str(found)
    PAYLOAD = payload.resolve() if found is not None else None


def pytest_report_header() -> list[str]:
    """Name the payload before anything runs.

    The summary line cannot distinguish a tier that skipped from one that
    passed, and this suite has reported "222 passed" in 0.86 seconds on a
    machine where nothing above a_unit ran. Whatever else is true, the run now
    says which payload it found and whether it is the one this tree expects.
    """
    if PAYLOAD is None:
        return [
            "libera payload: NONE -- every tier above a_unit will skip",
            (
                f"  wanted {payload.PAYLOAD_VERSION}, not installed, not built here,"
                " and nothing to install it from: `make payload`, or LIBERA_PAYLOAD=DIR"
            ),
        ]
    found = PAYLOAD.read_record().get("payload_version", "unknown")
    line = f"libera payload: {PAYLOAD.root} (payload {found})"
    if found != payload.PAYLOAD_VERSION:
        line += f" -- this tree wants {payload.PAYLOAD_VERSION}"
    return [line]


NEEDS_PAYLOAD = pytest.mark.skip(
    reason=(
        "needs the payload this tree wants: not installed, not built here, and "
        "nothing to install it from (see the header); `make payload`, or set LIBERA_PAYLOAD"
    )
)

NOT_ASKED_FOR = pytest.mark.skip(
    reason="opens real windows: `make test-gui`, `-m gui`, or name tests/d_gui"
)


def _asked_for_a_window(config) -> bool:
    """Did this run ask for the gui tier, by marker or by name?

    `-m gui` is one way to ask. Naming the directory is the other, and keying
    on the marker alone made `pytest tests/d_gui/` report three skips: the run
    said exactly which tests it wanted and got none of them.
    """
    if "gui" in config.option.markexpr:
        return True
    return any("d_gui" in Path(arg.split("::")[0]).parts for arg in config.args)


# Nowhere: a directory no test and no application ever creates.
NO_INSTANCE = Path(tempfile.gettempdir()) / "libera-tests-no-instance" / "instance.json"


def pytest_runtest_setup(item):
    """Keep every test away from a Libera Suite running on this machine.

    `libera FILE` hands its documents to a running instance before it does
    anything else, and finds one through instance.json in the real state
    directory. Run on a machine where Libera Suite was open, the CLI tests
    handed their temporary documents to it -- measured: they opened as windows
    on the desktop, and the tests failed because nothing reached their stubs.

    A hook rather than an autouse fixture, like the teardown below. Tests of
    the hand-off itself point it back at a directory of their own.

    And in English, whatever this machine's language: our strings are looked
    up in it, and a test that reads "Untitled.docx" failed on a French Mac.
    Tests of another language say which.
    """
    instance.get_path = lambda: NO_INSTANCE
    language._ask_system_language = lambda: language.ENGLISH
    language.get_language.cache_clear()


def pytest_runtest_teardown(item):
    """What one test leaves in module state, the next must not find.

    The registry of sessions above all. A request that names no session gets
    the first one registered, so a session one test left behind became the
    next test's -- with somebody else's payload under it. While sessions were
    bound to the thread, the binding hid that; a test passed on its own and
    failed in a full run.

    And the logging any test turned up, so the next one is not louder than it
    asked to be; the server's counters, which `/__host__/report` reports and
    tests count; and an announcement a test that ran the real `app.run` left
    where every later hand-off would find it.
    """
    session.SESSIONS.clear()
    logs.setup(0)
    diagnostics.reset()
    diagnostics.ASKED.clear()
    diagnostics.NOT_FOUND.clear()
    NO_INSTANCE.unlink(missing_ok=True)


def pytest_collection_modifyitems(config, items):
    """Mark each test by the level it sits at, and skip what cannot run here.

    pytest hands this hook every item collected, build/tests' as well, which
    mark themselves; only the ones under this directory are touched here.
    """
    here = Path(__file__).parent
    asked_for_a_window = _asked_for_a_window(config)
    for item in items:
        if here not in Path(item.fspath).parents:
            continue
        parts = Path(item.fspath).parts
        if "a_unit" in parts:
            item.add_marker(pytest.mark.unit)
            continue
        if "d_gui" in parts:
            item.add_marker(pytest.mark.gui)
            # These open real windows on the machine running them, which takes
            # the focus and types into whatever is in front. So they run when
            # a run says `-m gui` and never as part of the default suite.
            if not asked_for_a_window:
                item.add_marker(NOT_ASKED_FOR)
            if PAYLOAD is None:
                item.add_marker(NEEDS_PAYLOAD)
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
