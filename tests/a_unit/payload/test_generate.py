"""Generating fonts, the one install step that runs a payload binary.

allfontsgen is stood in for by a shell script, because what is checked is how
its two ways of failing are reported: exiting non-zero, which raised an error
nothing above caught and threw its stderr away, and exiting 0 having found no
fonts, which an editor then shows as a box for every glyph.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from libera.payload import PayloadError, generate

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="a shell script stands in for allfontsgen"
)


def make_payload_with_allfontsgen(tmp_path: Path, script: str) -> Path:
    root = tmp_path / "payload"
    tool = root / "bin" / "tools" / "allfontsgen"
    tool.parent.mkdir(parents=True)
    tool.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    tool.chmod(0o755)
    (root / "fonts-src").mkdir()
    return root


def test_a_failing_allfontsgen_says_what_it_said(tmp_path):
    root = make_payload_with_allfontsgen(
        tmp_path, 'echo "no such directory" >&2; exit 3'
    )

    with pytest.raises(PayloadError, match=r"exit 3.*no such directory"):
        generate.generate(root)


def test_finding_no_fonts_is_a_failure_whatever_it_exits(tmp_path):
    root = make_payload_with_allfontsgen(tmp_path, "exit 0")

    with pytest.raises(PayloadError, match="found no fonts"):
        generate.generate(root)
