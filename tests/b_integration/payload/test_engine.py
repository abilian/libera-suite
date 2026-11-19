"""The editors' engine, tested in Node rather than in a browser.

`tests/engine/` loads each editor's sdkjs bundle in a plain Node context, the
way x2t loads it, and runs tests against it: ours, and, when this payload's
sdkjs sources are at hand, upstream's own spreadsheet formula suites. This is
the bridge that puts them in `make test`: it names the payload to Node and
reads the result. See notes/experiments/e1-engine-tests-in-node.md.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

from support.documents import SAMPLES
from support.paths import build_roots, repo_root

from libera.host import convert, session as sessions
from libera.host.session import Session
from libera.payload import locate

if TYPE_CHECKING:
    from pathlib import Path


def sdkjs_sources(root: Path) -> Path | None:
    """The sdkjs source tree this payload was built from, when it was built
    here: a build root's `out/payload` beside its `src/sdkjs`. The installed
    components carry no sources, and then upstream's suites skip."""
    for build in build_roots():
        if (build / "out" / "payload").resolve() == root.resolve():
            sources = build / "src" / "sdkjs"
            return sources if (sources / "tests").is_dir() else None
    return None


def editor_bins(payload: Path, work: Path) -> Path:
    """Each of `SAMPLES`, as the payload's x2t converts it for the editor,
    in one folder, `<name>.bin`, for the Node tests to open by name."""
    out = work / "samples"
    out.mkdir()
    for name, (app, build) in SAMPLES.items():
        folder = work / name
        folder.mkdir()
        document = build(folder)
        session = Session(
            payload=payload, work=folder / "session", document=document, app=app
        )
        sessions.configure(session)
        convert.convert_to_editor_bin(session, document)
        shutil.copyfile(session.editor_bin, out / f"{name}.bin")
    return out


def test_the_engine_passes_its_tests_in_node(live_payload, tmp_path):
    node = shutil.which("node")
    assert node, "no node: the engine's tests need Node, as `make lint` does"
    layout = locate.Layout.of(live_payload)
    env = {
        **os.environ,
        # UTC, as upstream's CI: FormulaTests.html compares NOW() with
        # cDate().getExcelDate(), one local and one UTC, and failed in the
        # hour after midnight in Paris.
        "TZ": "UTC",
        "LIBERA_SDKJS": str(layout.sdkjs),
        "LIBERA_WEB_APPS": str(layout.web_apps),
    }
    # A document laid out needs the font index allfontsgen wrote beside the
    # editors, which a build tree has.
    if (layout.root / "AllFonts.js").is_file():
        env["LIBERA_PAYLOAD"] = str(layout.root)
        env["LIBERA_SAMPLES"] = str(editor_bins(live_payload, tmp_path))
    sources = sdkjs_sources(live_payload)
    if sources is not None:
        env["LIBERA_SDKJS_SRC"] = str(sources)
    # The files, not a pattern: node --test expands one itself only from
    # Node 21, and Debian's, in the Linux test image, is 20.
    tests = sorted(
        str(p) for p in (repo_root() / "tests" / "engine").glob("*.test.mjs")
    )
    done = subprocess.run(
        [node, "--test", "--test-reporter=tap", *tests],
        cwd=repo_root(),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    # On the counts, not the exit status alone: a run that finds no test
    # file exits 0 too.
    counts = dict(re.findall(r"^# (tests|pass|fail) (\d+)$", done.stdout, re.MULTILINE))
    assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-2000:]
    assert int(counts.get("tests", 0)) > 0, done.stdout[-2000:]
    assert counts.get("fail") == "0", done.stdout[-4000:]
