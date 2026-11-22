// E5's measurement: what one engine library shared by the four editors takes.
//
// The shared files are those all four editors load. For them: their size,
// and so what sharing would save; the pairs among them that the editors load
// in different orders, which one shared bundle must settle; what they need
// while they load from files that are not shared, which would then come after
// them (static and observed needs, deps.mjs and deps-observed.mjs); and the
// names that cross sdk-all.js's one function scope between shared and
// unshared files, in either direction, which each side loses once the shared
// files leave that bundle (E4).
//
// `node shared.mjs`, with LIBERA_SDKJS_SRC and LIBERA_WEB_APPS.
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { analyse, EDITORS, filesOf, mapOf } from "./deps.mjs";
import { observedNeeds } from "./deps-observed.mjs";

function sections(src, editor) {
  const configs = createRequire(path.join(src, "build", "package.json"))(
    path.join(src, "build", "lib", "sdk-configs.cjs"),
  );
  const sdk = configs.loadAllConfigs(src, [])[editor].sdk;
  const rel = (files) => configs.expandGlobs(files).map((f) => path.relative(src, f));
  return {
    min: new Set(rel(configs.getFilesMin(sdk, "desktop"))),
    all: new Set(rel(configs.getFilesAll(sdk, "desktop"))),
  };
}

function topNames(statement) {
  if (
    (statement.type === "FunctionDeclaration" ||
      statement.type === "ClassDeclaration") &&
    statement.id
  )
    return [statement.id.name];
  if (statement.type === "VariableDeclaration") {
    return statement.declarations
      .filter((d) => d.id.type === "Identifier")
      .map((d) => d.id.name);
  }
  return [];
}

export function measure(src, webApps) {
  const acorn = createRequire(path.join(src, "build", "package.json"))("acorn");
  const orders = Object.fromEntries(
    EDITORS.map((e) => [e, filesOf(src, e).map((f) => path.relative(src, f))]),
  );
  const shared = orders.word.filter((f) => EDITORS.every((e) => orders[e].includes(f)));
  const isShared = new Set(shared);
  const bytes = (files) =>
    files.reduce((a, f) => a + fs.statSync(path.join(src, f)).size, 0);

  // Pairs of shared files in different orders.
  const position = Object.fromEntries(
    EDITORS.map((e) => [e, new Map(orders[e].map((f, i) => [f, i]))]),
  );
  const conflicts = [];
  for (let i = 0; i < shared.length; i++) {
    for (let j = i + 1; j < shared.length; j++) {
      const [a, b] = [shared[i], shared[j]];
      const before = EDITORS.map((e) => position[e].get(a) < position[e].get(b));
      if (before.some((x) => x !== before[0])) conflicts.push([a, b]);
    }
  }

  // Load-time needs from shared files on unshared ones.
  const blocking = {};
  for (const editor of EDITORS) {
    const found = new Map(); // "from -> to" -> how
    for (const l of mapOf(src, editor).links) {
      if (isShared.has(l.from) && !isShared.has(l.to))
        found.set(`${l.from} -> ${l.to}`, `reads ${l.key}`);
    }
    for (const [from, tos] of observedNeeds(src, webApps, editor)) {
      if (!isShared.has(from)) continue;
      for (const to of tos) {
        if (!isShared.has(to) && !found.has(`${from} -> ${to}`))
          found.set(`${from} -> ${to}`, "observed");
      }
    }
    blocking[editor] = [...found].map(([k, how]) => `${k} (${how})`);
  }

  // Names crossing sdk-all.js's scope between shared and unshared files.
  const analysed = new Map();
  const get = (f) => {
    if (!analysed.has(f))
      analysed.set(f, analyse(fs.readFileSync(path.join(src, f), "utf8"), acorn));
    return analysed.get(f);
  };
  const crossing = {};
  for (const editor of EDITORS) {
    const { all } = sections(src, editor);
    const declaredBy = new Map();
    for (const f of all) {
      for (const st of get(f).ast.body)
        for (const n of topNames(st)) declaredBy.set(n, f);
    }
    const names = new Set();
    for (const f of all) {
      for (const site of get(f).sites) {
        if (site.kind !== "read" || site.key.includes(".")) continue;
        const by = declaredBy.get(site.key);
        if (by && by !== f && isShared.has(by) !== isShared.has(f)) {
          names.add(
            `${site.key} ${isShared.has(by) ? "shared -> own" : "own -> shared"}`,
          );
        }
      }
    }
    crossing[editor] = [...names].sort();
  }

  return {
    shared,
    sharedBytes: bytes(shared),
    editorBytes: Object.fromEntries(EDITORS.map((e) => [e, bytes(orders[e])])),
    inMin: Object.fromEntries(
      EDITORS.map((e) => [e, shared.filter((f) => sections(src, e).min.has(f)).length]),
    ),
    conflicts,
    blocking,
    crossing,
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const src = process.env.LIBERA_SDKJS_SRC;
  const webApps = process.env.LIBERA_WEB_APPS;
  if (!src || !webApps)
    throw new Error("LIBERA_SDKJS_SRC and LIBERA_WEB_APPS name the sources");
  const m = measure(src, webApps);
  const mb = (n) => `${(n / 1048576).toFixed(1)} MB`;
  const total = Object.values(m.editorBytes).reduce((a, b) => a + b, 0);
  console.log(
    `shared by all four editors: ${m.shared.length} files, ${mb(m.sharedBytes)} of source`,
  );
  for (const e of EDITORS) {
    console.log(
      `  ${e.padEnd(6)} ${mb(m.editorBytes[e])} in all; ${m.inMin[e]} of the shared files in sdk-all-min.js`,
    );
  }
  console.log(
    `  four editors: ${mb(total)}; with one shared copy: ${mb(total - 3 * m.sharedBytes)}`,
  );
  console.log(
    `pairs of shared files the editors load in different orders: ${m.conflicts.length}`,
  );
  for (const [a, b] of m.conflicts.slice(0, 20)) console.log(`    ${a} / ${b}`);
  for (const e of EDITORS) {
    console.log(
      `${e}: shared files that need an unshared one while they load: ${m.blocking[e].length}`,
    );
    for (const b of m.blocking[e].slice(0, 30)) console.log(`    ${b}`);
  }
  for (const e of EDITORS) {
    console.log(`${e}: names crossing sdk-all.js's scope: ${m.crossing[e].length}`);
    for (const c of m.crossing[e].slice(0, 12)) console.log(`    ${c}`);
  }
}
