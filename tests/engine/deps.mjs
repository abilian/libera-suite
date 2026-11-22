// The engine's dependency map: which file needs which while it loads.
//
// Each editor's engine is its files concatenated in the order sdkjs's configs
// give them (configs/<editor>.json, read by build/lib/sdk-configs.cjs, which
// is what upstream's webpack loader reads). A file needs another while it
// loads when the code that runs as it is evaluated (its top level and the
// bodies of the functions it calls on the spot, which is how nearly every
// file is wrapped) reads a name the other defines: a namespace member
// (`AscFormat.CShape`, `window['AscCommon'].g_oTableId`) or a global. Reads
// inside other function bodies happen later, once everything has loaded, and
// ES modules' live bindings make cycles among them harmless; the load-time
// ones decide whether imports can be generated (report, "The dependency
// graph", and E4).
//
// From the links: their cycles (the knot, which no order satisfies), the
// reads of a name only a later file defines (forward reads, undefined when
// they run), and the layers the graph suggests. `node deps.mjs EDITOR...`
// prints a report; deps.test.mjs holds the knot and the forward reads to the
// numbers in deps-limits.json, which may only fall.
//
// Reads LIBERA_SDKJS_SRC, the sdkjs sources, and parses them with the acorn
// sdkjs's own build installs (build/node_modules), so nothing is added here.
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const EDITORS = ["word", "cell", "slide", "visio"];
const NAMESPACE = /^Asc/;

function sdkRequire(src) {
  return createRequire(path.join(src, "build", "package.json"));
}

/** The editor's files, in load order: sdk-all-min.js's, then sdk-all.js's,
 * as the desktop build has them, each once; and before them the files of the
 * library the four editors share, where the sources have been cut for one
 * (E5, share.mjs: packages/shared/order.txt), which loads first. */
export function filesOf(src, editor) {
  const configs = sdkRequire(src)(path.join(src, "build", "lib", "sdk-configs.cjs"));
  const sdk = configs.loadAllConfigs(src, [])[editor].sdk;
  const order = path.join(src, "packages", "shared", "order.txt");
  const shared = fs.existsSync(order)
    ? fs
        .readFileSync(order, "utf8")
        .split("\n")
        .filter(Boolean)
        .map((f) => path.join(src, f))
    : [];
  const listed = [
    ...shared,
    ...configs.expandGlobs(configs.getFilesMin(sdk, "desktop")),
    ...configs.expandGlobs(configs.getFilesAll(sdk, "desktop")),
  ];
  return [...new Set(listed)];
}

// --- scopes ------------------------------------------------------------------

class Scope {
  constructor(parent, program = false, thisIsWindow = program) {
    this.parent = parent;
    this.program = program;
    // `this` is window at the top level, and in a function called there on
    // the spot, plainly or with .call(this); in any other function it is
    // whatever the call makes it, and `this.x = ...` in a constructor is no
    // global.
    this.thisIsWindow = thisIsWindow;
    this.names = new Map(); // name -> {ns} for a namespace alias, {window} for window, {}
  }
  declare(name, what = {}) {
    if (!this.names.has(name) || what.ns || what.window) this.names.set(name, what);
  }
  /** What `name` is here: null for a global, else its binding. A name the
   * program scope declares is a global too: in a script it is one. */
  lookup(name) {
    for (let s = this; s; s = s.parent) {
      if (s.names.has(name)) return s.program ? null : s.names.get(name);
    }
    return null;
  }
}

function patternNames(node, out = []) {
  if (!node) return out;
  switch (node.type) {
    case "Identifier":
      out.push(node.name);
      break;
    case "ObjectPattern":
      for (const p of node.properties)
        patternNames(p.type === "RestElement" ? p.argument : p.value, out);
      break;
    case "ArrayPattern":
      for (const e of node.elements) patternNames(e, out);
      break;
    case "AssignmentPattern":
      patternNames(node.left, out);
      break;
    case "RestElement":
      patternNames(node.argument, out);
      break;
  }
  return out;
}

const FUNCTION = new Set([
  "FunctionDeclaration",
  "FunctionExpression",
  "ArrowFunctionExpression",
]);

/** Every name a function body (or the program) declares, without entering
 * nested functions: var and function hoist there, and let, const and class
 * are counted there too, which is close enough for what this asks. */
