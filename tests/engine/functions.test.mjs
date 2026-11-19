// Spreadsheet functions, called directly, against the values Microsoft's own
// documentation gives for them. These need no source tree, so they run
// against any payload, the installed components included; upstream's far
// larger suites (upstream.test.mjs) need sdkjs's sources.
import assert from "node:assert/strict";
import { test } from "node:test";
import { load } from "./harness.mjs";
import { roundingOnly } from "./upstream.mjs";

const engine = load("cell");
const X = engine.AscCommonExcel;
X.getFormulasInfo(); // registers the functions in cFormulaFunction

const num = (v) => new X.cNumber(v);
const str = (v) => new X.cString(v);

function calculate(name, args) {
  const Fn = X.cFormulaFunction[name];
  assert.ok(Fn, `no function ${name}`);
  return new Fn().Calculate(args).getValue();
}

// [function, arguments, expected, source]
const CASES = [
  // https://support.microsoft.com/office/mod-function-9b6cd169-b6ee-406a-a97b-edf2a9dc24f3
  ["MOD", [num(3), num(2)], 1, "MOD"],
  ["MOD", [num(-3), num(2)], 1, "MOD"],
  ["MOD", [num(3), num(-2)], -1, "MOD"],
  ["MOD", [num(-3), num(-2)], -1, "MOD"],
  // https://support.microsoft.com/office/round-function-c018c5d8-40fb-4053-90b1-b3e7f61a213c
  ["ROUND", [num(2.15), num(1)], 2.2, "ROUND"],
  ["ROUND", [num(2.149), num(1)], 2.1, "ROUND"],
  ["ROUND", [num(-1.475), num(2)], -1.48, "ROUND"],
  ["ROUND", [num(21.5), num(-1)], 20, "ROUND"],
  // https://support.microsoft.com/office/int-function-a6c4af9e-356d-4369-ab6a-cb1fd9d343ef
  ["INT", [num(8.9)], 8, "INT"],
  ["INT", [num(-8.9)], -9, "INT"],
  // https://support.microsoft.com/office/trunc-function-8b86a64c-3127-43db-ba14-aa5ceb292721
  ["TRUNC", [num(8.9)], 8, "TRUNC"],
  ["TRUNC", [num(-8.9)], -8, "TRUNC"],
  // https://support.microsoft.com/office/abs-function-3420200f-5628-4e8c-99da-c99d7c87713c
  ["ABS", [num(-2)], 2, "ABS"],
  // https://support.microsoft.com/office/power-function-d3f2908b-56f4-4c3f-895a-07fb519c362a
  ["POWER", [num(5), num(2)], 25, "POWER"],
  ["POWER", [num(4), num(5 / 4)], 5.656854249492381, "POWER"],
  ["SUM", [num(2), num(3), num(4)], 9, "SUM"],
  ["CONCATENATE", [str("a"), str("b")], "ab", "CONCATENATE"],
];

for (const [name, args, expected] of CASES) {
  const shown = args.map((a) => JSON.stringify(a.getValue())).join(", ");
  // Equal, or but for the last digits Math gives differently in each engine
  // (Node 20's V8 and Node 26's differ on POWER(4, 1.25)), as for upstream's
  // own pages.
  test(`${name}(${shown}) is ${expected}`, () => {
    const actual = calculate(name, args);
    assert.ok(actual === expected || roundingOnly(actual, expected), `${actual}`);
  });
}

test("487 or more functions register", () => {
  assert.ok(Object.keys(X.cFormulaFunction).length >= 487);
});
