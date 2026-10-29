#!/bin/sh
# Prove the built core actually converts documents, not just that it linked.
#
#   build/engine/smoke.sh
#
# Exits non-zero on the first failure. Run it after every `build.sh build`:
# linking successfully is a much weaker statement than it looks. allfontsgen in
# particular exited 0 and wrote a well-formed AllFonts.js holding zero fonts
# when NSDirectory::GetFiles had no live branch for our platform -- an editor
# built on that renders every glyph as a box, and nothing anywhere says so.
#
# The pdf stage additionally covers doctrenderer (sdkjs running inside V8), and
# is skipped when no payload has been built. Everything else needs only core.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
# build/, one up: the scripts here and their inputs live beside each other.
BUILD="$(cd "$HERE/.." && pwd)"
. "$HERE/common.sh"

BIN="$OUT/core/bin"
PAYLOAD="${PAYLOAD:-$OUT/payload}"
[ -x "$BIN/x2t$EXE" ] || { echo "FAIL: no x2t at $BIN -- run build.sh build" >&2; exit 1; }

W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }

generate_fonts "$W"
SEL="$W/sdkjs/common/font_selection.bin"

echo "==> x2t docx -> odt -> docx"
# The sample is built on the pinned blank, not on core/Common/empty/*.bin --
# see notes/08-build.md on why that .bin is not a blank document.
LIBERA_BLANK="$SRC/document-templates/new/${BLANK_LOCALE:-en-US}/new.docx" \
    py "$BUILD/../tests/support/make_sample_docx.py" "$W/in.docx" >/dev/null
built x2t "$W/in.docx" "$W/mid.odt"  "$SEL" >"$W/x2t.log" 2>&1 || fail "docx -> odt failed; see $W/x2t.log"
built x2t "$W/mid.odt" "$W/out.docx" "$SEL" >>"$W/x2t.log" 2>&1 || fail "odt -> docx failed; see $W/x2t.log"

# Both files exist and both still hold the text: a converter that writes a
# valid-but-empty package passes every check that only stats the output.
py - "$W/mid.odt" "$W/out.docx" <<'PY' || fail "converted documents lost their text"
import re, sys, zipfile

NEEDLE = "Second paragraph"
for path, member in ((sys.argv[1], "content.xml"), (sys.argv[2], "word/document.xml")):
    text = re.sub(r"<[^>]+>", "", zipfile.ZipFile(path).read(member).decode("utf-8", "replace"))
    if NEEDLE not in text:
        print(f"  {path}: {member} does not contain {NEEDLE!r}", file=sys.stderr)
        raise SystemExit(1)
    print(f"    {path.rsplit('/', 1)[-1]}: text preserved")
PY

echo "==> x2t csv in Windows-1251 and Shift_JIS -> xlsx (ICU's converters)"
# ICU's data is filtered down to the converters (icu-data-filter.json), and a
# converter missing from it is another exit 0: x2t writes the workbook with
# the text gone. The ids are sdkjs's c_oAscEncodings, the ones x2t reads.
py - "$W" <<'PY'
import sys
w = sys.argv[1]
for idx, codec, text in ((14, "cp1251", "Привет мир"), (27, "shift_jis", "こんにちは世界")):
    open(f"{w}/{codec}.csv", "wb").write(f"{text},x\n".encode(codec))
    open(f"{w}/{codec}.expected", "w", encoding="utf-8").write(text)
    open(f"{w}/{codec}.xml", "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="utf-8"?><TaskQueueDataConvert>'
        f"<m_sFileFrom>{w}/{codec}.csv</m_sFileFrom><m_sFileTo>{w}/{codec}.xlsx</m_sFileTo>"
        f"<m_nFormatTo>257</m_nFormatTo><m_nCsvTxtEncoding>{idx}</m_nCsvTxtEncoding>"
        "<m_nCsvDelimiter>4</m_nCsvDelimiter></TaskQueueDataConvert>")
PY
for codec in cp1251 shift_jis; do
    built x2t "$W/$codec.xml" >>"$W/x2t.log" 2>&1 || fail "csv ($codec) -> xlsx failed; see $W/x2t.log"
done
py - "$W" <<'PY' || fail "a CSV lost its text on the way through its code page"
import re, sys, zipfile
w = sys.argv[1]
for codec in ("cp1251", "shift_jis"):
    text = open(f"{w}/{codec}.expected", encoding="utf-8").read()
    package = zipfile.ZipFile(f"{w}/{codec}.xlsx")
    found = "".join(package.read(n).decode() for n in package.namelist() if n.startswith("xl/"))
    if text not in re.sub(r"<[^>]+>", "", found):
        print(f"  {codec}.xlsx does not contain {text!r}", file=sys.stderr)
        raise SystemExit(1)
    print(f"    {codec}: text preserved")
PY

