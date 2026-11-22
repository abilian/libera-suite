// E4's codemod: a package of the engine's files made ES modules, mechanically.
//
// The package is a set of files closed under load-time needs (deps.mjs): the
// seeds below and everything they need while they load. Each file becomes a
// module in <sdkjs>/packages/<name>/src/, and the package is bundled by
// esbuild, the minifier upstream's build already runs, into one script that
// takes the place of the package's first file in every editor's configs. The
// rest of the engine stays concatenated as it is.
//
// Behaviour must not change, so each rule is the conservative one:
//
// - A file's wrapper, `(function(window, undefined){ ... })(window)`, is
//   unwrapped: in a module, `window` is the global it was given anyway.
// - A namespace member is exported when one file, and only one in any editor,
//   defines it, once, while it loads, in a statement of its own. Its value is
//   taken into a module variable at that moment (`var AscCommon_X = ...;`), and
//   the assignment to the namespace stays: that is the facade, so the files
//   not converted, web-apps, plugins and x2t see what they saw.
// - A read of an exported member is replaced by an import, when the file that
//   defines it comes earlier. Each module then imports only from modules before
//   it, and the bundle evaluates them in today's order. Every other read stays
//   a namespace read: a member several files define, or one defined later.
// - A name a file declares at its top level was a global, and a module keeps
//   it to itself: it is put back on `window` as the file ends, and exported.
// - sdk-all.js is one function, so a top-level `var` of one of its files is
//   a variable every other file of that bundle sees, and no global. A package
//   file that reads one (`g_fontApplication`, `fontslot_ASCII`), once moved
//   out, would not see it: the file that declares it also puts it on
//   `window`, right after, provided nothing assigns it again, which would
//   leave the copy stale. Anything else is refused.
//
// `node codemod.mjs` with LIBERA_SDKJS_SRC, the sources to convert in place
// (the experiments tree, never a release tree). It prints what it did.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { analyse, EDITORS, filesOf, mapOf } from "./deps.mjs";
import { observedNeeds } from "./deps-observed.mjs";

export const PACKAGE = "core";
export const SEEDS = [
  "common/libfont/",
  "common/bidi/",
  "common/commonDefines.js",
  "common/editorscommon.js",
];
export const BUNDLE = `packages/${PACKAGE}/dist/${PACKAGE}.js`;

/** The package's files, in load order: the seeds and what they need while
 * they load, which a package must hold. Needs as the sources say them
 * (deps.mjs) and as the engine shows them running (deps-observed.mjs), in
 * every editor: the static map does not follow a call made while a file
 * loads, and `new CTextMeasurer()` in textmeasurer.js needs, through its
 * constructor, a file the map alone left out. */
export function packageFiles(src, webApps) {
  const map = mapOf(src, "word");
  const needs = new Map();
  const add = (file, more) => {
    if (!needs.has(file)) needs.set(file, new Set());
    for (const f of more) needs.get(file).add(f);
  };
  for (const editor of EDITORS) {
    for (const l of (editor === "word" ? map : mapOf(src, editor)).layers)
      add(l.file, l.needs);
    for (const [file, seen] of observedNeeds(src, webApps, editor)) add(file, seen);
  }
  const seeds = map.files.filter((f) => SEEDS.some((s) => f === s || f.startsWith(s)));
  const held = new Set();
  const stack = [...seeds];
  while (stack.length) {
    const f = stack.pop();
    if (held.has(f)) continue;
    held.add(f);
    stack.push(...needs.get(f));
  }
  return map.files.filter((f) => held.has(f));
}

const exportName = (key) => key.replace(/\./g, "_").replace(/[^\w$]/g, "$");

/** The one wrapper a file is, or null. */
function wrapperOf(ast) {
  const calls = ast.body.filter(
    (s) => s.type === "ExpressionStatement" && s.expression.type === "CallExpression",
  );
  if (calls.length !== 1) return null;
  const call = calls[0].expression;
  const fn = call.callee;
  if (fn.type !== "FunctionExpression") return null;
  return { statement: calls[0], call, fn };
}

