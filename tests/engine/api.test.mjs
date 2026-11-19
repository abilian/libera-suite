// The API between the interface and the engine is what the snapshot says it
// is (tests/engine/api/sdkjs-api.txt). A pin bump or a patch that changes it
// fails here; `node tests/engine/api-inventory.mjs --write` records the new
// API, and the snapshot's diff is what a reviewer reads beside the change.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { inventory, SNAPSHOT } from "./api-inventory.mjs";

test("the engine's API is the one the snapshot records", () => {
  const recorded = fs.readFileSync(SNAPSHOT, "utf8").split("\n");
  const now = inventory().split("\n");
  const gone = recorded.filter((line) => !now.includes(line));
  const added = now.filter((line) => !recorded.includes(line));
  assert.deepEqual(
    { gone, added },
    { gone: [], added: [] },
    "the API changed: review the difference, then `node tests/engine/api-inventory.mjs --write`",
  );
});
