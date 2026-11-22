// The engine's load order stays as clean as it is (E4): no cycle among the
// files' load-time needs, and no forward read but the known ones
// (tests/engine/api/forward-reads.txt), no more and no fewer. Needs the sdkjs
// sources (LIBERA_SDKJS_SRC), as upstream's suites do.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { EDITORS, mapOf } from "./deps.mjs";
import { observedForward } from "./deps-observed.mjs";

const SRC = process.env.LIBERA_SDKJS_SRC;
const KNOWN = new URL("./api/forward-reads.txt", import.meta.url);
const skip = !SRC && "LIBERA_SDKJS_SRC names no sources";

for (const editor of EDITORS) {
  test(`${editor}: no cycle among the files' load-time needs`, { skip }, () => {
    assert.deepEqual(mapOf(SRC, editor).knot, []);
  });

  test(`${editor}: no forward read but the known ones`, { skip }, () => {
    const known = fs
      .readFileSync(KNOWN, "utf8")
      .split("\n")
      .filter((line) => line && !line.startsWith("#"))
      .map((line) => line.split(/\s+/))
      .filter(([e]) => e === editor)
      .map(([, key, file]) => `${key} ${file}`);
    const found = observedForward(SRC, process.env.LIBERA_WEB_APPS, editor).forward.map(
      (f) => `${f.key} ${f.file}`,
    );
    assert.deepEqual(
      {
        new: found.filter((f) => !known.includes(f)),
        gone: known.filter((f) => !found.includes(f)),
      },
      { new: [], gone: [] },
    );
  });
}
