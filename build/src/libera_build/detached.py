"""A long job on a builder that outlives the connection that started it.

A build is an hour or more, and the connection to a builder does not always
last that long: on 2026-11-01 builder-windows dropped off the network four
times in an afternoon, and each drop ended the phase that was streaming its
build over ssh, while the build itself carried on there unwatched. So a job
is started detached from the session, in a folder of its own on the builder,
`~/.lb/runs/<name>/`, which holds:

    job.sh   the script
    log      everything it prints
    pid      the process running it, while it runs
    done     its exit status, once it has ended

and the driver polls that folder with short connections of their own, each
bringing back what the log gained since the last. A connection that fails is
a poll that missed, not a build that failed.

Detaching is measured, per system (2026-11-01). On Linux, a job put in the
background with `setsid`, or `nohup` alone, outlives the session. On Windows,
under Git Bash and Windows's OpenSSH, a job put in the background holds the
session open until it ends; started through PowerShell's `Start-Process`, it
is detached and outlives it. macOS has no `setsid` and needs only `nohup`.

These are the scripts, pure strings; `release.builds` runs them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The lines a poll's answer starts and ends with, around whatever the log
# gained: ssh may print its own warnings first, and a capture strips spaces.
POLL_BEGIN = "__LIBERA_POLL_BEGIN__"
POLL_MARK = "__LIBERA_POLL__"
# Delimiters of the scripts written into the run folder; no script holds them.
JOB_END = "__LIBERA_JOB_END__"
RUN_END = "__LIBERA_RUN_END__"


def run_folder(name: str) -> str:
    """Where a job lives on its builder, as the remote shell spells it. The
    name is the command, made safe as a single path segment, so that a re-run
    of the same command finds the job it started."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "job"
    return f'"$HOME/.lb/runs/{safe}"'


def start_script(name: str, script: str) -> str:
    """bash that starts `script` detached, or finds it already running.

    It prints ATTACHED=1 when a job of that name is still running (a re-run
    of a phase whose driver died watches it rather than starting a second
    build on the same tree), STARTED=1 once the new job has written its pid,
    or START=failed.
    """
    run = run_folder(name)
    return f"""
RUN={run}
if [ -f "$RUN/pid" ] && [ ! -f "$RUN/done" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null
then echo "ATTACHED=1"; exit
fi
rm -rf "$RUN" && mkdir -p "$RUN" || {{ echo "START=failed: no $RUN"; exit; }}
cat > "$RUN/job.sh" <<'{JOB_END}'
{script}
{JOB_END}
cat > "$RUN/run.sh" <<'{RUN_END}'
cd "$(dirname "$0")" || exit
echo $$ > pid
bash -l job.sh > log 2>&1 < /dev/null
echo "$?" > done
{RUN_END}
if command -v powershell.exe >/dev/null 2>&1; then
    bash_exe=$(cygpath -w "$(command -v bash)")
    run_sh=$(cygpath -w "$RUN/run.sh")
    powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden \\
        -FilePath '$bash_exe' -ArgumentList '-l','$run_sh'"
elif command -v setsid >/dev/null 2>&1; then
    setsid nohup bash "$RUN/run.sh" > /dev/null 2>&1 < /dev/null &
else
    nohup bash "$RUN/run.sh" > /dev/null 2>&1 < /dev/null &
fi
for _ in $(seq 60); do [ -f "$RUN/pid" ] && break; sleep 0.5; done
if [ -f "$RUN/pid" ]; then echo "STARTED=1"; else echo "START=failed: no pid"; fi
"""


def poll_script(name: str, offset: int) -> str:
    """bash that prints what the log gained past `offset`, then a last line
    with the log's size, the exit status once there is one, and whether the
    job's process is still alive."""
    run = run_folder(name)
    return f"""
RUN={run}
[ -d "$RUN" ] || {{ echo "{POLL_MARK} GONE=1"; exit; }}
# Whether it runs, then whether it has ended, then the log's size, in that
# order: run.sh writes done before it exits, so a poll that finds the job
# ended reads all of its log. Read the other way round, a job that ended
# between two reads was taken for ended with its last lines, its verdict
# among them, unread.
alive=0
[ -f "$RUN/pid" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null && alive=1
done=$(cat "$RUN/done" 2>/dev/null)
size=$(wc -c < "$RUN/log" 2>/dev/null | tr -d ' ')
size=${{size:-0}}
echo "{POLL_BEGIN}"
if [ "$size" -gt {offset} ]; then
    tail -c +{offset + 1} "$RUN/log" | head -c $((size - {offset}))
fi
echo
echo "{POLL_MARK} SIZE=$size DONE=$done ALIVE=$alive"
"""


@dataclass(frozen=True)
class Poll:
    """What one poll found: the log's new text, and the job's state."""

    text: str
    size: int
    done: str  # the exit status, "" while it runs
    alive: bool
    gone: bool = False


def parse_poll(out: str) -> Poll | None:
    """A poll's answer, or None when there was none: the connection failed,
    or the builder answered with something else."""
    head, sep, last = out.rpartition(POLL_MARK)
    if not sep:
        return None
    facts = dict(field.split("=", 1) for field in last.split() if "=" in field)
    if facts.get("GONE") == "1":
        return Poll("", 0, "", alive=False, gone=True)
    try:
        size = int(facts.get("SIZE", ""))
    except ValueError:
        return None
    _, began, text = head.partition(POLL_BEGIN + "\n")
    if not began:
        return None
    # The poll echoes one newline after the log's text, so that its last
    # line starts a line of its own.
    text = text.removesuffix("\n")
    return Poll(text, size, facts.get("DONE", ""), facts.get("ALIVE") == "1")
