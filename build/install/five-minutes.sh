#!/bin/sh
# A user's first five minutes with an installed Libera Suite, in each editor:
# a blank opened in a real window, a line typed and saved, the line looked for
# in the file written, then the file opened again in a new window, which
# photographs its own page.
#
#   sh five-minutes.sh DRIVER WORK PYTHON...
#
# DRIVER is tests/d_gui/driver.py, which runs one window in the process of the
# Python it is given and drives it through pywebview; WORK a directory for the
# documents and the pictures; PYTHON... the command that runs the *installed*
# application's own Python: the virtualenv's on macOS, and on Linux
#
#   flatpak run --user --command=python3 eu.liberasuite.Libera
#
# so the window, the web engine, the host and the payload are the ones users
# got. Under Flatpak, DRIVER and WORK must be under $HOME, which the sandbox
# can read and write. Without a display (Linux, over ssh) run it under
# xvfb-run, as released-gui.sh does.
#
# What it says is a line per editor, FIVE_<EXT>=ok or the reason, and the size
# of its picture, SHOT_<EXT>=bytes: facts for whoever ran it, never an exit
# status, which over ssh is the login shell's.
#
# The text is entered through the editor's API, as the gui tier does, not
# typed: a keystroke cannot be sent to a window that has no focus under Xvfb.
set -u

DRIVER=$1
WORK=$2
shift 2
# Split on spaces where it is used: a command of several words, none of which
# has a space in it (a tool's path, flatpak's options, the app's id).
PY="$*"
MARK="Five minutes with Libera Suite"
mkdir -p "$WORK"

# The blanks out of the payload the installed application reports, never a
# path written here: inside a Flatpak it is under /app.
# shellcheck disable=SC2086  # $PY is a command of several words
$PY - "$WORK" <<'EOF' || { echo "FIVE=the installed Python could not read its payload"; exit; }
import pathlib, shutil, sys
from libera.payload import locate
root = locate.resolve().root
for ext in ("docx", "xlsx", "pptx"):
    shutil.copyfile(root / "empty" / f"new.{ext}", pathlib.Path(sys.argv[1]) / f"five.{ext}")
EOF

# One window on DOCUMENT doing STEPS (JSON), named NAME, with its page's
# picture at SHOT if that is not empty. Says nothing, or what went wrong.
window() {
    document=$1 steps=$2 name=$3 shot=$4
    home="$WORK/home-$name"
    result="$WORK/$name.json"
    mkdir -p "$home"
    rm -f "$result"
    plan=$(printf '{"document": "%s", "passwords": [], "steps": %s, "result": "%s", "home": "%s", "key": "", "decline": false, "shot": "%s"}' \
        "$document" "$steps" "$result" "$home" "$shot")
    # shellcheck disable=SC2086  # $PY is a command of several words
    $PY "$DRIVER" "$plan" > "$WORK/$name.log" 2>&1 || :
    if [ ! -f "$result" ]; then
        echo "the window died: $(tail -n 3 "$WORK/$name.log" | tr '\n' ' ')"
    elif ! grep -q '"ok": true' "$result"; then
        sed -n 's/.*"said": "\(.*\)"}.*/\1/p' "$result"
    fi
}

for ext in docx xlsx pptx; do
    doc="$WORK/five.$ext"
    upper=$(printf '%s' "$ext" | tr '[:lower:]' '[:upper:]')
    said=$(window "$doc" "[[\"type-and-save\", \"$MARK\"]]" "typed-$ext" "")
    if [ -n "$said" ]; then
        echo "FIVE_$upper=typing and saving: $said"
        continue
    fi
    # shellcheck disable=SC2086  # $PY is a command of several words
    if ! $PY - "$doc" "$MARK" <<'EOF'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
xml = [n for n in z.namelist() if n.endswith(".xml")]
sys.exit(0 if any(sys.argv[2].encode() in z.read(n) for n in xml) else 1)
EOF
    then
        echo "FIVE_$upper=saved, and the text is not in the file"
        continue
    fi
    shot="$WORK/five-$ext.png"
    rm -f "$shot"
    said=$(window "$doc" "[[\"photographed\", \"$shot\"]]" "reopened-$ext" "$shot")
    if [ -n "$said" ]; then
        echo "FIVE_$upper=opening it again: $said"
        continue
    fi
    echo "FIVE_$upper=ok"
    echo "SHOT_$upper=$(wc -c < "$shot" | tr -d ' ')"
done
