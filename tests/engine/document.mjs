// A document opened and laid out by an engine in Node, x2t's way.
//
// Beyond harness.mjs's load(), this needs what x2t gives the engine for
// text: the font index (AllFonts.js, which x2t runs first), the font files,
// and a font engine. x2t's is FreeType and HarfBuzz in C++; here it is the
// browser's, the same code built to WebAssembly (common/libfont/engine/
// fonts.js and fonts.wasm). Then NativeOpenFileData, as native.js defines
// it and doctrenderer.cpp calls it, and the API's own asc_nativeCalculateFile.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { JQUERY_STUB, scripts } from "./harness.mjs";

const EDITOR_TYPES = { word: "document", cell: "spreadsheet", slide: "presentation" };

// What the engine asks of x2t's `native` object while it opens, lays out and
// saves a document. Anything else it asks for answers undefined. A save ends
// by telling native the file's header and length (`Save_End`), kept in `saved`.
function nativeFor(editor, file, fontsDir, saved) {
  const answers = {
    Save_End: (header, length) => Object.assign(saved, { header, length }),
    GetEditorType: () => EDITOR_TYPES[editor],
    GetFilePath: () => file,
    GetDevicePixelRatio: () => 1,
    CheckNextChange: () => false,
    GetCountChanges: () => 0,
    // The index names a font by its path, or by a file in the payload's fonts/.
    GetFontBinary: (id) =>
      new Uint8Array(
        fs.readFileSync(path.isAbsolute(id) ? id : path.join(fontsDir, id)),
      ),
  };
  return new Proxy(
    {},
    {
      get: (_, name) =>
        answers[name] ?? (typeof name === "string" ? () => undefined : undefined),
    },
  );
}

// The browser's WebAssembly engines, standing in for x2t's C++ ones: fonts
// (FreeType and HarfBuzz) and zlib. Each declares its own `Module` inside its
// wrapper, so its binary can only be handed in by rewriting that one
// declaration as the text is loaded.
const MODULE_DECLARATION = 'var Module=typeof Module!="undefined"?Module:{}';
const WASM_ENGINES = {
  fonts: "common/libfont/engine/fonts",
  zlib: "common/zlib/engine/zlib",
};

function runWasmEngine(run, engine, sdkjs, name) {
  const base = path.join(sdkjs, WASM_ENGINES[name]);
  const text = fs.readFileSync(`${base}.js`, "utf8");
  if (!text.includes(MODULE_DECLARATION)) {
    throw new Error(`${base}.js no longer declares Module as this expects`);
  }
  engine.__modules[name] = { wasmBinary: fs.readFileSync(`${base}.wasm`) };
  run(
    `${base}.js`,
    text.replace(MODULE_DECLARATION, `var Module=window.__modules.${name}`),
  );
}

async function until(ready, what) {
  for (let i = 0; i < 500 && !ready(); i++) {
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  if (!ready()) throw new Error(`${what} did not start in 5 s`);
}

// `file`: a path to an Editor.bin, or its bytes.
export async function openDocument(
  editor,
  file,
  { payload = process.env.LIBERA_PAYLOAD } = {},
) {
  if (!payload)
    throw new Error(
      "LIBERA_PAYLOAD names the payload whose AllFonts.js and fonts/ to use",
    );
  const sdkjs = path.join(payload, "sdkjs");
  const saved = {};
  const engine = {
    native: nativeFor(editor, file, path.join(payload, "fonts"), saved),
    __modules: {},
    // x2t's zip object; the browser's WebAssembly zlib does the same work.
    CreateEmbedObject: (name) => {
      if (name !== "CZipEmbed") throw new Error(`no stand-in for x2t's ${name}`);
      return new engine.AscCommon.CZLibEngineJS();
    },
    setTimeout,
    clearTimeout,
  };
  engine.window = engine;
  engine.self = engine;
  vm.createContext(engine);
  const run = (file, text = fs.readFileSync(file, "utf8")) =>
    vm.runInContext(text, engine, { filename: file });

  run(path.join(payload, "AllFonts.js"));
  const files = scripts(editor, {
    sdkjs,
    webApps: path.join(payload, "web-apps"),
  });
  for (const file of files.slice(0, -1)) run(file);
  runWasmEngine(run, engine, sdkjs, "fonts");
  runWasmEngine(run, engine, sdkjs, "zlib");
  run(files.at(-1));
  if (editor === "cell" && files.some((f) => f.endsWith(JQUERY_STUB))) {
    // What editors.cpp appends for the spreadsheet, and only for it.
    vm.runInContext("$.ready()", engine);
  }
  // Each WebAssembly engine compiles asynchronously: text shaping and the zip
  // reader exist once it has.
  await until(
    () => typeof engine.AscFonts.HB_StartString === "function",
    "the font engine",
  );
  await until(() => engine.AscCommon.CZLibEngineJS?.prototype.isModuleInit, "zlib");

  const data = typeof file === "string" ? fs.readFileSync(file) : Buffer.from(file);
  const version = Number(/;v(\d+);/.exec(data.subarray(0, 32).toString("latin1"))?.[1]);
  engine.NativeOpenFileData(new Uint8Array(data), version, undefined, {});
  const api = engine.Asc.editor;
  api.asc_nativeCalculateFile();
  // The document as the engine's own writer saves it, in the editor's format,
  // ready to open again: its buffer, which starts with the format's header, up
  // to the length Save_End was told.
  const save = () => {
    const buffer = api.asc_nativeGetFileData();
    return Buffer.from(buffer.buffer, buffer.byteOffset, saved.length);
  };
  return { engine, api, pages: api.asc_nativePrintPagesCount(), save };
}
