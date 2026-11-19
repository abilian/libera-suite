// Each editor's engine loads in Node, from the payload, as x2t loads it.
import assert from "node:assert/strict";
import { test } from "node:test";
import { EDITORS, load } from "./harness.mjs";

// What each engine publishes, at the least: the API object's class among them.
const EXPECTED = {
  word: ["Asc", "AscCommon", "AscFormat", "AscWord", "AscDFH"],
  cell: ["Asc", "AscCommon", "AscFormat", "AscCommonExcel", "AscDFH"],
  slide: ["Asc", "AscCommon", "AscFormat", "AscCommonSlide", "AscDFH"],
  visio: ["Asc", "AscCommon", "AscFormat", "AscDFH"],
};
const API = {
  word: "asc_docs_api",
  cell: "spreadsheet_api",
  slide: "asc_docs_api",
  visio: "VisioEditorApi",
};

for (const editor of EDITORS) {
  test(`${editor} loads and publishes its namespaces`, () => {
    const engine = load(editor);
    for (const name of EXPECTED[editor]) {
      assert.equal(typeof engine[name], "object", `${editor}: no ${name}`);
    }
    assert.equal(
      typeof engine.Asc[API[editor]],
      "function",
      `${editor}: no Asc.${API[editor]}`,
    );
  });
}
