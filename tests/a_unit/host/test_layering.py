"""Nothing in the host imports anything above it.

`host/__init__.py` has listed the layers since the beginning, and the list was
a description rather than a rule: two edges broke it -- `server` and `window`
both reached up to `menu` -- and the breakage was invisible because it was
done with function-level imports. A `from x import y` inside a function is
what a circular dependency looks like once somebody has worked around it.

So the order is read out of that docstring and checked against the real import
graph, function-level imports included. Adding a layer means adding a line to
the docstring, which is the point: the two cannot drift.
"""

from __future__ import annotations

import ast
import re

from support import repo_root

HOST = repo_root() / "src" / "libera" / "host"


def documented_order() -> list[str]:
    """The layers, innermost first, as host/__init__.py lists them."""
    text = (HOST / "__init__.py").read_text(encoding="utf-8")
    body = text.split('"""')[1]
    names = []
    for line in body.splitlines():
        m = re.match(r"^ {4}(\w+) {2,}\S", line)
        if m:
            names.append(m.group(1))
    return names


def imports_of(module: str) -> set[str]:
    """Every host module this one imports, wherever the import is written."""
    path = HOST / f"{module}.py"
    if not path.is_file():
        path = HOST / module / "__init__.py"
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if not node.module.startswith("libera.host"):
            continue
        parts = node.module.split(".")
        if len(parts) > 2:
            found.add(parts[2])
        else:
            found.update(a.name for a in node.names)
    return found


def test_the_docstring_lists_every_module():
    listed = set(documented_order())
    real = {
        p.stem if p.suffix == ".py" else p.name
        for p in HOST.iterdir()
        if (p.suffix == ".py" and p.stem != "__init__")
        or (p.is_dir() and (p / "__init__.py").is_file())
    }

    assert real - listed == set(), "modules missing from the layer list"
    assert listed - real == set(), "layers listed that do not exist"


def test_nothing_imports_upward():
    order = documented_order()
    rank = {name: i for i, name in enumerate(order)}

    upward = [
        (module, imported)
        for module in order
        for imported in sorted(imports_of(module))
        if imported in rank and rank[imported] > rank[module]
    ]

    assert upward == [], "these import a layer above themselves:\n  " + "\n  ".join(
        f"{a} -> {b}" for a, b in upward
    )
