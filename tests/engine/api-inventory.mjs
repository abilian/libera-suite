// The API between the interface (web-apps) and the engine (sdkjs), as text,
// one line per fact, so that a change of pin shows as a diff someone reads.
//
//   member Asc.asc_docs_api.asc_Save(isAutoSave, isUndoRequest)  word slide
//   member AscDFH.CChangesBase.asc_x(...)  word  desktop
//   assigned asc_AddBookmark  cell word
//   event asc_onDocumentModifiedChanged  cell slide word
//   calls asc_getCanUndo
//   listens asc_onCountPages
//
// Members come from the loaded engines themselves: every function with a
// prototype on an Asc* namespace, and the asc_* names on that prototype (its
// own, not inherited), with their parameter names as the source declares
// them. `desktop` marks a member only the desktop view has, the layer our
// build guards by window.AscDesktopEditor. Events are the asc_on* names the
// bundles hold as strings; calls and listens are what the payload's built
// web-apps calls on the engine and registers callbacks for. Names, not
// parsed code: a name built at run time is missed, and the snapshot says so
// in no way, which is why the triage of the unexplained names is in the note.
//
//   node tests/engine/api-inventory.mjs           print it
//   node tests/engine/api-inventory.mjs --write   write tests/engine/api/sdkjs-api.txt and .d.ts
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundles, EDITORS, load } from "./harness.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SNAPSHOT = path.join(HERE, "api", "sdkjs-api.txt");
export const DECLARATIONS = path.join(HERE, "api", "sdkjs-api.d.ts");