function hasTopLevelReturn(body) {
  const walk = (node) => {
    if (!node || typeof node.type !== "string") return false;
    if (node.type === "ReturnStatement") return true;
    if (/Function/.test(node.type) || node.type === "ClassBody") return false;
    return Object.values(node).some((v) =>
      Array.isArray(v) ? v.some(walk) : v && typeof v.type === "string" && walk(v),
    );
  };
  return body.some(walk);
}

export function plan(src, webApps) {
  const acorn = createRequire(path.join(src, "build", "package.json"))("acorn");
  const files = packageFiles(src, webApps);
  const order = new Map(files.map((f, i) => [f, i]));
  // Every file of every editor, for who defines what.
  const analysed = new Map();
  const definers = new Map();
  for (const editor of EDITORS) {
    for (const abs of filesOf(src, editor)) {
      const rel = path.relative(src, abs);
      if (analysed.has(rel)) continue;
      const a = analyse(fs.readFileSync(abs, "utf8"), acorn);
      analysed.set(rel, a);
      for (const key of a.defines) {
        if (!definers.has(key)) definers.set(key, new Set());
        definers.get(key).add(rel);
      }
    }
  }
  // What each package file exports: members it alone defines, once, while
  // it loads, in a statement of its own directly in its wrapper's body.
  const exported = new Map(); // key -> file
  const refused = { shared: 0, runtime: 0, shape: 0 };
  for (const file of files) {
    const a = analysed.get(file);
    const wrapper = wrapperOf(a.ast);
    const statements = new Set(wrapper ? wrapper.fn.body.body : []);
    const byKey = new Map();
    for (const site of a.sites.filter(
      (s) => s.kind === "define" && s.key.includes("."),
    )) {
      if (!byKey.has(site.key)) byKey.set(site.key, []);
      byKey.get(site.key).push(site);
    }
    for (const [key, sites] of byKey) {
      if (definers.get(key).size > 1) refused.shared++;
      else if (sites.some((site) => !site.load)) refused.runtime++;
      else {
        // One statement of the wrapper's body, `Ns.m = value;` or the chain
        // `Ns['m'] = Ns.m = value;`, every target this member.
        const statement =
          [...statements].find(
            (s) =>
              s.type === "ExpressionStatement" && s.expression === sites[0].assignment,
          ) ??
          [...statements].find(
            (s) =>
              s.type === "ExpressionStatement" &&
              chainOf(s.expression).includes(sites[0].assignment),
          );
        const chain = statement ? chainOf(statement.expression) : [];
        const same =
          chain.length === sites.length &&
          sites.every((site) => chain.includes(site.assignment));
        if (!statement || !same || chain.some((x) => x.operator !== "="))
          refused.shape++;
        else exported.set(key, { file, statement, chain });
      }
    }
  }
  // Top-level names, which were globals.
  const topLevel = new Map(); // name -> file
  for (const file of files) {
    for (const name of analysed.get(file).defines) {
      if (
        !name.includes(".") &&
        !/^Asc/.test(name) &&
        analysed.get(file).ast.body.some((s) => declares(s, name))
      ) {
        topLevel.set(name, file);
      }
    }
  }
  // Names the package reads from sdk-all.js's shared scope.
  const configs = createRequire(path.join(src, "build", "package.json"))(
    path.join(src, "build", "lib", "sdk-configs.cjs"),
  );
  const inAll = new Set();
  for (const editor of EDITORS) {
    const sdk = configs.loadAllConfigs(src, [])[editor].sdk;
    for (const f of configs.expandGlobs(configs.getFilesAll(sdk, "desktop")))
      inAll.add(path.relative(src, f));
  }
  const declared = new Map(); // name -> files declaring it at their top level, in sdk-all.js
  for (const [file, a] of analysed) {
    if (order.has(file) || !inAll.has(file)) continue;
    for (const statement of a.ast.body) {
      for (const name of topNames(statement)) {
        if (!declared.has(name)) declared.set(name, new Set());
        declared.get(name).add(file);
      }
    }
  }
  const scoped = new Map(); // name -> files declaring it
  for (const file of files) {
    for (const site of analysed.get(file).sites) {
      if (site.kind === "read" && !site.key.includes(".") && declared.has(site.key)) {
        scoped.set(site.key, declared.get(site.key));
      }
    }
  }
  for (const [name, declarers] of scoped) {
    const assigners = [...(definers.get(name) ?? [])].filter((f) => !declarers.has(f));
    const reassigned = [...declarers].some((f) =>
      analysed
        .get(f)
        .sites.some((x) => x.kind === "define" && x.key === name && x.assignment),
    );
    if (assigners.length || reassigned) {
      throw new Error(
        `${name} is assigned after it is declared, and a copy on window would go stale`,
      );
    }
  }
  return { files, order, analysed, definers, exported, topLevel, refused, scoped };
}