function hoisted(body, out = []) {
  const walk = (node) => {
    if (!node || typeof node.type !== "string") return;
    if (node.type === "VariableDeclaration") {
      for (const d of node.declarations) patternNames(d.id, out);
    } else if (
      node.type === "FunctionDeclaration" ||
      node.type === "ClassDeclaration"
    ) {
      if (node.id) out.push(node.id.name);
      if (node.type === "FunctionDeclaration") return;
    } else if (FUNCTION.has(node.type)) {
      return;
    }
    for (const key of Object.keys(node)) {
      const v = node[key];
      if (Array.isArray(v)) v.forEach(walk);
      else if (v && typeof v.type === "string" && key !== "id") walk(v);
    }
  };
  (Array.isArray(body) ? body : [body]).forEach(walk);
  return out;
}

// --- one file --------------------------------------------------------------

function staticName(member) {
  if (!member.computed)
    return member.property.type === "Identifier" ? member.property.name : null;
  const p = member.property;
  return p.type === "Literal" && typeof p.value === "string" ? p.value : null;
}

/** What one file defines and reads. Keys are `Ns.member` for a namespace's
 * member and `name` for a global. `sites` places each read and definition in
 * the text, for the codemod (codemod.mjs): {kind, key, start, end, load}, and
 * for a definition made by `=`, the assignment. */
