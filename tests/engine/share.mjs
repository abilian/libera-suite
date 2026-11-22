// E5's cut: one engine library the four editors share, built from the files
// they all load, the rest of each editor's engine as it was.
//
//   node share.mjs sources    the experiments tree's sources, before the build
//   node share.mjs payload    its payload, after it
//
// with LIBERA_SDKJS_SRC, LIBERA_WEB_APPS (for xregexp, which the engine runs
// first) and, for `payload`, LIBERA_PAYLOAD. Never a release tree.
//
// The shared files are those all four editors load, less those that need, as
// they load, a file an editor keeps (statically or as the engine runs them,
// deps.mjs and deps-observed.mjs), and what needs those: the shared bundle
// loads before every editor's own. Its order is the word processor's, checked
// against every editor's needs. It is the files concatenated with no wrapper,
// as upstream's develop mode loads them one by one, so their top-level names
// are globals, as the editors' own files, which used to share sdk-all.js's
// scope with them, need.
//
// What changes in the editors' own files, to keep behaviour:
// - a definition an editor's file made before a shared file overwrote it is
//   dead today, and would win once the shared files come first: it goes
//   (slide's and visio's page sizes, which word's Document.js overwrites);
// - a top-level name an editor's file declares in sdk-all.js and a shared file
//   reads was a variable of that bundle's scope: the file puts it on `window`
//   too, refused if anything assigns it again.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { analyse, EDITORS, filesOf, mapOf } from "./deps.mjs";
import { observedNeeds } from "./deps-observed.mjs";

export const BUNDLE = "common/sdk-shared.js";
const PAGES = [
  "documenteditor",
  "spreadsheeteditor",
  "presentationeditor",
  "visioeditor",
  "pdfeditor",
];

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

function configsOf(src) {
  return createRequire(path.join(src, "build", "package.json"))(
    path.join(src, "build", "lib", "sdk-configs.cjs"),
  );
}

