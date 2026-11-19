// The engine's undefined namespace members are the ones the list knows
// (tests/engine/api/undefined-members.txt), no more and no fewer: a new one
// is a typo or a constant lost, and fails here; one fixed must leave the list.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { KNOWN, undefinedMembers } from "./names.mjs";

test("no namespace member is read that nothing defines, but the known ones", () => {
  const known = fs
    .readFileSync(KNOWN, "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => line.split(/\s+/)[0]);
  const found = undefinedMembers().map((line) => line.split(/\s+/)[0]);
  assert.deepEqual(
    {
      new: found.filter((name) => !known.includes(name)),
      gone: known.filter((name) => !found.includes(name)),
    },
    { new: [], gone: [] },
  );
});