export function analyse(code, acorn) {
  const ast = acorn.parse(code, {
    ecmaVersion: "latest",
    sourceType: "script",
    allowReturnOutsideFunction: true,
    allowHashBang: true,
  });
  const defines = new Set();
  const sites = [];
  const loadReads = new Set();
  const laterReads = new Set();
  const program = new Scope(null, true, true);
  for (const name of hoisted(ast.body)) {
    program.declare(name);
    defines.add(name);
  }

  const isWindow = (node, scope) => {
    if (node.type === "ThisExpression") return scope.thisIsWindow;
    if (node.type !== "Identifier") return false;
    if (node.name === "window" || node.name === "self" || node.name === "globalThis") {
      const b = scope.lookup(node.name);
      return b === null || Boolean(b.window);
    }
    return Boolean(scope.lookup(node.name)?.window);
  };
  // The namespace an expression is, or null.
  const nsOf = (node, scope) => {
    if (!node) return null;
    if (node.type === "Identifier") {
      const b = scope.lookup(node.name);
      if (b) return b.ns ?? null;
      return NAMESPACE.test(node.name) ? node.name : null;
    }
    if (node.type === "MemberExpression" && isWindow(node.object, scope)) {
      const name = staticName(node);
      return name && NAMESPACE.test(name) ? name : null;
    }
    if (node.type === "AssignmentExpression" || node.type === "LogicalExpression") {
      return nsOf(node.left, scope) ?? nsOf(node.right, scope);
    }
    return null;
  };
  // The key a member expression names, or null: `Ns.member`, or a global
  // written as `window.name`.
  const keyOf = (member, scope) => {
    const name = staticName(member);
    if (!name) return null;
    const ns = nsOf(member.object, scope);
    if (ns) return `${ns}.${name}`;
    if (isWindow(member.object, scope)) return name;
    return null;
  };

  const read = (key, load, node) => {
    if (NAMESPACE.test(key) && !key.includes(".")) return; // a namespace object
    (load ? loadReads : laterReads).add(key);
    sites.push({ kind: "read", key, start: node.start, end: node.end, load });
  };
  const define = (key, node, load, assignment = null) => {
    defines.add(key);
    sites.push({
      kind: "define",
      key,
      start: node.start,
      end: node.end,
      load,
      assignment,
    });
  };

  const enterFunction = (fn, scope, args, load, thisIsWindow = false) => {
    const arrow = fn.type === "ArrowFunctionExpression";
    const inner = new Scope(scope, false, arrow ? scope.thisIsWindow : thisIsWindow);
    fn.params.forEach((param, i) => {
      for (const name of patternNames(param)) {
        const arg = args?.[i];
        if (arg && param.type === "Identifier" && isWindow(arg, scope))
          inner.declare(name, { window: true });
        else if (arg && param.type === "Identifier" && nsOf(arg, scope))
          inner.declare(name, { ns: nsOf(arg, scope) });
        else inner.declare(name);
      }
    });
    if (fn.type !== "ArrowFunctionExpression") inner.declare("arguments");
    if (fn.type === "FunctionExpression" && fn.id) inner.declare(fn.id.name);
    const body = fn.body.type === "BlockStatement" ? fn.body.body : fn.body;
    for (const name of hoisted(body)) inner.declare(name);
    for (const p of fn.params) visitPattern(p, inner, false);
    visit(fn.body, inner, load);
  };

  // Default values in a pattern are read when the binding is made.
  const visitPattern = (node, scope, load) => {
    if (!node) return;
    if (node.type === "AssignmentPattern") visit(node.right, scope, load);
    else if (node.type === "ObjectPattern") {
      for (const p of node.properties) {
        if (p.type === "RestElement") visitPattern(p.argument, scope, load);
        else {
          if (p.computed) visit(p.key, scope, load);
          visitPattern(p.value, scope, load);
        }
      }
    } else if (node.type === "ArrayPattern")
      for (const e of node.elements) visitPattern(e, scope, load);
    else if (node.type === "RestElement") visitPattern(node.argument, scope, load);
  };

  const assignTarget = (target, scope, load, assignment = null) => {
    if (target.type === "Identifier") {
      if (scope.lookup(target.name) === null)
        define(target.name, target, load, assignment);
      return;
    }
    if (target.type === "MemberExpression") {
      const key = keyOf(target, scope);
      if (key) define(key, target, load, assignment);
      if (!nsOf(target.object, scope) && !isWindow(target.object, scope))
        visit(target.object, scope, load);
      if (target.computed) visit(target.property, scope, load);
      return;
    }
    visitPattern(target, scope, load);
    for (const name of patternNames(target)) {
      if (scope.lookup(name) === null) define(name, target, load);
    }
  };

  const visit = (node, scope, load) => {
    if (!node || typeof node.type !== "string") return;
    switch (node.type) {
      case "Identifier": {
        if (
          scope.lookup(node.name) === null &&
          !["undefined", "window", "self", "globalThis"].includes(node.name)
        )
          read(node.name, load, node);
        return;
      }
      case "MemberExpression": {
        const key = keyOf(node, scope);
        if (key) read(key, load, node);
        else visit(node.object, scope, load);
        if (node.computed) visit(node.property, scope, load);
        return;
      }
      case "BinaryExpression": {
        // `X !== undefined` and its kin test whether a name is there yet: a
        // file that asks expects it may not be, so it is not a need.
        const isUndefined = (n) =>
          (n.type === "Identifier" && n.name === "undefined") ||
          (n.type === "UnaryExpression" && n.operator === "void");
        if (["===", "!==", "==", "!="].includes(node.operator)) {
          if (
            isUndefined(node.left) &&
            ["Identifier", "MemberExpression"].includes(node.right.type)
          )
            return;
          if (
            isUndefined(node.right) &&
            ["Identifier", "MemberExpression"].includes(node.left.type)
          )
            return;
        }
        visit(node.left, scope, load);
        visit(node.right, scope, load);
        return;
      }
      case "UnaryExpression":
        // `typeof X` guards a name that may not be there: not a need.
        if (
          node.operator === "typeof" &&
          (node.argument.type === "Identifier" ||
            node.argument.type === "MemberExpression")
        )
          return;
        visit(node.argument, scope, load);
        return;
      case "AssignmentExpression":
        assignTarget(node.left, scope, load, node);
        if (node.operator !== "=" && node.left.type !== "Identifier") {
          const key =
            node.left.type === "MemberExpression" ? keyOf(node.left, scope) : null;
          if (key) read(key, load, node.left);
        }
        visit(node.right, scope, load);
        return;
      case "UpdateExpression":
        assignTarget(node.argument, scope, load);
        return;
      case "VariableDeclarator": {
        const ns = node.init ? nsOf(node.init, scope) : null;
        if (ns && node.id.type === "Identifier" && !scope.program)
          scope.declare(node.id.name, { ns });
        if (
          node.id.type === "Identifier" &&
          node.init &&
          isWindow(node.init, scope) &&
          !scope.program
        ) {
          scope.declare(node.id.name, { window: true });
        }
        visitPattern(node.id, scope, load);
        visit(node.init, scope, load);
        return;
      }
      case "CallExpression":
      case "NewExpression": {
        const callee = node.callee;
        if (FUNCTION.has(callee.type)) {
          for (const a of node.arguments) visit(a, scope, load);
          // Called plainly: `this` is window in sloppy code, as nearly every
          // wrapper is written; `new` makes it the new object.
          enterFunction(
            callee,
            scope,
            node.arguments,
            load,
            node.type === "CallExpression",
          );
          return;
        }
        // (function () {...}).call(this, ...)
        if (
          callee.type === "MemberExpression" &&
          FUNCTION.has(callee.object.type) &&
          ["call", "apply"].includes(staticName(callee))
        ) {
          for (const a of node.arguments) visit(a, scope, load);
          const self = node.arguments[0];
          enterFunction(
            callee.object,
            scope,
            staticName(callee) === "call" ? node.arguments.slice(1) : [],
            load,
            Boolean(self) && isWindow(self, scope),
          );
          return;
        }
        visit(callee, scope, load);
        for (const a of node.arguments) visit(a, scope, load);
        return;
      }
      case "FunctionDeclaration":
      case "FunctionExpression":
      case "ArrowFunctionExpression":
        enterFunction(node, scope, null, false);
        return;
      case "ClassDeclaration":
      case "ClassExpression":
        visit(node.superClass, scope, load);
        for (const m of node.body.body) {
          if (m.computed) visit(m.key, scope, load);
          if (m.type === "StaticBlock") for (const s of m.body) visit(s, scope, load);
          else if (m.type === "PropertyDefinition")
            visit(m.value, scope, load && m.static);
          else visit(m.value, scope, false);
        }
        return;
      case "Property":
        if (node.computed) visit(node.key, scope, load);
        visit(node.value, scope, load);
        return;
      case "LabeledStatement":
        visit(node.body, scope, load);
        return;
      case "BreakStatement":
      case "ContinueStatement":
        return;
      case "CatchClause": {
        const inner = new Scope(scope);
        for (const name of patternNames(node.param)) inner.declare(name);
        visit(node.body, inner, load);
        return;
      }
      default:
        for (const key of Object.keys(node)) {
          if (key === "type" || key === "start" || key === "end" || key === "loc")
            continue;
          const v = node[key];
          if (Array.isArray(v)) for (const c of v) visit(c, scope, load);
          else if (v && typeof v.type === "string") visit(v, scope, load);
        }
    }
  };
  for (const s of ast.body) visit(s, program, true);
  return { defines, loadReads, laterReads, sites, ast };
}