function topNames(statement) {
  if (
    (statement.type === "FunctionDeclaration" ||
      statement.type === "ClassDeclaration") &&
    statement.id
  ) {
    return [statement.id.name];
  }
  if (statement.type === "VariableDeclaration") {
    return statement.declarations
      .filter((d) => d.id.type === "Identifier")
      .map((d) => d.id.name);
  }
  return [];
}

/** The files outside the package that declare a name it reads from
 * sdk-all.js's scope, each putting it on window after its declaration. */
export function exposeScoped(src, p) {
  const byFile = new Map();
  for (const [name, files] of p.scoped) {
    for (const file of files) {
      if (!byFile.has(file)) byFile.set(file, []);
      byFile.get(file).push(name);
    }
  }
  for (const [file, names] of byFile) {
    const text = fs.readFileSync(path.join(src, file), "utf8");
    const edits = p.analysed
      .get(file)
      .ast.body.filter((st) => topNames(st).some((n) => names.includes(n)))
      .map((st) => ({
        at: st.end,
        text: topNames(st)
          .filter((n) => names.includes(n))
          .map(
            (n) =>
              `\nwindow[${JSON.stringify(n)}] = ${n}; // for the ${PACKAGE} package (E4)`,
          )
          .join(""),
      }))
      .sort((a, b) => b.at - a.at);
    let out = text;
    for (const e of edits) out = out.slice(0, e.at) + e.text + out.slice(e.at);
    fs.writeFileSync(path.join(src, file), out);
  }
  return byFile;
}

/** `a = b = c = value`: the assignments, outermost first. */
function chainOf(expression) {
  const chain = [];
  for (let x = expression; x?.type === "AssignmentExpression"; x = x.right)
    chain.push(x);
  return chain;
}

function declares(statement, name) {
  if (
    statement.type === "FunctionDeclaration" ||
    statement.type === "ClassDeclaration"
  ) {
    return statement.id?.name === name;
  }
  if (statement.type === "VariableDeclaration") {
    return statement.declarations.some(
      (d) => d.id.type === "Identifier" && d.id.name === name,
    );
  }
  return false;
}

