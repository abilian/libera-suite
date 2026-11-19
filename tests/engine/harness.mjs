// An editor's engine (sdkjs), loaded in plain Node the way x2t loads it.
//
// x2t reads DoctRenderer.config (src/libera/payload/generate.py writes it),
// then doctrenderer/editors.cpp, and runs these scripts in one V8 context:
// native.js, which stubs the browser, jQuery's stub, XRegExp, the editor's
// sdk-all-min.js, the font engine, its sdk-all.js. The font engine is left
// out: fonts_native.js needs x2t's own `native` object. Nothing in the engine
// meets a DOM, so nothing here needs one.
//
// The payload's paths come from the environment, which the pytest bridge
// (tests/b_integration/payload/test_engine.py) sets from the resolved payload.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

export const EDITORS = ["word", "cell", "slide", "visio"];

function payloadPaths() {
  const sdkjs = process.env.LIBERA_SDKJS;
  const webApps = process.env.LIBERA_WEB_APPS;
  if (!sdkjs || !webApps) {
    throw new Error(
      "LIBERA_SDKJS and LIBERA_WEB_APPS name the payload's sdkjs and web-apps:" +
        " run these through pytest (tests/b_integration/payload/test_engine.py)",
    );
  }
  return { sdkjs, webApps };
}

export function scripts(editor, { sdkjs, webApps } = payloadPaths()) {
  if (!EDITORS.includes(editor)) {
    throw new Error(`no editor ${editor}: one of ${EDITORS.join(", ")}`);
  }
  return [
    path.join(sdkjs, "common/Native/native.js"),
    path.join(sdkjs, "common/Native/jquery_native.js"),
    path.join(webApps, "vendor/xregexp/xregexp-all-min.js"),
    path.join(sdkjs, editor, "sdk-all-min.js"),
    path.join(sdkjs, editor, "sdk-all.js"),
  ];
}

// sdk-all.js is wrapped in one function (build/loaders/sdk-concat.cjs), so
// its files' top-level names are not globals, as they are on upstream's test
// pages, which load the files one by one. `pageScope` loads the engine as
// such a page sees it: the bundle unwrapped, and jQuery's ready left for the
// page to fire once its own scripts are in.
const WRAPPER_OPEN = "(function(window,undefined){";
const WRAPPER_CLOSE = "})(window);";

function unwrapped(text, file) {
  const open = text.indexOf(WRAPPER_OPEN);
  if (open < 0 || open > 4096 || !text.trimEnd().endsWith(WRAPPER_CLOSE)) {
    throw new Error(`${file} is not wrapped as sdk-concat.cjs wraps it`);
  }
  const body = text.trimEnd().slice(0, -WRAPPER_CLOSE.length);
  return body.slice(0, open) + body.slice(open + WRAPPER_OPEN.length);
}

// The engine's global object: `window`, as its code calls it. `native` is
// declared because native.js tests it; x2t gives an object, we give none.
// `desktop` loads the engine as our desktop application sees it: the desktop
// layer is guarded by window.AscDesktopEditor (sdkjs 0025), which the host's
// bridge defines and a browser does not. Here it gives every answer the
// bridge gives as a constant, read from the bridge itself
// (src/libera/host/server/bridge-desktop.js: `Name: () => "value",`), and
// undefined for the rest, which need a window or a host.
const BRIDGE = new URL(
  "../../src/libera/host/server/bridge-desktop.js",
  import.meta.url,
);
const CONSTANT_ANSWER =
  /^ {4}(\w+): \(\) => (true|false|null|-?[\d.]+|"[^"]*"|\[\]|\{\}),$/gm;

function desktopStandIn() {
  const answers = {};
  for (const [, name, value] of fs
    .readFileSync(BRIDGE, "utf8")
    .matchAll(CONSTANT_ANSWER)) {
    answers[name] = () => JSON.parse(value);
  }
  return new Proxy({}, { get: (_, name) => answers[name] ?? (() => undefined) });
}

export function load(editor, paths, { pageScope = false, desktop = false } = {}) {
  const engine = { native: undefined };
  if (desktop) engine.AscDesktopEditor = desktopStandIn();
  engine.window = engine;
  vm.createContext(engine);
  const files = scripts(editor, paths);
  for (const file of files) {
    let text = fs.readFileSync(file, "utf8");
    if (pageScope && file === files.at(-1)) text = unwrapped(text, file);
    vm.runInContext(text, engine, { filename: file });
  }
  if (editor === "cell" && !pageScope) {
    // What editors.cpp appends for the spreadsheet, and only for it. A test
    // page calls it itself, once its own scripts are in, as a browser would.
    vm.runInContext("$.ready()", engine);
  }
  return engine;
}
