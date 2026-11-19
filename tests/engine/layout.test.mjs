// Documents opened and laid out in Node, one per editor: the samples
// tests/support/documents.py builds, converted by the payload's own x2t,
// which the pytest bridge does and names here.
import assert from "node:assert/strict";
import path from "node:path";
import { test } from "node:test";
import { openDocument } from "./document.mjs";

const SAMPLES = process.env.LIBERA_SAMPLES;
const skip = !SAMPLES && "LIBERA_SAMPLES names no folder of samples";
const sample = (name) => path.join(SAMPLES, `${name}.bin`);

test("a document opens and lays out as x2t lays it out", { skip }, async () => {
  const { api, pages } = await openDocument("word", sample("sample"));
  const content = api.WordControl.m_oLogicDocument.Content;
  assert.equal(pages, 1);
  assert.equal(content.length, 3);
  assert.match(content[1].GetText(), /^If you can read this in the editor/);
  // x2t's PDF of the same document breaks this paragraph once, after
  // "Python-served", and the shorter ones not at all.
  // Array.from: the engine's arrays belong to its own context, and a strict
  // comparison would hold their prototype against them.
  assert.deepEqual(
    Array.from(content, (paragraph) => paragraph.Lines.length),
    [1, 2, 1],
  );
});

test("a spreadsheet opens: the blank's one sheet", { skip }, async () => {
  const { api, pages } = await openDocument("cell", sample("blank-table"));
  assert.equal(pages, 1);
  assert.equal(api.wbModel.getWorksheetCount(), 1);
  assert.equal(api.wbModel.getWorksheet(0).getName(), "Sheet1");
});

test("a presentation opens: the blank's one slide", { skip }, async () => {
  const { api, pages } = await openDocument("slide", sample("blank-deck"));
  assert.equal(pages, 1);
  assert.equal(api.WordControl.m_oLogicDocument.Slides.length, 1);
});