/** One file, converted: its module text and what was done to it. */
export function convert(p, file) {
  const a = p.analysed.get(file);
  const text = a.code;
  const edits = [];
  const imports = new Map(); // from file -> Map(export name -> local)
  const stats = { file, imported: 0, keptNamespace: 0, exported: 0, facade: 0 };
  const wrapper = wrapperOf(a.ast);
  if (wrapper) {
    if (hasTopLevelReturn(wrapper.fn.body.body))
      throw new Error(`${file}: its wrapper returns early`);
    const bind = wrapper.fn.params
      .map((param, i) => {
        const arg = wrapper.call.arguments[i];
        if (param.type !== "Identifier")
          throw new Error(`${file}: a wrapper parameter is a pattern`);
        if (!arg) return param.name === "undefined" ? "" : `var ${param.name};`;
        if (arg.type === "Identifier" && arg.name === param.name) return "";
        return `var ${param.name} = ${text.slice(arg.start, arg.end)};`;
      })
      .join(" ");
    edits.push({
      start: wrapper.statement.start,
      end: wrapper.fn.body.start + 1,
      text: bind,
    });
    edits.push({
      start: wrapper.fn.body.end - 1,
      end: wrapper.statement.end,
      text: "",
    });
  }
  const words = new Set(text.match(/[A-Za-z_$][\w$]*/g));
  const localName = (key) => {
    let name = exportName(key);
    while (words.has(name)) name = `${name}$`;
    return name;
  };
  const exports = [];
  for (const site of a.sites) {
    if (site.kind === "define" && p.exported.get(site.key)?.file === file) {
      // `Ns.m = <value>;` becomes `var Ns_m = <value>; Ns.m = Ns_m;`, and a
      // chain the same: the value stays where it is, so edits inside it apply.
      const { statement, chain } = p.exported.get(site.key);
      if (site.assignment !== chain[0]) continue; // the chain's other targets
      const value = chain.at(-1).right;
      const name = localName(site.key);
      const targets = text.slice(chain[0].start, value.start);
      edits.push({ start: chain[0].start, end: value.start, text: `var ${name} = ` });
      edits.push({
        start: statement.end,
        end: statement.end,
        text: `\n\t${targets}${name};`,
      });
      exports.push(`${name} as ${exportName(site.key)}`);
      stats.exported++;
    } else if (site.kind === "read" && site.key.includes(".")) {
      const from = p.exported.get(site.key)?.file;
      if (!from || from === file || p.order.get(from) >= p.order.get(file)) {
        // A member another package file defines, read the old way.
        const others = [...(p.definers.get(site.key) ?? [])].filter((f) => f !== file);
        if (others.some((f) => p.order.has(f))) stats.keptNamespace++;
        continue;
      }
      if (!imports.has(from)) imports.set(from, new Map());
      const local = imports.get(from).get(exportName(site.key)) ?? localName(site.key);
      imports.get(from).set(exportName(site.key), local);
      edits.push({ start: site.start, end: site.end, text: local });
      stats.imported++;
    }
  }
  // Top-level declarations: back on window, and exported.
  const mine = [...p.topLevel].filter(([, f]) => f === file).map(([n]) => n);
  if (mine.length) {
    edits.push({
      start: text.length,
      end: text.length,
      text: `\n${mine.map((n) => `window[${JSON.stringify(n)}] = ${n};`).join("\n")}\n`,
    });
    exports.push(...mine);
    stats.facade = mine.length;
  }
  // Bare reads of another package file's top-level names, imported too.
  for (const site of a.sites) {
    if (site.kind !== "read" || site.key.includes(".")) continue;
    const from = p.topLevel.get(site.key);
    if (!from || from === file || p.order.get(from) >= p.order.get(file)) continue;
    if (!imports.has(from)) imports.set(from, new Map());
    if (!imports.get(from).has(site.key)) stats.imported++;
    imports.get(from).set(site.key, site.key);
  }
  edits.sort((x, y) => y.start - x.start || y.end - x.end);
  let out = text;
  for (let i = 0; i < edits.length; i++) {
    const e = edits[i];
    if (i && e.end > edits[i - 1].start && e.start !== e.end)
      throw new Error(`${file}: overlapping edits at ${e.start}`);
    out = out.slice(0, e.start) + e.text + out.slice(e.end);
  }
  const head = [...imports]
    .map(([from, names]) => {
      const spec = [...names]
        .map(([n, l]) => (n === l ? n : `${n} as ${l}`))
        .join(", ");
      return `import { ${spec} } from ${JSON.stringify(path.relative(path.dirname(file), from).replace(/^(?!\.)/, "./"))};`;
    })
    .join("\n");
  const tail = exports.length ? `\nexport { ${exports.join(", ")} };\n` : "";
  return { text: `${head}${head ? "\n" : ""}${out}${tail}`, stats };
}

/** The configs with the package's files out, and its bundle where its first
 * file was. */