export function plan(src, webApps) {
  const acorn = createRequire(path.join(src, "build", "package.json"))("acorn");
  const configs = configsOf(src);
  const rel = (files) => configs.expandGlobs(files).map((f) => path.relative(src, f));
  const orders = Object.fromEntries(
    EDITORS.map((e) => [e, filesOf(src, e).map((f) => path.relative(src, f))]),
  );
  const inAll = Object.fromEntries(
    EDITORS.map((e) => [
      e,
      new Set(
        rel(configs.getFilesAll(configs.loadAllConfigs(src, [])[e].sdk, "desktop")),
      ),
    ]),
  );
  const candidates = orders.word.filter((f) =>
    EDITORS.every((e) => orders[e].includes(f)),
  );

  // Every editor's load-time needs, static and observed.
  const needs = new Map();
  const add = (from, to) => {
    if (!needs.has(from)) needs.set(from, new Set());
    needs.get(from).add(to);
  };
  for (const editor of EDITORS) {
    for (const l of mapOf(src, editor).links) add(l.from, l.to);
    for (const [from, tos] of observedNeeds(src, webApps, editor))
      for (const to of tos) add(from, to);
  }
  const shared = new Set(candidates);
  for (let changed = true; changed; ) {
    changed = false;
    for (const f of [...shared]) {
      if ([...(needs.get(f) ?? [])].some((t) => !shared.has(t))) {
        shared.delete(f);
        changed = true;
      }
    }
  }
  const order = candidates.filter((f) => shared.has(f));
  const at = new Map(order.map((f, i) => [f, i]));
  const misordered = [];
  for (const f of order) {
    for (const t of needs.get(f) ?? [])
      if (at.get(t) > at.get(f)) misordered.push(`${f} needs ${t}`);
  }
  if (misordered.length)
    throw new Error(`the shared order breaks needs: ${misordered.join("; ")}`);

  const analysed = new Map();
  const get = (f) => {
    if (!analysed.has(f)) {
      const code = fs.readFileSync(path.join(src, f), "utf8");
      analysed.set(f, { code, ...analyse(code, acorn) });
    }
    return analysed.get(f);
  };

  // Definitions that lose today and would win: an editor's file defining a
  // member before a shared file does.
  const dead = new Map(); // file -> Set of keys
  for (const editor of EDITORS) {
    const o = orders[editor];
    for (let i = 0; i < o.length; i++) {
      if (shared.has(o[i])) continue;
      const mine = new Set(
        get(o[i])
          .sites.filter((s) => s.kind === "define" && s.load && s.key.includes("."))
          .map((s) => s.key),
      );
      for (let j = i + 1; j < o.length; j++) {
        if (!shared.has(o[j])) continue;
        for (const s of get(o[j]).sites) {
          if (s.kind === "define" && s.load && mine.has(s.key)) {
            if (!dead.has(o[i])) dead.set(o[i], new Set());
            dead.get(o[i]).add(s.key);
          }
        }
      }
    }
  }

  // Names shared files read from an editor file's top level in sdk-all.js.
  const expose = new Map(); // file -> Set of names
  for (const editor of EDITORS) {
    const declaredBy = new Map();
    for (const f of inAll[editor]) {
      if (shared.has(f)) continue;
      for (const st of get(f).ast.body)
        for (const n of topNames(st)) declaredBy.set(n, f);
    }
    for (const f of order) {
      // A name the file declares itself is its own, whoever else declares one;
      // so is one it assigns before it reads, a scratch variable some other
      // file happens to declare (`prot = CShape.prototype;`): it needs the
      // variable, not a value, and a shared file declaring it must exist.
      const own = new Set(get(f).ast.body.flatMap(topNames));
      for (const x of get(f).sites)
        if (x.kind === "define" && !x.key.includes(".")) own.add(x.key);
      for (const s of get(f).sites) {
        if (
          s.kind !== "read" ||
          s.key.includes(".") ||
          !declaredBy.has(s.key) ||
          own.has(s.key)
        )
          continue;
        const by = declaredBy.get(s.key);
        // `window.X = X` keeps the same value; any other assignment of the
        // name would leave a copy on window stale.
        const again = get(by).sites.some(
          (x) =>
            x.kind === "define" &&
            x.key === s.key &&
            x.assignment &&
            !(
              x.assignment.right.type === "Identifier" &&
              x.assignment.right.name === s.key
            ),
        );
        if (again) {
          throw new Error(
            `${s.key}, declared in ${by}, is assigned again: a copy on window would go stale`,
          );
        }
        if (!expose.has(by)) expose.set(by, new Set());
        expose.get(by).add(s.key);
      }
    }
  }

  // Every name a shared file assigns without declaring must be declared by
  // some shared file, or it is an assignment to nothing in strict code.
  const declaredShared = new Set(
    order.flatMap((f) => get(f).ast.body.flatMap(topNames)),
  );
  const undeclared = new Set();
  for (const f of order) {
    for (const x of get(f).sites) {
      const bare = x.assignment?.left.type === "Identifier";
      if (
        x.kind === "define" &&
        !x.key.includes(".") &&
        !declaredShared.has(x.key) &&
        bare
      ) {
        undeclared.add(`${x.key} (${f})`);
      }
    }
  }

  // Top-level names of shared files from sdk-all.js, which become globals:
  // a collision is another global of that name, declared by an editor's own
  // file outside sdk-all.js's function (in sdk-all-min.js), which would now
  // overwrite the shared file's. One inside it only shadows the global, as
  // it did. (`History`, a browser global, upstream's develop mode overwrites
  // already.)
  const sharedAll = order.filter((f) => EDITORS.some((e) => inAll[e].has(f)));
  const declaredElsewhere = new Map();
  for (const editor of EDITORS) {
    for (const f of orders[editor]) {
      if (shared.has(f) || inAll[editor].has(f)) continue;
      for (const st of get(f).ast.body)
        for (const n of topNames(st)) declaredElsewhere.set(n, f);
    }
  }
  const collisions = [];
  for (const f of sharedAll) {
    for (const st of get(f).ast.body) {
      for (const n of topNames(st))
        if (declaredElsewhere.has(n))
          collisions.push(`${n}: ${f} and ${declaredElsewhere.get(n)}`);
    }
  }

  return {
    candidates,
    order,
    shared,
    dead,
    expose,
    collisions,
    undeclared,
    get,
    orders,
  };
}