// A function's parameters as its source declares them: what is between the
// first parentheses of its text, whitespace and comments removed.
function parameters(fn) {
  const text = Function.prototype.toString.call(fn);
  const list = /^[^(]*\(([^)]*)\)/.exec(text)?.[1] ?? "";
  return list
    .replace(/\/\*.*?\*\//gs, "")
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}

// class name -> { member -> parameters }, one engine, one view. A class
// published under several names is listed under the first, sorted.
function members(engine) {
  const found = new Map();
  const seen = new Set();
  const namespaces = Object.keys(engine)
    .filter((k) => /^Asc/.test(k) && engine[k] && typeof engine[k] === "object")
    .sort();
  for (const ns of namespaces) {
    for (const key of Object.keys(engine[ns]).sort()) {
      const value = engine[ns][key];
      if (typeof value !== "function" || !value.prototype || seen.has(value)) continue;
      seen.add(value);
      const own = {};
      for (const name of Object.getOwnPropertyNames(value.prototype).sort()) {
        const member = Object.getOwnPropertyDescriptor(value.prototype, name);
        if (/^asc_/.test(name) && typeof member.value === "function") {
          own[name] = parameters(member.value);
        }
      }
      if (Object.keys(own).length) found.set(`${ns}.${key}`, own);
    }
  }
  return found;
}

// An asc_* member assigned anywhere in a bundle: `x.asc_Name =` or
// `x["asc_Name"] =`, not a comparison.
const ASSIGNED = /(?:\[\s*["'](asc_\w+)["']\s*\]|\.(asc_\w+))\s*=(?!=)/g;

function bundleText(editor) {
  const sdkjs = process.env.LIBERA_SDKJS;
  return bundles(sdkjs, editor)
    .map((f) => fs.readFileSync(f, "utf8"))
    .join("\n");
}

function interfaceText() {
  const apps = path.join(process.env.LIBERA_WEB_APPS, "apps");
  const texts = [];
  for (const entry of fs.readdirSync(apps, { recursive: true }).sort()) {
    if (!entry.endsWith(".js")) continue;
    if (/(^|\/)(mobile|locale)\/|resources\/help\//.test(entry)) continue;
    texts.push(fs.readFileSync(path.join(apps, entry), "utf8"));
  }
  return texts.join("\n");
}

export function inventory() {
  const lines = [];
  const ui = interfaceText();
  const calls = new Set([...ui.matchAll(/\.(asc_\w+)\(/g)].map((m) => m[1]));
  const listens = new Set(
    [...ui.matchAll(/asc_registerCallback\(\s*["'](\w+)["']/g)].map((m) => m[1]),
  );
  const memberEditors = new Map(); // "Class.member(params)" -> Set of "editor" / "editor desktop"
  const eventEditors = new Map();
  const assignedEditors = new Map();
  for (const editor of EDITORS) {
    const browser = members(load(editor));
    const desktop = members(load(editor, undefined, { desktop: true }));
    for (const [view, classes] of [
      ["", browser],
      ["desktop", desktop],
    ]) {
      for (const [cls, own] of classes) {
        for (const [name, params] of Object.entries(own)) {
          if (view === "desktop" && browser.get(cls)?.[name]) continue;
          const key = `${cls}.${name}(${params.join(", ")})`;
          if (!memberEditors.has(key))
            memberEditors.set(key, { editors: new Set(), view });
          memberEditors.get(key).editors.add(editor);
        }
      }
    }
    const text = bundleText(editor);
    // An event is fired by its name, as a string: every asc_on* string, and
    // any other name the interface listens for (asc_canIncreaseIndent,
    // onPluginToolbarMenu ...) that the bundle quotes.
    const quoted = new Set([...text.matchAll(/["'](\w+)["']/g)].map((m) => m[1]));
    const fired = [...quoted].filter(
      (name) => /^asc_on/.test(name) || listens.has(name),
    );
    for (const name of fired) {
      if (!eventEditors.has(name)) eventEditors.set(name, new Set());
      eventEditors.get(name).add(editor);
    }
    for (const [, quoted, dotted] of text.matchAll(ASSIGNED)) {
      const name = quoted ?? dotted;
      if (!assignedEditors.has(name)) assignedEditors.set(name, new Set());
      assignedEditors.get(name).add(editor);
    }
  }
  for (const [key, { editors, view }] of [...memberEditors].sort()) {
    lines.push(
      `member ${key}  ${[...editors].sort().join(" ")}${view ? `  ${view}` : ""}`,
    );
  }
  // Members of objects no namespace publishes (the bookmarks manager, a code
  // page), which the interface reaches through other calls: known by their
  // assignment in the bundles' text, without a class or parameters.
  const walked = new Set(
    [...memberEditors.keys()].map((key) => /\.(asc_\w+)\(/.exec(key)[1]),
  );
  for (const [name, editors] of [...assignedEditors].sort()) {
    if (!walked.has(name))
      lines.push(`assigned ${name}  ${[...editors].sort().join(" ")}`);
  }
  for (const [name, editors] of [...eventEditors].sort()) {
    lines.push(`event ${name}  ${[...editors].sort().join(" ")}`);
  }
  for (const name of [...calls].sort()) lines.push(`calls ${name}`);
  for (const name of [...listens].sort()) lines.push(`listens ${name}`);
  return `${lines.join("\n")}\n`;
}

// The members as TypeScript declarations, every argument and result unknown
// for now: the skeleton a typed API grows from.
export function declarations(text) {
  const classes = new Map();
  for (const [, cls, name, params] of text.matchAll(
    /^member ([\w.]+)\.(asc_\w+)\(([^)]*)\)/gm,
  )) {
    if (!classes.has(cls)) classes.set(cls, []);
    const args = params
      ? params.split(", ").map((p, i) => `${/^\w+$/.test(p) ? p : `arg${i}`}?: unknown`)
      : [];
    classes.get(cls).push(`    ${name}(${args.join(", ")}): unknown;`);
  }
  const out = [
    "// Generated by tests/engine/api-inventory.mjs --write: do not edit.",
    "",
  ];
  const byNamespace = Map.groupBy(classes, ([cls]) => cls.split(".")[0]);
  for (const [ns, entries] of byNamespace) {
    out.push(`declare namespace ${ns} {`);
    for (const [cls, lines] of entries) {
      out.push(`  interface ${cls.split(".").slice(1).join("_")} {`, ...lines, "  }");
    }
    out.push("}", "");
  }
  return out.join("\n");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const text = inventory();
  if (process.argv.includes("--write")) {
    fs.mkdirSync(path.dirname(SNAPSHOT), { recursive: true });
    fs.writeFileSync(SNAPSHOT, text);
    fs.writeFileSync(DECLARATIONS, declarations(text));
    console.log(`wrote ${SNAPSHOT} and ${DECLARATIONS}`);
  } else {
    process.stdout.write(text);
  }
}