// --- the map ---------------------------------------------------------------

/** Tarjan's strongly connected components of `edges` (index -> Set). */
function components(n, edges) {
  let index = 0;
  const idx = new Array(n).fill(-1);
  const low = new Array(n).fill(0);
  const on = new Array(n).fill(false);
  const stack = [];
  const found = [];
  const strong = (v) => {
    // Iterative, as the graph is deep enough to overflow a recursion.
    const work = [[v, [...(edges[v] || [])], 0]];
    idx[v] = low[v] = index++;
    stack.push(v);
    on[v] = true;
    while (work.length) {
      const frame = work[work.length - 1];
      const [u, next] = frame;
      if (frame[2] < next.length) {
        const w = next[frame[2]++];
        if (idx[w] === -1) {
          idx[w] = low[w] = index++;
          stack.push(w);
          on[w] = true;
          work.push([w, [...(edges[w] || [])], 0]);
        } else if (on[w]) low[u] = Math.min(low[u], idx[w]);
      } else {
        work.pop();
        if (work.length)
          low[work[work.length - 1][0]] = Math.min(
            low[work[work.length - 1][0]],
            low[u],
          );
        if (low[u] === idx[u]) {
          const c = [];
          let w;
          do {
            w = stack.pop();
            on[w] = false;
            c.push(w);
          } while (w !== u);
          found.push(c);
        }
      }
    }
  };
  for (let v = 0; v < n; v++) if (idx[v] === -1) strong(v);
  return found;
}

