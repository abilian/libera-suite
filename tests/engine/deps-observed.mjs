// The dependency map's forward reads, observed rather than inferred.
//
// deps.mjs reads the sources; this runs them. Each editor's files are loaded
// one by one in their order into a Node context, as upstream's test pages load
// them, and after each file every Asc* namespace on the global is replaced by
// a proxy that notes, with the file being loaded, each read of a member the
// namespace does not hold yet. A noted member that some later file defines is
// a forward read, observed: through the functions a file calls while it loads
// too, which the static map does not follow. Where the two disagree, this is
// the engine's own answer.
//
// `node deps-observed.mjs EDITOR...`, with LIBERA_SDKJS_SRC (the sources) and
// LIBERA_WEB_APPS (for xregexp, which the engine loads first).
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { analyse, EDITORS, filesOf } from "./deps.mjs";

const NAMESPACE = /^Asc/;

/** Each file run in turn, watched: the members read before they existed,
 * and the files each one needed while it loaded (the file that last wrote
 * each member it read, through any call). */
function observe(src, webApps, editor) {
  const engine = { native: undefined };
  engine.window = engine;
  vm.createContext(engine);
  for (const file of [
    path.join(src, "common/Native/native.js"),
    path.join(webApps, "vendor/xregexp/xregexp-all-min.js"),
  ]) {
    vm.runInContext(fs.readFileSync(file, "utf8"), engine, { filename: file });
  }
  const missing = []; // {file, key}
  const owners = new Map(); // "Ns.member" -> the file that last wrote it
  const needs = new Map(); // file -> Set of files
  const wrapped = new WeakSet();
  let current = null;
  const wrap = () => {
    for (const ns of Object.keys(engine).filter((k) => NAMESPACE.test(k))) {
      const target = engine[ns];
      if (!target || typeof target !== "object" || wrapped.has(target)) continue;
      const proxy = new Proxy(target, {
        get(t, key, receiver) {
          if (current && typeof key === "string") {
            if (!(key in t)) missing.push({ file: current, key: `${ns}.${key}` });
            else {
              const owner = owners.get(`${ns}.${key}`);
              if (owner && owner !== current) needs.get(current).add(owner);
            }
          }
          return Reflect.get(t, key, receiver);
        },
        set(t, key, value, receiver) {
          if (current && typeof key === "string") owners.set(`${ns}.${key}`, current);
          return Reflect.set(t, key, value, receiver);
        },
      });
      wrapped.add(proxy);
      engine[ns] = proxy;
    }
  };
  const failed = [];
  const files = filesOf(src, editor);
  for (const file of files) {
    current = path.relative(src, file);
    needs.set(current, new Set());
    try {
      vm.runInContext(fs.readFileSync(file, "utf8"), engine, { filename: file });
    } catch (e) {
      failed.push(`${current}: ${e.message.split("\n")[0]}`);
    }
    // A member that appeared through a reference the proxies do not see
    // (the file that made the namespace holds it bare) is this file's too.
    for (const ns of Object.keys(engine).filter((k) => NAMESPACE.test(k))) {
      const target = engine[ns];
      if (!target || typeof target !== "object") continue;
      for (const key of Object.keys(target)) {
        if (!owners.has(`${ns}.${key}`)) owners.set(`${ns}.${key}`, current);
      }
    }
    current = null;
    wrap();
  }
  return { engine, missing, needs, failed, files };
}

/** The files each file needed while it loaded, as the engine ran them. */
export function observedNeeds(src, webApps, editor) {
  return observe(src, webApps, editor).needs;
}

export function observedForward(src, webApps, editor) {
  const { engine, missing, failed, files } = observe(src, webApps, editor);
  // Read before it existed, and there in the end: defined by a later file.
  // Not a member the reading file defines itself: `X = X || {}` reads before
  // it writes, and needs nothing.
  const acorn = createRequire(path.join(src, "build", "package.json"))("acorn");
  const own = new Map();
  const definesOf = (file) => {
    if (!own.has(file))
      own.set(
        file,
        analyse(fs.readFileSync(path.join(src, file), "utf8"), acorn).defines,
      );
    return own.get(file);
  };
  const forward = new Map();
  for (const { file, key } of missing) {
    const [ns, member] = key.split(/\.(.*)/s);
    if (engine[ns] && member in engine[ns] && !definesOf(file).has(key)) {
      forward.set(`${key} ${file}`, { key, file });
    }
  }
  return { forward: [...forward.values()], failed, files: files.length };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const src = process.env.LIBERA_SDKJS_SRC;
  const webApps = process.env.LIBERA_WEB_APPS;
  if (!src || !webApps)
    throw new Error("LIBERA_SDKJS_SRC and LIBERA_WEB_APPS name the sources");
  const asked = process.argv.slice(2);
  for (const editor of asked.length ? asked : EDITORS) {
    const seen = observedForward(src, webApps, editor);
    console.log(
      `${editor}: ${seen.files} files, ${seen.forward.length} forward reads observed, ${seen.failed.length} file(s) failed to load`,
    );
    for (const f of seen.forward) console.log(`    ${f.key}: read by ${f.file}`);
    for (const f of seen.failed.slice(0, 10)) console.log(`    FAILED ${f}`);
  }
}