if [ ! -f "$PAYLOAD/AllFonts.js" ]; then
    echo "==> pdf: SKIPPED (no payload at $PAYLOAD -- run payload.sh)"
    echo "PASS (core only)"
    exit 0
fi

echo "==> x2t docx -> pdf (doctrenderer: sdkjs inside V8)"
# The params XML, not the three-argument CLI form: only <m_sFontDir> gives x2t's
# native font manager a font directory. Without it GetFontInfoByParams returns
# NULL and CPdfWriter::GetFontPath dereferences it -- a segfault, not an error.
# Every path through winpath: these are contents, not arguments, so nothing
# rewrites them on the way to a native x2t.
cat > "$W/job.xml" <<XML
<?xml version="1.0" encoding="utf-8"?>
<TaskQueueDataConvert>
  <m_sFileFrom>$(winpath "$W/in.docx")</m_sFileFrom>
  <m_sFileTo>$(winpath "$W/out.pdf")</m_sFileTo>
  <m_sAllFontsPath>$(winpath "$PAYLOAD/AllFonts.js")</m_sAllFontsPath>
  <m_sFontDir>$(winpath "$CORE_FONTS")</m_sFontDir>
  <m_sThemeDir>$(winpath "$PAYLOAD/sdkjs/slide/themes")</m_sThemeDir>
</TaskQueueDataConvert>
XML
built x2t "$W/job.xml" >"$W/pdf.log" 2>&1 || fail "docx -> pdf failed; see $W/pdf.log"

# A PDF of the right size with no glyphs in it is the failure that looks like
# success, so check for an embedded font and for text-showing operators.
py - "$W/out.pdf" <<'PY' || fail "pdf has no rendered text"
import re, sys, zlib
raw = open(sys.argv[1], "rb").read()
pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
fonts = len(re.findall(rb"/FontFile2", raw))
body = b""
for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
    try:
        body += zlib.decompress(m.group(1))
    except Exception:
        pass
shown = len(re.findall(rb"\].*?TJ|\(.*?\)\s*Tj", body, re.S))
print(f"    {pages} page(s), {fonts} embedded font(s), {shown} text operator(s)")
if not (pages and fonts and shown):
    raise SystemExit(1)
PY

echo "==> x2t pdf + a comment -> pdf (the PDF editor's save, replayed)"
# What saving a PDF is: the change log replayed onto the original, appended as
# an incremental update. smoke-pdf/ is one comment the PDF editor made on
# sample.pdf (2026-10-29), its log as the editor wrote it but for the account
# name it carried; .txt, because a change log is not JSON (each entry ends in
# a comma). When the replay fails -- drawingfile_native.js missing from
# sdkjs/pdf, for one -- x2t writes the original and exits 0, so the check is
# that the comment is there, after the original's bytes.
SMOKE_PDF="$(dirname "$0")/smoke-pdf"
if [ ! -d "$PAYLOAD/sdkjs/pdf" ]; then
    echo "    SKIPPED (this payload has no sdkjs/pdf)"
else
mkdir -p "$W/pdfdoc/changes"
cp "$SMOKE_PDF/sample.pdf" "$W/pdfdoc/Editor.bin"
cp "$SMOKE_PDF/changes0.txt" "$W/pdfdoc/changes/changes0.json"
cat > "$W/pdfjob.xml" <<XML
<?xml version="1.0" encoding="utf-8"?>
<TaskQueueDataConvert>
  <m_sFileFrom>$(winpath "$W/pdfdoc/Editor.bin")</m_sFileFrom>
  <m_sFileTo>$(winpath "$W/annotated.pdf")</m_sFileTo>
  <m_nFormatTo>513</m_nFormatTo>
  <m_bFromChanges>true</m_bFromChanges>
  <m_bDontSaveAdditional>true</m_bDontSaveAdditional>
  <m_sAllFontsPath>$(winpath "$PAYLOAD/AllFonts.js")</m_sAllFontsPath>
  <m_sFontDir>$(winpath "$CORE_FONTS")</m_sFontDir>
</TaskQueueDataConvert>
XML
built x2t "$W/pdfjob.xml" >"$W/pdfsave.log" 2>&1 || fail "pdf save failed; see $W/pdfsave.log"
py - "$SMOKE_PDF/sample.pdf" "$W/annotated.pdf" <<'PY' || fail "the comment was not saved: x2t wrote the original"
import re, sys
original, saved = (open(p, "rb").read() for p in sys.argv[1:])
update = saved[len(original):]
found = re.search(rb"/Contents \((.*?)\)\s*/", update, re.S)
text = found.group(1).replace(rb"\000", b"\0").decode("utf-16", "replace") if found else ""
print(f"    {len(original)} -> {len(saved)} bytes, comment: {text!r}")
if not (saved.startswith(original) and b"/Subtype /Text" in update and "zqx-smoke-comment" in text):
    raise SystemExit(1)
PY
fi

echo "PASS"