export function mapOf(src, editor) {
  const acorn = sdkRequire(src)("acorn");
  const files = filesOf(src, editor);
  const parsed = files.map((f) => analyse(fs.readFileSync(f, "utf8"), acorn));
  const definers = new Map(); // key -> sorted indices of the files defining it
  parsed.forEach((p, i) => {
    for (const key of p.defines) {
      if (!definers.has(key)) definers.set(key, []);
      definers.get(key).push(i);
    }
  });
  const links = []; // {from, to, key}: `from` needs `to` while it loads
  const forward = [];
  const later = []; // runtime links, for the totals
  parsed.forEach((p, i) => {
    for (const key of p.loadReads) {
      const by = definers.get(key);
      if (!by || by.includes(i)) continue;
      const before = by.filter((j) => j < i);
      if (before.length) links.push({ from: i, to: before[before.length - 1], key });
      else {
        links.push({ from: i, to: by[0], key });
        forward.push({ from: i, to: by[0], key });
      }
    }
    for (const key of p.laterReads) {
      const by = definers.get(key);
      if (by && !by.includes(i)) later.push({ from: i, to: by[0], key });
    }
  });
  const edges = files.map(() => new Set());
  for (const l of links) edges[l.from].add(l.to);
  const cycles = components(files.length, edges).filter((c) => c.length > 1);
  const knot = cycles.reduce((a, c) => (c.length > a.length ? c : a), []);
  // Layers: 0 for a file that needs nothing while it loads, else one more
  // than the deepest file it needs; a cycle's files share their layer.
  const layer = new Array(files.length).fill(-1);
  const inCycle = new Map();
  cycles.forEach((c, n) => {
    for (const f of c) inCycle.set(f, n);
  });
  const depth = (f, seen = new Set()) => {
    if (layer[f] >= 0) return layer[f];
    if (seen.has(f)) return 0;
    seen.add(f);
    let d = 0;
    for (const t of edges[f]) {
      if (inCycle.has(f) && inCycle.get(t) === inCycle.get(f)) continue;
      d = Math.max(d, depth(t, seen) + 1);
    }
    layer[f] = d;
    return d;
  };
  for (let f = 0; f < files.length; f++) depth(f);
  const rel = (f) => path.relative(src, f);
  return {
    editor,
    files: files.map(rel),
    links: links.map((l) => ({
      from: rel(files[l.from]),
      to: rel(files[l.to]),
      key: l.key,
    })),
    later: later.length,
    forward: forward.map((l) => ({
      from: rel(files[l.from]),
      to: rel(files[l.to]),
      key: l.key,
    })),
    knot: knot.map((f) => rel(files[f])).sort(),
    cycles: cycles.length,
    layers: files.map((f, i) => ({
      file: rel(f),
      layer: layer[i],
      needs: [...edges[i]].map((t) => rel(files[t])),
    })),
  };
}

export function summary(map) {
  const fileLinks = new Set(map.links.map((l) => `${l.from}>${l.to}`)).size;
  const top = Math.max(...map.layers.map((l) => l.layer));
  const zero = map.layers.filter((l) => l.layer === 0).length;
  return [
    `${map.editor}: ${map.files.length} files`,
    `  load-time reads of another file's name: ${map.links.length} (${fileLinks} file-to-file links)`,
    `  reads that wait until later: ${map.later}`,
    `  the knot: ${map.knot.length} files (${map.cycles} cycle(s) in all)`,
    `  forward reads: ${map.forward.length}`,
    `  layers: 0 to ${top}; ${zero} files need nothing while they load`,
  ].join("\n");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const src = process.env.LIBERA_SDKJS_SRC;
  if (!src) throw new Error("LIBERA_SDKJS_SRC names the sdkjs sources");
  const asked = process.argv.slice(2).filter((a) => !a.startsWith("--"));
  for (const editor of asked.length ? asked : EDITORS) {
    const map = mapOf(src, editor);
    console.log(summary(map));
    if (process.argv.includes("--json")) {
      fs.writeFileSync(`deps-${editor}.json`, `${JSON.stringify(map, null, 1)}\n`);
    }
    if (process.argv.includes("--forward")) {
      for (const f of map.forward)
        console.log(`    ${f.key}: ${f.from} reads it, ${f.to} defines it`);
    }
  }
}
