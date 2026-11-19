// Patches of our queue (build/upstream/patches/sdkjs), checked in the engine
// itself: the documents tests/support/documents.py builds, converted by the
// payload's x2t, opened and laid out here. The integration and end-to-end
// tests check the same patches through x2t's PDF and through the editor;
// these say what the engine does, in milliseconds.
import assert from "node:assert/strict";
import path from "node:path";
import { test } from "node:test";
import vm from "node:vm";
import { openDocument } from "./document.mjs";
import { load } from "./harness.mjs";

const SAMPLES = process.env.LIBERA_SAMPLES;
const skip = !SAMPLES && "LIBERA_SAMPLES names no folder of samples";
const sample = (name) => path.join(SAMPLES, `${name}.bin`);

// A run item's width in millimetres. Text keeps its width in units of
// 1/TEXTWIDTH_DIVIDER mm; a positional tab, in millimetres. An engine without
// sdkjs 0017 has no positional tab class at all.
function width(engine, item) {
  const ptab = engine.AscWord.CRunPTab;
  return ptab && item instanceof ptab
    ? item.Width
    : item.Width / engine.AscWord.TEXTWIDTH_DIVIDER;
}

// Each word of a one-line paragraph, with where it starts and ends, in mm.
function words(engine, paragraph) {
  const found = [];
  let x = paragraph.Lines[0].Ranges[0].X;
  for (const run of paragraph.Content) {
    for (const item of run.Content ?? []) {
      const w = width(engine, item);
      if (item.IsText?.()) {
        const last = found.at(-1);
        if (last && last.end === x) {
          last.word += String.fromCodePoint(item.Value);
          last.end = x + w;
        } else {
          found.push({ word: String.fromCodePoint(item.Value), start: x, end: x + w });
        }
      }
      x += w;
    }
  }
  return found;
}

test("sdkjs 0017: positional tabs put their text at the centre and the edge", {
  skip,
}, async () => {
  const { engine, api } = await openDocument("word", sample("ptabs"));
  const paragraph = api.WordControl.m_oLogicDocument.Content[0];
  const { X: left, XEnd: right } = paragraph.Lines[0].Ranges[0];
  const placed = Object.fromEntries(words(engine, paragraph).map((w) => [w.word, w]));
  assert.deepEqual(Object.keys(placed), ["Left", "Mid", "End"]);
  assert.ok(
    Math.abs((placed.Mid.start + placed.Mid.end) / 2 - (left + right) / 2) < 0.1,
    placed,
  );
  assert.ok(Math.abs(placed.End.end - right) < 0.1, placed);
});

test("sdkjs 0018: a SET field's result is laid out but not drawn", {
  skip,
}, async () => {
  const { engine, api } = await openDocument("word", sample("set-field"));
  const runs = api.WordControl.m_oLogicDocument.Content[0].Content;
  // Each run's text, and whether any of its characters is drawn.
  const drawn = Array.from(runs, (run) => {
    const text = (run.Content ?? []).filter((i) => i.IsText?.());
    return [
      text.map((i) => String.fromCodePoint(i.Value)).join(""),
      text.some((i) => i.WidthVisible !== 0 && width(engine, i) > 0),
    ];
  }).filter(([text]) => text);
  assert.deepEqual(
    drawn.filter(([, visible]) => visible).map(([text]) => text),
    ["Before", "after"],
  );
  assert.ok(
    drawn.some(([text, visible]) => text === "2001" && !visible),
    drawn,
  );
});

test("sdkjs 0022: a document's style ids survive the engine's own save", {
  skip,
}, async () => {
  const ids = (api) => {
    const doc = api.WordControl.m_oLogicDocument;
    return Array.from(doc.Content)
      .filter((p) => p.Pr?.PStyle)
      .map((p) => doc.Styles.Style[p.Pr.PStyle].EoDocxStyleId);
  };
  const first = await openDocument("word", sample("style-ids"));
  assert.deepEqual(ids(first.api), ["Heading1", "MyQuote"]);
  const again = await openDocument("word", first.save());
  assert.deepEqual(ids(again.api), ["Heading1", "MyQuote"]);
});

test("sdkjs 0026: Convert Text to Table checks its lock against a change type", {
  skip,
}, async () => {
  const { engine, api } = await openDocument("word", sample("sample"));
  const doc = api.WordControl.m_oLogicDocument;
  const asked = [];
  doc.IsSelectionLocked = (type) => asked.push(type) > 0; // locked: change nothing
  doc.SelectAll();
  doc.ConvertTextToTable({});
  assert.deepEqual(asked, [engine.AscCommon.changestype_Document_Content]);
});

// The JSON converters ask the running editor which editor they serve.
function withEditor(editor, id) {
  const engine = load(editor);
  vm.runInContext(
    `var editor = {editorId: AscCommon.c_oEditorId.${id}}; Asc.editor = editor;`,
    engine,
  );
  return engine;
}

test("sdkjs 0028: a sheet protection's algorithm goes to JSON and back", () => {
  const engine = withEditor("cell", "Spreadsheet");
  const { AscCommon, AscJsonConverter } = engine;
  for (const [name, value] of Object.entries(AscCommon.c_oSerAlgorithmNameTypes)) {
    const json = JSON.parse(
      JSON.stringify(
        new AscJsonConverter.WriterToJSON().SerSheetProtection({
          algorithmName: value,
        }),
      ),
    );
    const sheet = {};
    new AscJsonConverter.ReaderFromJSON().SheetProtectionFromJSON(json, sheet);
    assert.equal(sheet.sheetProtection.algorithmName, value, name);
  }
});

test("sdkjs 0029: SHA-1 is read from and written to XML", () => {
  const { AscCommon, AscCommonExcel } = load("cell");
  const sha1 = AscCommon.c_oSerAlgorithmNameTypes.SHA_1;
  assert.equal(AscCommonExcel.FromXml_ST_AlgorithmName("SHA-1"), sha1);
  assert.equal(AscCommonExcel.ToXml_ST_AlgorithmName(sha1), "SHA-1");
});

test("sdkjs 0030: a 3D shape's contour and extrusion colours go to JSON and back", () => {
  const engine = withEditor("word", "Word");
  const back = vm.runInContext(
    `var sp = new AscFormat.Sp3d();
     sp.setContourClr(AscFormat.CreateUniColorRGB(255, 0, 0));
     sp.setExtrusionClr(AscFormat.CreateUniColorRGB(0, 0, 255));
     var json = JSON.parse(JSON.stringify(new AscJsonConverter.WriterToJSON().SerSp3D(sp)));
     new AscJsonConverter.ReaderFromJSON().Sp3DFromJSON(json);`,
    engine,
  );
  const rgb = (c) => [c.color.RGBA.R, c.color.RGBA.G, c.color.RGBA.B];
  assert.deepEqual(rgb(back.contourClr), [255, 0, 0]);
  assert.deepEqual(rgb(back.extrusionClr), [0, 0, 255]);
});