export function reconfigure(src, files) {
  const held = new Set(files);
  for (const editor of EDITORS) {
    const file = path.join(src, "configs", `${editor}.json`);
    const config = JSON.parse(fs.readFileSync(file, "utf8"));
    const lists = (o) =>
      Object.values(o).flatMap((v) =>
        Array.isArray(v) ? [v] : v && typeof v === "object" ? lists(v) : [],
      );
    for (const list of lists(config.sdk)) {
      const at = list.findIndex((f) => held.has(f));
      const first = at >= 0 && list[at] === files[0];
      for (let i = list.length - 1; i >= 0; i--)
        if (held.has(list[i])) list.splice(i, 1);
      if (first) list.splice(at, 0, BUNDLE);
    }
    fs.writeFileSync(file, `${JSON.stringify(config, null, 2)}\n`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const src = process.env.LIBERA_SDKJS_SRC;
  if (!src) throw new Error("LIBERA_SDKJS_SRC names the sources to convert");
  // From the sources as fetched: the configs restored, the last output gone,
  // so a second run converts what the first did.
  execFileSync("git", ["-C", src, "checkout", "--", "."]);
  fs.rmSync(path.join(src, "packages", PACKAGE), { recursive: true, force: true });
  const webApps = process.env.LIBERA_WEB_APPS;
  if (!webApps)
    throw new Error(
      "LIBERA_WEB_APPS names web-apps, for xregexp, which the engine loads first",
    );
  const p = plan(src, webApps);
  const acorn = createRequire(path.join(src, "build", "package.json"))("acorn");
  const out = path.join(src, "packages", PACKAGE, "src");
  const totals = {
    imported: 0,
    keptNamespace: 0,
    exported: 0,
    facade: 0,
    linesIn: 0,
    linesOut: 0,
  };
  for (const file of p.files) {
    p.analysed.get(file).code = fs.readFileSync(path.join(src, file), "utf8");
    const { text, stats } = convert(p, file);
    acorn.parse(text, { ecmaVersion: "latest", sourceType: "module" }); // a module, or it throws
    fs.mkdirSync(path.dirname(path.join(out, file)), { recursive: true });
    fs.writeFileSync(path.join(out, file), text);
    for (const k of ["imported", "keptNamespace", "exported", "facade"])
      totals[k] += stats[k];
    totals.linesIn += p.analysed.get(file).code.split("\n").length;
    console.log(
      `  ${file.padEnd(44)} imports ${String(stats.imported).padStart(4)}  kept ${String(stats.keptNamespace).padStart(3)}  exports ${String(stats.exported).padStart(4)}  on window ${stats.facade}`,
    );
  }
  fs.writeFileSync(
    path.join(out, "index.js"),
    `// The ${PACKAGE} package, in the order the configs loaded its files.\n${p.files.map((f) => `import "./${f}";`).join("\n")}\n`,
  );
  reconfigure(src, p.files);
  const exposed = exposeScoped(src, p);
  console.log(
    `${p.scoped.size} names read from sdk-all.js's scope, put on window by ${exposed.size} file(s): ${[...p.scoped.keys()].join(", ")}`,
  );
  // The bundle, by the esbuild upstream's build installs: one script, its
  // modules in one scope, ASCII as x2t needs (build/webpack.sdk.factory.mjs).
  const esbuild = createRequire(path.join(src, "build", "package.json"))("esbuild");
  const started = performance.now();
  esbuild.buildSync({
    entryPoints: [path.join(out, "index.js")],
    // Each module is labelled with its path from here: the package's, not
    // this machine's.
    absWorkingDir: out,
    bundle: true,
    format: "iife",
    target: "es2022",
    charset: "ascii",
    legalComments: "none",
    // Guarded `require(...)` calls for when the engine runs under Node: left
    // as calls, as they are today. A browser and x2t never reach them.
    external: ["xregexp", "sockjs", "socketio"],
    outfile: path.join(src, BUNDLE),
    logLevel: "warning",
  });
  // esbuild turns `require` into its own `__require`, a function even where
  // `require` is not, and `typeof require === 'function'` with it: a guard
  // that skipped in a browser and in x2t would call it, and throw. The
  // original `require` is put back, and the shim taken out.
  const bundled = path.join(src, BUNDLE);
  let code = fs.readFileSync(bundled, "utf8");
  code = code.replace(/^ {2}var __require = [\s\S]*?\n {2}\}\);\n/m, "");
  code = code.replaceAll("__require", "require");
  if (code.includes("__require"))
    throw new Error("the bundle still uses esbuild's require shim");
  fs.writeFileSync(bundled, code);
  console.log(
    `bundled: ${BUNDLE}, ${fs.statSync(path.join(src, BUNDLE)).size} bytes, in ${Math.round(performance.now() - started)} ms`,
  );
  console.log(
    `${p.files.length} files; ${totals.imported} reads became imports, ${totals.keptNamespace} stayed namespace reads; ${totals.exported} members exported, ${totals.facade} top-level names put back on window; not exported: ${p.refused.shared} defined by several files or twice, ${p.refused.runtime} defined only at run time, ${p.refused.shape} in a shape left alone`,
  );
}
