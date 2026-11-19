// Namespace members the engine reads that no engine defines and no line
// assigns: `AscCommon.changestype_Document_Contentt`, a typo for a constant
// that exists, is one. Such a read is undefined at run time: a lock checked
// against nothing, a change recorded with no type, a call that throws.
//
// Found without a type checker: the loaded engines say what each Asc*
// namespace holds once every file has run; the bundles' text says which
// members are read and which are assigned anywhere (a member set at run time,
// Asc.editor or AscCommon.CollaborativeEditing, is assigned somewhere). What
// is read, held by no namespace and assigned nowhere is reported.
import fs from "node:fs";
import path from "node:path";
import { EDITORS, load } from "./harness.mjs";

// A name ends where its characters do ((?![\w$])): without it, a member
// followed by `=` would backtrack one character short of the assignment and
// be reported under a name it does not have.
const READ =
  /\b(Asc\w*)\s*(?:\.\s*([A-Za-z_$][\w$]*)(?![\w$])|\[\s*["']([A-Za-z_$][\w$]*)["']\s*\])(?!\s*=[^=])/g;
const ASSIGNED =
  /(?:\.\s*([A-Za-z_$][\w$]*)|\[\s*["']([A-Za-z_$][\w$]*)["']\s*\])\s*=(?!=)/g;

export const KNOWN = new URL("./api/undefined-members.txt", import.meta.url);

export function undefinedMembers() {
  const held = new Map(); // namespace -> Set of members, across editors and views
  const read = new Map(); // "Ns.member" -> Set of editors
  const assigned = new Set();
  for (const editor of EDITORS) {
    for (const desktop of [false, true]) {
      const engine = load(editor, undefined, { desktop });
      for (const ns of Object.keys(engine).filter((k) => /^Asc/.test(k))) {
        if (!engine[ns] || typeof engine[ns] !== "object") continue;
        if (!held.has(ns)) held.set(ns, new Set());
        for (const member of Object.keys(engine[ns])) held.get(ns).add(member);
      }
    }
    const text = ["sdk-all-min.js", "sdk-all.js"]
      .map((f) =>
        fs.readFileSync(path.join(process.env.LIBERA_SDKJS, editor, f), "utf8"),
      )
      .join("\n");
    for (const [, a, b] of text.matchAll(ASSIGNED)) assigned.add(a ?? b);
    for (const [, ns, a, b] of text.matchAll(READ)) {
      const name = `${ns}.${a ?? b}`;
      if (!read.has(name)) read.set(name, new Set());
      read.get(name).add(editor);
    }
  }
  const found = [];
  for (const [name, editors] of read) {
    const [ns, member] = name.split(".");
    // A namespace no engine has at all is an add-on's (AscOForm), or a
    // local variable that happens to start with Asc. AscDesktopEditor is the
    // host's object, not the engine's.
    if (!held.has(ns) || ns === "AscDesktopEditor") continue;
    if (held.get(ns).has(member) || assigned.has(member)) continue;
    found.push(`${name}  ${[...editors].sort().join(" ")}`);
  }
  return found.sort();
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  for (const line of undefinedMembers()) console.log(line);
}