function applyToSources(src, p) {
  // The configs without the shared files.
  for (const editor of EDITORS) {
    const file = path.join(src, "configs", `${editor}.json`);
    const config = JSON.parse(fs.readFileSync(file, "utf8"));
    const lists = (o) =>
      Object.values(o).flatMap((v) =>
        Array.isArray(v) ? [v] : v && typeof v === "object" ? lists(v) : [],
      );
    for (const list of lists(config.sdk)) {
      for (let i = list.length - 1; i >= 0; i--)
        if (p.shared.has(list[i])) list.splice(i, 1);
    }
    fs.writeFileSync(file, `${JSON.stringify(config, null, 2)}\n`);
  }
  // editorscommon.js loads the editor's sdk-all.js from the folder of the
  // script it ran in, which was the editor's sdk-all-min.js and is now the
  // shared library, in common/: the same URL, named from there.
  if (p.shared.has("common/editorscommon.js")) {
    const file = path.join(src, "common/editorscommon.js");
    const text = fs.readFileSync(file, "utf8");
    const from = "loadScript(scriptDirectory + 'sdk-all.js', onSuccess, onError);";
    if (text.split(from).length !== 2)
      throw new Error("editorscommon.js: loadSdk is not as expected");
    fs.writeFileSync(
      file,
      text.replace(
        from,
        "loadScript(scriptDirectory + '../' + sdkName + '/sdk-all.js', onSuccess, onError); // E5: from common/",
      ),
    );
  }
  // The editors' own files: dead definitions out, names exposed.
  const files = new Set([...p.dead.keys(), ...p.expose.keys()]);
  let changed = 0;
  for (const file of files) {
    const a = p.get(file);
    const edits = [];
    for (const key of p.dead.get(file) ?? []) {
      for (const s of a.sites.filter(
        (x) => x.kind === "define" && x.key === key && x.assignment,
      )) {
        const statement = findStatement(a.ast, s.assignment);
        if (!statement)
          throw new Error(`${file}: ${key} is not defined by a statement of its own`);
        edits.push({
          start: statement.start,
          end: statement.end,
          text: `/* E5: ${key} is set again by a shared file, which used to load after this one */`,
        });
      }
    }
    for (const name of p.expose.get(file) ?? []) {
      const statement = a.ast.body.find((st) => topNames(st).includes(name));
      edits.push({
        start: statement.end,
        end: statement.end,
        text: `\nwindow[${JSON.stringify(name)}] = ${name}; // read by the shared library (E5)`,
      });
    }
    edits.sort((x, y) => y.start - x.start);
    let out = a.code;
    for (const e of edits) out = out.slice(0, e.start) + e.text + out.slice(e.end);
    fs.writeFileSync(path.join(src, file), out);
    changed += edits.length;
  }
  return { files: files.size, changed };
}

function findStatement(ast, assignment) {
  let found = null;
  const walk = (node) => {
    if (found || !node || typeof node.type !== "string") return;
    if (node.type === "ExpressionStatement" && node.expression === assignment) {
      found = node;
      return;
    }
    for (const v of Object.values(node)) {
      if (Array.isArray(v)) v.forEach(walk);
      else if (v && typeof v.type === "string") walk(v);
    }
  };
  walk(ast);
  return found;
}

// The shared files, in their order: written by `sources`, which plans from
// the configs as fetched, read by `payload`, once they no longer list them.
const ORDER = "packages/shared/order.txt";

