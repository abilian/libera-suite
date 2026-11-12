#!/bin/sh
# The suite's gui tier (tests/d_gui) on Windows: the application in a real
# WebView2 window, in the session someone is logged on to.
#
#   sh build/windows/gui-test.sh            the payload in $OUT/payload
#   LIBERA_PAYLOAD=C:/p sh build/windows/gui-test.sh
#
# An ssh session has no desktop, so a window started from it never appears
# and the tier skips itself. A scheduled task with /it runs in the session
# this user is logged on to instead, at the console or over Remote Desktop,
# which therefore has to be there and active. This writes the task, runs it,
# waits for it, and hands back pytest's output and status. The real drags also
# need the screen unlocked, and skip, saying so, while it is locked.
# Measured on the Windows builder on 2026-11-05: 8 passed in 114 s.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$BUILD/.." && pwd)"
. "$BUILD/engine/common.sh"

[ -n "$EXE" ] || { echo "FATAL: this runs the Windows gui tier; run it on Windows" >&2; exit 1; }

PAYLOAD_DIR="${LIBERA_PAYLOAD:-$OUT/payload}"
[ -d "$PAYLOAD_DIR" ] || { echo "FATAL: no payload at $PAYLOAD_DIR -- lb payload build" >&2; exit 1; }
# Fifteen minutes: the tier takes two, a cold payload two more.
BUDGET="${GUI_TEST_BUDGET:-900}"
TASK="libera-gui-test"
WORK="$OUT/gui-test"
mkdir -p "$WORK"
LOG="$WORK/gui-test.log"
CMD="$WORK/gui-test.cmd"
rm -f "$LOG"

# `query user` lists desktop sessions, never this ssh one: a line per user,
# the session name (console, rdp-tcp#0) and its state. A disconnected one
# says Disc, and draws nothing.
query user 2>/dev/null | grep -qi "^ *>\{0,1\}$USERNAME  *[^ ]*  *[0-9]*  *active" || {
    echo "FATAL: $USERNAME has no active desktop session (console or Remote Desktop)," \
        "and a window needs one" >&2
    exit 1
}

# The task's own shell is cmd, in the desktop session, with none of ours. The
# redirection goes first: `echo exit=0>> log` is handle 0 redirected, and the
# line never reached the log.
#
# No fault handler: finding a file in Explorer through UI Automation raises a COM
# error it handles itself (0x8001010D), printed as a fatal one, with a whole stack,
# for each search. The application, which could really crash, is another process.
cat > "$CMD" <<EOF
@echo off
cd /d $(cygpath -w "$REPO")
set LIBERA_PAYLOAD=$(cygpath -m "$PAYLOAD_DIR")
uv run --no-sync pytest -p no:cacheprovider -p no:faulthandler -m gui tests/d_gui -q -rs > "$(cygpath -w "$LOG")" 2>&1
>> "$(cygpath -w "$LOG")" echo exit=%ERRORLEVEL%
EOF

echo "==> $TASK, in $USERNAME's desktop session"
schtasks //create //tn "$TASK" //tr "$(cygpath -w "$CMD")" //sc once //st 23:59 //it //f >/dev/null
schtasks //run //tn "$TASK" >/dev/null
waited=0
until grep -q '^exit=' "$LOG" 2>/dev/null; do
    if [ "$waited" -ge "$BUDGET" ]; then
        schtasks //end //tn "$TASK" >/dev/null 2>&1 || true
        echo "FATAL: no result after ${BUDGET} s; the log so far:" >&2
        cat "$LOG" >&2 2>/dev/null || true
        exit 1
    fi
    sleep 5
    waited=$((waited + 5))
done
schtasks //delete //tn "$TASK" //f >/dev/null

grep -v '^exit=' "$LOG"
status="$(sed -n 's/^exit=//p' "$LOG" | tr -d '\r ')"
# pytest exits 0 when every test skipped itself, which is the failure this
# script exists to get around: a window that could not be put on screen.
if [ "$status" = 0 ] && ! grep -q ' passed' "$LOG"; then
    echo "FATAL: nothing passed: every test skipped" >&2
    exit 1
fi
exit "$status"
