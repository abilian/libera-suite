"""Does the same build print the same document the same way twice?

    lb fidelity [DOC...] [--runs N] [--out DIR]

The first stage of measuring fidelity (notes/plans/00-roadmap.md): before a
score against a reference can mean anything, two runs of one build on one
machine have to give the same pixels. Each document goes through the print
path, `libera --convert DOC -t pdf`, which converts it to Editor.bin and
exports that, as Print does; pdftoppm turns each PDF into one PNG per page,
and every run's pages are held to the first run's, byte for byte. The PDFs
themselves are not compared: they carry the time they were written.

Without DOCs: ElixirOffice's provisional corpus, 30 .docx files with a
manifest naming the hard features in each (24 generated for it, CC0; 6 public
documents under the Etalab Licence Ouverte). It is fetched at a pinned commit
into the cache, and each file is checked against the sha256 the manifest
gives. A document is named by its manifest id (`t01`), or, given on the
command line, by `doc-` and the start of its sha256, so that no output names
a user's file.

The pages land in --out (build/out/fidelity by default), run-1/<id>/ and so
on, where they can be looked at. Exit status 1 if any page differs, a page
count differs, or a conversion fails.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from libera_build.repo import REPO

CORPUS_REPO = "https://github.com/leag1234/elixiroffice"
CORPUS_SHA = "764e83489d6991a571de05a88efcbf45fdc5596d"  # 2026-10-21
CORPUS_DIR = "corpus/provisional"
CACHE = Path.home() / ".cache" / "libera-fidelity"
OUT = REPO / "build" / "out" / "fidelity"
# Pages are compared, not looked at closely: 96 dpi shows a moved line and
# keeps a run of the corpus to a few hundred MB.
DPI = 96
# One conversion of one document. x2t has its own limit inside the host.
TIMEOUT = 300
# Fewer than two leaves nothing to compare.
MIN_RUNS = 2
SHA256 = re.compile(r"sha256=([0-9a-f]{64})\s*$")


def fetch_corpus(cache: Path = CACHE) -> list[tuple[str, Path]]:
    """The corpus at its pin, as (id, path), each file checked by its hash."""
    root = cache / f"elixiroffice-{CORPUS_SHA[:12]}"
    manifest = root / CORPUS_DIR / "manifest.csv"
    if not manifest.is_file():
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        for step in (
            ["init", "-q"],
            ["remote", "add", "origin", CORPUS_REPO],
            ["sparse-checkout", "set", CORPUS_DIR],
            ["fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", CORPUS_SHA],
            ["checkout", "-q", "FETCH_HEAD"],
        ):
            subprocess.run(["git", "-C", str(root), *step], check=True)
    return read_manifest(manifest)


def read_manifest(manifest: Path) -> list[tuple[str, Path]]:
    """Each row's id and file. The last sha256 in its notes is the delivered
    file's; one that does not match is refused, not measured."""
    documents = []
    with manifest.open(encoding="utf-8", newline="") as rows:
        for row in csv.DictReader(rows):
            path = manifest.parent / row["file"]
            expected = SHA256.search(row["notes"])
            if expected is None:
                msg = f"{manifest}: {row['id']} gives no sha256"
                raise SystemExit(msg)
            if hash_file(path) != expected.group(1):
                msg = f"{path}: not the file the manifest describes"
                raise SystemExit(msg)
            documents.append((row["id"], path))
    return documents


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def name_documents(paths: list[Path]) -> list[tuple[str, Path]]:
    """A user's documents, named by content: the name never leaves the machine
    in a report."""
    return [(f"doc-{hash_file(p)[:12]}", p.resolve()) for p in paths]


def render(document: Path, into: Path) -> list[Path] | str:
    """The document's pages as PNGs, through the print path; or what failed."""
    shutil.rmtree(into, ignore_errors=True)
    into.mkdir(parents=True)
    pdf = into / "document.pdf"
    converted = subprocess.run(
        [
            sys.executable,
            "-m",
            "libera",
            "-q",
            "--convert",
            str(document),
            "-t",
            "pdf",
            "-o",
            str(pdf),
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )
    if converted.returncode != 0 or not pdf.is_file():
        return f"conversion failed: {converted.stderr.strip() or converted.returncode}"
    subprocess.run(
        ["pdftoppm", "-r", str(DPI), "-png", str(pdf), str(into / "page")],
        check=True,
    )
    pages = sorted(into.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1]))
    return pages or "pdftoppm wrote no page"


def count_pages(n: int) -> str:
    return f"{n} page" if n == 1 else f"{n} pages"


def compare(first: list[bytes], other: list[bytes]) -> str | None:
    """None when two runs gave the same pages, else how they differ."""
    if len(first) != len(other):
        return f"{count_pages(len(first))}, then {len(other)}"
    differ = [
        str(n) for n, (a, b) in enumerate(zip(first, other, strict=True), 1) if a != b
    ]
    return f"page {', '.join(differ)} differs" if differ else None


def measure(documents: list[tuple[str, Path]], runs: int, out: Path) -> int:
    failures = 0
    for name, document in documents:
        started = time.monotonic()
        rendered = [
            render(document, out / f"run-{n}" / name) for n in range(1, runs + 1)
        ]
        took = (time.monotonic() - started) / runs
        failed = next((r for r in rendered if isinstance(r, str)), None)
        if failed is None:
            pages = [
                [p.read_bytes() for p in r] for r in rendered if not isinstance(r, str)
            ]
            failed = next(filter(None, (compare(pages[0], p) for p in pages[1:])), None)
            summary = failed or f"{count_pages(len(pages[0]))}, the same {runs} times"
        else:
            summary = failed
        failures += failed is not None
        print(f"{name:<18} {took:5.1f} s  {summary}")
    print(f"\n{len(documents) - failures} of {len(documents)} the same; pages in {out}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lb fidelity",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("documents", nargs="*", type=Path, metavar="DOC")
    parser.add_argument("--runs", type=int, default=2, help="renderings per document")
    parser.add_argument(
        "--out", type=Path, default=OUT, help=f"where the pages go ({OUT})"
    )
    args = parser.parse_args(argv)
    if args.runs < MIN_RUNS:
        parser.error("--runs: at least 2, or there is nothing to compare")
    if shutil.which("pdftoppm") is None:
        msg = (
            "pdftoppm is not installed:"
            " brew install poppler, or apt install poppler-utils"
        )
        raise SystemExit(msg)
    documents = name_documents(args.documents) if args.documents else fetch_corpus()
    return measure(documents, args.runs, args.out)


if __name__ == "__main__":
    sys.exit(main())
