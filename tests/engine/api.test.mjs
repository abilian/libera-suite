// The API between the interface and the engine is what the snapshot says it
// is (tests/engine/api/sdkjs-api.txt). A pin bump or a patch that changes it
// fails here; `node tests/engine/api-inventory.mjs --write` records the new
// API, and the snapshot's diff is what a reviewer reads beside the change.
//
// A member is compared by its class, its name, its editors and how many
// parameters it takes, not by the parameters' names: those are read from the
// built bundles, and the bundler renames one that shadows another (`value`
// as `value2`) whenever the bundling changes, which no caller can see (E4,
// E5). The file keeps the names, for the reader and the declarations.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { inventory, SNAPSHOT } from "./api-inventory.mjs";

/** A snapshot line as the test compares it. */
export function contract(line) {
  return line.replace(/^(member [\w.$]+)\(([^)]*)\)/, (_, member, params) => {
    const count = params ? params.split(", ").length : 0;
    return `${member}/${params === "..." ? "..." : count}`;
  });
}

test("the engine's API is the one the snapshot records", () => {
  const recorded = fs.readFileSync(SNAPSHOT, "utf8").split("\n").map(contract);
  const now = inventory().split("\n").map(contract);
  const gone = recorded.filter((line) => !now.includes(line));
  const added = now.filter((line) => !recorded.includes(line));
  assert.deepEqual(
    { gone, added },
    { gone: [], added: [] },
    "the API changed: review the difference, then `node tests/engine/api-inventory.mjs --write`",
  );
});

test("a member is compared by its parameters' number, not their names", () => {
  assert.equal(
    contract("member Asc.asc_docs_api.asc_Save(isAutoSave, isUndoRequest)  slide word"),
    "member Asc.asc_docs_api.asc_Save/2  slide word",
  );
  assert.equal(
    contract("member Asc.X.asc_f(value2)  word"),
    contract("member Asc.X.asc_f(value)  word"),
  );
  assert.notEqual(
    contract("member Asc.X.asc_f(a)  word"),
    contract("member Asc.X.asc_f(a, b)  word"),
  );
  assert.equal(contract("member Asc.X.asc_f()  word"), "member Asc.X.asc_f/0  word");
  assert.equal(contract("event asc_onX  word"), "event asc_onX  word");
});
