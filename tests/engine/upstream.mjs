// Upstream's own QUnit files (sdkjs/tests/**), run unchanged in a loaded
// engine. They need sdkjs's sources, which the payload does not carry:
// LIBERA_SDKJS_SRC names them, and without it these tests skip.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { load } from "./harness.mjs";
import { install } from "./qunit.mjs";

export const SOURCES = process.env.LIBERA_SDKJS_SRC;

const RELATIVE = 1e-13;

const NUMBER = /[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?/gi;

// Equal but for rounding: the same text around the numbers (a complex
// number is two of them, "a+bi"), and each pair of numbers within RELATIVE.
export function roundingOnly(actual, expected) {
  if (typeof actual === "number" && typeof expected === "number") {
    return Math.abs(actual - expected) <= RELATIVE * Math.max(1, Math.abs(expected));
  }
  if (typeof actual !== "string" || typeof expected !== "string") return false;
  if (actual.replace(NUMBER, "#") !== expected.replace(NUMBER, "#")) return false;
  const a = actual.match(NUMBER) ?? [];
  const b = expected.match(NUMBER) ?? [];
  return a.length > 0 && a.every((x, i) => roundingOnly(Number(x), Number(b[i])));
}

// Upstream's own list of pages (tests/runAll.js: allTests), and the ones it
// skips, with its reasons (skippedTests).
export function upstreamPages(sources = SOURCES) {
  const text = fs.readFileSync(path.join(sources, "tests", "runAll.js"), "utf8");
  const block = (name) =>
    text.slice(text.indexOf(`const ${name}`)).split(/\n[}\]];/)[0];
  const all = [...block("allTests").matchAll(/'([^']+\.html)'/g)].map((m) => m[1]);
  const skipped = Object.fromEntries(
    [...block("skippedTests").matchAll(/'([^']+\.html)'\s*:\s*'([^']*)'/g)].map((m) => [
      m[1],
      m[2],
    ]),
  );
  return { all, skipped };
}

// What a page loads after the engine, from its HTML: its own scripts, in
// order, each relative to sdkjs's sources; and which editor's engine it wants,
// from the develop/sdkjs/<editor>/scripts.js it would have loaded the engine
// with. A path that does not resolve from the page's folder is tried from the
// root of the sources, where some pages' paths point when served. The page's
// QUnit and jQuery (tests/node_modules, since upstream serves them locally)
// are left out: qunit.mjs stands in for the one, and of the other the pages
// use only $(fn), which runUpstream gives them.
export function pageScripts(page, sources = SOURCES) {
  const html = fs.readFileSync(path.join(sources, "tests", page), "utf8");
  const editor = /develop\/sdkjs\/(\w+)\/scripts\.js/.exec(html)?.[1];
  if (!editor) throw new Error(`${page} loads no develop/sdkjs/<editor>/scripts.js`);
  const folder = path.dirname(path.join("tests", page));
  const files = [...html.matchAll(/src="([^"]+)"/g)]
    .map((m) => m[1])
    .filter(
      (src) =>
        !/^https?:|scripts\.js$|\+ item \+|node_modules\/(qunit|jquery)\//.test(src),
    )
    .map((src) => {
      const near = path.normalize(path.join(folder, src));
      if (fs.existsSync(path.join(sources, near))) return near;
      const root = src.replace(/^(\.\.\/)+/, "");
      if (fs.existsSync(path.join(sources, root))) return root;
      throw new Error(`${page}: no ${src}`);
    });
  return { editor, files };
}

// A test page's scripts after the engine, relative to sdkjs's sources, as its
// HTML lists them; the test file itself last.
export async function runUpstream(files, editor = "cell", sources = SOURCES) {
  // Upstream's pages load the sources one file at a time, so each file's
  // top-level names are globals there, and the tests read them as such.
  const engine = load(editor, undefined, { pageScope: true });
  // x2t's jQuery stub, up to 9.3.8, gave the engine all of jQuery; since,
  // the pages' $(fn), which runs fn once the page is ready, is all there is.
  if (!engine.$) {
    const queued = [];
    engine.$ = (fn) => queued.push(fn);
    engine.$.ready = () => {
      for (const fn of queued.splice(0)) fn();
    };
  }
  const run = install(engine);
  engine.setTimeout = setTimeout;
  engine.clearTimeout = clearTimeout;
  for (const file of files) {
    const full = path.join(sources, file);
    vm.runInContext(fs.readFileSync(full, "utf8"), engine, { filename: full });
  }
  // Pages register their tests in $(function () { ... }), which jQuery runs
  // once the page is ready, told so here.
  vm.runInContext("$.ready()", engine);
  return run();
}
