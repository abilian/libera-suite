#!/bin/sh
# Assemble Libera.app.
#
#   build/macos-app.sh [DEST]        default: build/out/Libera.app
#
# A thin bundle: the launcher runs the libera package from the interpreter it
# was built against. It is what makes double-click, "Open With" and a Dock icon
# work; it is not a redistributable application, because nothing is embedded,
# signed or notarised. See notes/04-plan.md.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
APP="${1:-$HERE/out/Libera.app}"

# The interpreter to launch with, resolved now rather than at run time: the
# bundle has no PATH to speak of when Finder starts it.
PYTHON="${PYTHON:-$REPO/.venv/bin/python3}"
[ -x "$PYTHON" ] || { echo "FATAL: no interpreter at $PYTHON (set PYTHON=)" >&2; exit 1; }
"$PYTHON" -c "import libera" 2>/dev/null || {
    echo "FATAL: $PYTHON cannot import libera -- run 'uv sync' first" >&2; exit 1; }

VERSION="$(sed -n 's/^version *= *"\(.*\)"/\1/p' "$REPO/pyproject.toml" | head -1)"
: "${VERSION:=0.0.0}"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

echo "==> icon"
"$PYTHON" "$HERE/macos-icon.py" "$APP/Contents/Resources/Libera.icns"
rm -rf "$APP/Contents/Resources/Libera.iconset"

echo "==> launcher"
# Compiled, not a shell script: the bundle's executable has to be the process
# that stays, or the open-document Apple Event is delivered to a bundle that
# exec() has already replaced. See build/macos/launcher.m.
command -v clang >/dev/null || { echo "FATAL: clang not found (Xcode command line tools)" >&2; exit 1; }
clang -O2 -Wall -Werror -framework Cocoa \
    -DLIBERA_PYTHON="\"$PYTHON\"" \
    -o "$APP/Contents/MacOS/Libera" "$HERE/macos/launcher.m"

# LSMinimumSystemVersion, read off the binary rather than asserted beside it.
#
# It said 11.0 for as long as this script has existed, and the shipped x2t
# reports `minos 14.0` -- built against an Xcode SDK with no deployment target,
# so it takes the SDK's. A user on Big Sur, Monterey or Ventura therefore got a
# bundle that launched and a converter that could not load: the promise in the
# metadata, the refusal at the first save.
#
# Asking the artifact means the two cannot drift apart again. Put a deployment
# target on the core build and this follows it down without being told.
X2T="$("$PYTHON" -c 'from libera import payload; print(payload.resolve().x2t)' 2>/dev/null || true)"
MIN_MACOS=""
if [ -n "$X2T" ] && [ -x "$X2T" ]; then
    MIN_MACOS="$(otool -l "$X2T" |
        awk '/LC_BUILD_VERSION/ { found = 1 } found && $1 == "minos" { print $2; exit }')"
fi
# Nothing to ask, so the last measured value. The branch above corrects it the
# moment a payload is present, which is every case that ships.
: "${MIN_MACOS:=14.0}"

echo "==> Info.plist (minimum macOS $MIN_MACOS)"
# CFBundleDocumentTypes is what puts Libera Suite in Finder's "Open With" and lets a
# double-click reach us. LSHandlerRank Alternate: we claim to handle these, not
# to own them -- taking .docx away from whatever the user already uses would be
# rude for something this early.
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Libera</string>
  <key>CFBundleDisplayName</key><string>Libera Suite</string>
  <key>CFBundleIdentifier</key><string>eu.liberasuite.Libera</string>
  <key>CFBundleExecutable</key><string>Libera</string>
  <key>CFBundleIconFile</key><string>Libera.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <!-- Without NSPrincipalClass, AppKit never finishes launching the
       application and the open-document event is never delivered. -->
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>LSMinimumSystemVersion</key><string>$MIN_MACOS</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSHumanReadableCopyright</key>
  <string>Copyright © 2026 Abilian SAS. Based on Euro-Office and ONLYOFFICE.</string>
  <!-- The macOS half of src/libera/launcher.desktop, and the two are meant to
       stay the same set: one entry per format host/apps.py routes to an
       editor and the system has a name for. This declared Words alone, so
       macOS never offered to open a .xlsx or a .pptx that Libera Suite opens
       perfectly well -- the Linux entry had claimed all three since it was
       written. Measured both ways against
       NSWorkspace.URLsForApplicationsToOpenURL_: before, .docx yes and .xlsx
       and .pptx no; after, all three.

       Every identifier here was read out of the system rather than
       remembered, by asking UTType.typeWithFilenameExtension_ for each
       extension in apps.py. Two of its answers are deliberately not used.
       `org.libreoffice.visio-document` for .vsdx comes from LibreOffice being
       installed on the machine that asked, not from macOS, so claiming it
       would be claiming another application's type; Visio is therefore the one
       format the .desktop declares and this does not. And
       `com.microsoft.word.doc` is left out with it: .doc opens and cannot be
       saved, so offering to edit one leads somewhere Save does not go.

       One dict per editor rather than per format, because Open With shows
       CFBundleTypeName and "Spreadsheet" is more use there than four entries
       each naming one extension. -->
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeName</key><string>Word Document</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array>
        <string>org.openxmlformats.wordprocessingml.document</string>
        <string>org.oasis-open.opendocument.text</string>
        <string>public.rtf</string>
        <string>public.plain-text</string>
      </array>
    </dict>
    <dict>
      <key>CFBundleTypeName</key><string>Spreadsheet</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array>
        <string>org.openxmlformats.spreadsheetml.sheet</string>
        <string>org.oasis-open.opendocument.spreadsheet</string>
        <string>public.comma-separated-values-text</string>
        <string>public.tab-separated-values-text</string>
      </array>
    </dict>
    <dict>
      <key>CFBundleTypeName</key><string>Presentation</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array>
        <string>org.openxmlformats.presentationml.presentation</string>
        <string>org.oasis-open.opendocument.presentation</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
PLIST

# Finder caches bundle metadata aggressively; without this the document types
# are not noticed until logout.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "$APP" 2>/dev/null || true

echo
echo "app: $APP"
echo "  open it:            open '$APP'"
echo "  open a document:    open -a '$APP' FILE.docx"
