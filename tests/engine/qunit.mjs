// Enough of QUnit to run upstream's own test files (sdkjs/tests/**) inside a
// loaded engine: QUnit.module with its hooks, QUnit.test, and the assertions
// those files use. Each failed assertion is kept with its message, so a test
// reports what upstream's page would have shown.
import { isDeepStrictEqual } from "node:util";

// The assertions every test's `assert` has, which QUnit.assert forwards.
const STANDARD = new Set([
  "ok",
  "notOk",
  "equal",
  "strictEqual",
  "notStrictEqual",
  "deepEqual",
  "propEqual",
  "true",
  "false",
  "throws",
  "pushResult",
  "async",
]);

export function install(engine) {
  const tests = [];
  const callbacks = { testStart: [], testDone: [] };
  let hooks = {};
  let current = null;
  // Assertions a page adds to QUnit.assert (tests/word/common/common.js adds
  // `close`); each test's `assert` gets them too.
  const extensions = {};
  let module = "";

  const QUnit = {
    module(name, options, body) {
      module = name;
      const fn = typeof options === "function" ? options : body;
      hooks = typeof options === "object" && options !== null ? options : {};
      if (fn) {
        const nested = { before: [], beforeEach: [], afterEach: [], after: [] };
        fn({
          before: (f) => nested.before.push(f),
          beforeEach: (f) => nested.beforeEach.push(f),
          afterEach: (f) => nested.afterEach.push(f),
          after: (f) => nested.after.push(f),
        });
        const all = (fns) => () => {
          for (const f of fns) f();
        };
        hooks = {
          before: all(nested.before),
          beforeEach: all(nested.beforeEach),
          afterEach: all(nested.afterEach),
        };
      }
    },
    test(name, fn) {
      tests.push({ module, name, fn, hooks });
    },
    config: {},
    // Pages also call assertions on QUnit.assert itself, outside a test's
    // own `assert`: each forwards to the test running.
    assert: new Proxy(extensions, {
      get: (_, name) =>
        extensions[name] ??
        (STANDARD.has(name) ? (...args) => current[name](...args) : undefined),
    }),
    start() {},
    dump: { maxDepth: 5 },
    testStart: (fn) => callbacks.testStart.push(fn),
    testDone: (fn) => callbacks.testDone.push(fn),
  };
  engine.QUnit = QUnit;

  return async function run() {
    const results = [];
    const begun = new Set();
    for (const t of tests) {
      const failures = [];
      let count = 0;
      const pending = [];
      // A failure keeps the two values compared, where there are two, so
      // that the caller can tell a last-digit difference from a wrong one.
      const check = (ok, message, values = {}) => {
        count++;
        if (!ok) failures.push({ message: message ?? "(no message)", ...values });
      };
      const assert = {
        ok: (v, m) => check(Boolean(v), m),
        notOk: (v, m) => check(!v, m),
        // biome-ignore lint/suspicious/noDoubleEquals: QUnit's equal is loose
        equal: (a, b, m) => check(a == b, m, { actual: a, expected: b }),
        strictEqual: (a, b, m) => check(a === b, m, { actual: a, expected: b }),
        notStrictEqual: (a, b, m) => check(a !== b, m),
        deepEqual: (a, b, m) =>
          check(isDeepStrictEqual(a, b), m, { actual: a, expected: b }),
        propEqual: (a, b, m) => check(isDeepStrictEqual({ ...a }, { ...b }), m),
        throws: (fn, expected, m) => {
          let threw = false;
          try {
            fn();
          } catch {
            threw = true;
          }
          check(threw, typeof expected === "string" ? expected : m);
        },
        true: (v, m) => check(v === true, m, { actual: v, expected: true }),
        false: (v, m) => check(v === false, m, { actual: v, expected: false }),
        pushResult: ({ result, actual, expected, message }) =>
          check(result, message, { actual, expected }),
        async() {
          let done;
          pending.push(new Promise((r) => (done = r)));
          return () => done();
        },
      };
      for (const [name, fn] of Object.entries(extensions)) {
        assert[name] ??= fn;
      }
      current = assert;
      const details = { module: t.module, name: t.name };
      try {
        if (t.hooks.before && !begun.has(t.hooks)) {
          begun.add(t.hooks);
          t.hooks.before.call({});
        }
        for (const fn of callbacks.testStart) fn(details);
        t.hooks.beforeEach?.call({});
        await t.fn(assert);
        await Promise.race([
          Promise.all(pending),
          new Promise((r) => setTimeout(r, 5000)),
        ]);
        t.hooks.afterEach?.call({});
        for (const fn of callbacks.testDone)
          fn({ ...details, failed: failures.length });
      } catch (error) {
        failures.push({ message: `threw: ${error?.stack?.split("\n")[0] ?? error}` });
      }
      results.push({ module: t.module, name: t.name, assertions: count, failures });
    }
    return results;
  };
}
