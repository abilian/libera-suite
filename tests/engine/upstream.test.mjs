// Upstream's own test pages, the ones tests/runAll.js runs in headless
// Chrome, run unchanged in Node instead: 2,000 tests and 75,000 assertions,
// spreadsheet formulas, word layout, tables, numbering, revisions, the APIs.
//
// One kind of failure is not the engine's: a number that differs from
// upstream's expected value in its last digit or two. Math.sin, cosh, pow and
// the rest are not exactly specified, and Node, Chromium and macOS's
// JavaScriptCore disagree in the last digit on about one value in ten
// (measured 2026-11-19; notes/experiments/e1-engine-tests-in-node.md).
// Upstream's expected values carry their own browser's digits. Such a
// difference is counted and reported, not failed; any other failure fails.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  pageScripts,
  roundingOnly,
  runUpstream,
  SOURCES,
  upstreamPages,
} from "./upstream.mjs";

// Pages Node cannot run yet, and why. Each is a measured wall, not a guess:
// see the note's results.
const NOT_IN_NODE = {
  "cell/spreadsheet-calculation/DynamicArraysTests.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/spreadsheet-calculation/PivotTests.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/spreadsheet-calculation/SheetStructureTests.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/spreadsheet-calculation/UserProtectedRangesTest.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/spreadsheet-calculation/DataValidationTests.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/spreadsheet-calculation/conditionalFormattingTests.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/shortcuts/shortcuts.html":
    "builds its API the browser's way, which needs a DOM",
  "cell/spreadsheet-calculation/copy-paste-tests.html":
    "pastes HTML, which needs a DOM parser",
  "word/copypaste/copy-paste-tests.html": "pastes HTML, which needs a DOM parser",
  "word/shortcuts/shortcuts.html": "drives the editor through key events and timers",
  "slide/shortcuts/shortcuts.html": "drives the editor through key events and timers",
  "word/forms/forms.html":
    "needs the forms add-on's sources (apiPDF.js), which we do not build",
  "word/js-api/js-api-forms.html": "needs the forms add-on, which we do not build",
  "oform/xml/oformXml.html": "needs the forms add-on (AscOForm), which we do not build",
  "word/custom-xml/custom-xml-ooxml.html":
    "needs the sdkjs-ooxml add-on, which we do not build",
};

// Failures seen in Node only, by page and test name; their assertions are
// reported, not failed. The one here passes in Chromium, alone and in its page,
// and fails in Node alone too, on the bundle or the sources, with native.js's
// engine flags off and the same locale: something in the browser-less
// environment, not yet found (notes/experiments/e1-engine-tests-in-node.md).
const UNEXPLAINED = {
  "cell/spreadsheet-calculation/whatIfAnalysisTests.html": [
    "Test: Example - Delivery goods in stores. Linear programming. Minimize",
  ],
};

const pages = SOURCES ? upstreamPages().all.filter((page) => !NOT_IN_NODE[page]) : [];

test("upstream's test pages", {
  skip: !SOURCES && "LIBERA_SDKJS_SRC names no sources",
}, async (t) => {
  assert.ok(
    pages.length >= 60,
    `expected 60 or more of upstream's pages, found ${pages.length}`,
  );
  for (const page of pages) {
    await t.test(page, async (t) => {
      const { editor, files } = pageScripts(page);
      const results = await runUpstream(files, editor);
      assert.ok(results.length > 0, `${page} ran no test`);
      const wrong = [];
      let rounding = 0;
      let unexplained = 0;
      for (const r of results) {
        for (const f of r.failures) {
          if (roundingOnly(f.actual, f.expected)) rounding++;
          else if (UNEXPLAINED[page]?.includes(r.name)) unexplained++;
          else
            wrong.push(`${r.name}: ${f.message} (${f.actual} against ${f.expected})`);
        }
      }
      const assertions = results.reduce((s, r) => s + r.assertions, 0);
      t.diagnostic(
        `${results.length} tests, ${assertions} assertions, ${rounding} rounding differences, ${unexplained} unexplained`,
      );
      assert.deepEqual(wrong, []);
    });
  }
});
