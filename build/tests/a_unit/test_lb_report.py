"""What several machines say at once is said one machine at a time."""

from __future__ import annotations

import concurrent.futures
import threading

from libera_build.report import held, say, step


def test_held_keeps_each_threads_lines_apart(capsys):
    both = threading.Barrier(2)

    def machine(name: str) -> str:
        step(name)
        both.wait()  # each has said a line before the other says its next
        say(f"    {name} done")
        return name

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda n: held(lambda: machine(n)), ["a", "b"]))

    assert results == [("a", "\n==> a\n    a done\n"), ("b", "\n==> b\n    b done\n")]
    assert not capsys.readouterr().out
    say("after")
    assert capsys.readouterr().out == "after\n"