/** The shared bundle into the payload, and both loaders told of it. */
function applyToPayload(src, payload, order) {
  const esbuild = createRequire(path.join(src, "build", "package.json"))("esbuild");
  const text = order
    .map((f) => `${fs.readFileSync(path.join(src, f), "utf8")}\n;\n`)
    .join("");
  // Upstream minifies its desktop bundles this way: whitespace only, ASCII.
  const { code } = esbuild.transformSync(text, {
    minifyWhitespace: true,
    charset: "ascii",
    target: "es2022",
    legalComments: "none",
  });
  fs.writeFileSync(path.join(payload, "sdkjs", BUNDLE), code);
  // x2t: one more file, for every editor, after the ones it loads first.
  const config = path.join(payload, "bin", "DoctRenderer.config");
  const line = `<file>${path.join(payload, "sdkjs", BUNDLE)}</file>`;
  let xml = fs.readFileSync(config, "utf8");
  if (!xml.includes(line)) xml = xml.replace("<sdkjs>", `${line}\n<sdkjs>`);
  fs.writeFileSync(config, xml);
  // The browser: requirejs loads the shared library before the editor's.
  for (const page of PAGES) {
    const html = path.join(payload, "web-apps", "apps", page, "main", "index.html");
    if (!fs.existsSync(html)) continue;
    let s = fs.readFileSync(html, "utf8");
    if (!s.includes("sdkshared")) {
      s = s.replace(
        /(\n\s*)sdk:(\s*)"/,
        `$1sdkshared:$2"../../sdkjs/common/sdk-shared",$1sdk:$2"`,
      );
      if (/sdk: \{ deps: \[/.test(s)) {
        s = s.replace(
          /sdk: \{ deps: \[("jquery"[^\]]*)\] \}/,
          `sdkshared: { deps: [$1] },\n                sdk: { deps: ["sdkshared"] }`,
        );
      } else {
        // Visio's page declares no dependencies for its engine at all: the
        // shared library is given the ones the other editors' pages name.
        s = s.replace(
          /(\n\s*)callback:/,
          `$1shim: {$1    sdkshared: { deps: ["jquery", "allfonts", "xregexp", "socketio"] },$1    sdk: { deps: ["sdkshared"] }$1},$1callback:`,
        );
      }
      if (!s.includes('sdk: { deps: ["sdkshared"] }'))
        throw new Error(`${html}: no requirejs config found to change`);
      fs.writeFileSync(html, s);
    }
  }
  return fs.statSync(path.join(payload, "sdkjs", BUNDLE)).size;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const src = process.env.LIBERA_SDKJS_SRC;
  const webApps = process.env.LIBERA_WEB_APPS;
  if (!src || !webApps)
    throw new Error("LIBERA_SDKJS_SRC and LIBERA_WEB_APPS name the sources");
  const step = process.argv[2];
  if (step === "sources") {
    execFileSync("git", ["-C", src, "checkout", "--", "."]);
    fs.rmSync(path.join(src, "packages"), { recursive: true, force: true });
  }
  const mb = (n) => `${(n / 1048576).toFixed(1)} MB`;
  if (step === "payload") {
    const payload = process.env.LIBERA_PAYLOAD;
    if (!payload) throw new Error("LIBERA_PAYLOAD names the payload to change");
    const order = fs
      .readFileSync(path.join(src, ORDER), "utf8")
      .split("\n")
      .filter(Boolean);
    console.log(
      `payload: ${BUNDLE}, ${order.length} files, ${mb(applyToPayload(src, payload, order))}; x2t's config and the editors' pages load it first`,
    );
    process.exit(0);
  }
  const p = plan(src, webApps);
  const size = p.order.reduce((a, f) => a + fs.statSync(path.join(src, f)).size, 0);
  console.log(
    `shared: ${p.order.length} of the ${p.candidates.length} files all four editors load, ${mb(size)} of source; left to the editors, as they need an editor's own file while they load: ${p.candidates.length - p.order.length}`,
  );
  console.log(
    `dead definitions removed: ${[...p.dead].map(([f, k]) => `${f} (${k.size})`).join(", ") || "none"}`,
  );
  console.log(
    `names put on window: ${[...p.expose].map(([f, n]) => `${f}: ${[...n].join(", ")}`).join("; ") || "none"}`,
  );
  console.log(
    `names shared files assign that no shared file declares: ${[...p.undeclared].join(", ") || "none"}`,
  );
  console.log(
    `top-level names that become globals and collide: ${p.collisions.length}`,
  );
  for (const c of p.collisions.slice(0, 15)) console.log(`    ${c}`);
  if (step === "sources") {
    const done = applyToSources(src, p);
    fs.mkdirSync(path.dirname(path.join(src, ORDER)), { recursive: true });
    fs.writeFileSync(path.join(src, ORDER), `${p.order.join("\n")}\n`);
    console.log(
      `sources: configs without the shared files; ${done.changed} edits in ${done.files} editor files`,
    );
  }
}
