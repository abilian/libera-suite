// window.AscDesktopEditor: the seam between the editor and the host.
//
// Upstream this is C++ inside CEF (client_renderer_wrapper.cpp). Here it is a
// page of JavaScript talking to a loopback HTTP server, which is what makes
// the host a Python process instead of a browser fork. Every call is logged,
// and unknown methods stay absent rather than returning a stub -- the editor
// feature-detects, so pretending to have a method changes its behaviour.
//
// Loaded last: it needs the transport from bridge-runtime.js and the page
// shims from bridge-page.js.

((M) => {
  if (!M || M.w.__LIBERA_BRIDGE__) return;
  M.w.__LIBERA_BRIDGE__ = true;
  const w = M.w;
  const {
    TAG,
    answer,
    calls,
    getFromHost,
    getFromHostSync,
    log,
    openedHere,
    postToHost,
    postToHostSync,
    report,
  } = M;
  const { captureLater, spellChecker } = M.page;

  // -- host state -------------------------------------------------------------
  const DOC_DIR = "/doc"; // where Editor.bin + media/ live
  let saved = true;
  let handedOver = false; // the document goes to the editor once: LocalStartOpen

  // The path of the open document, read once. The native LocalFileGetSourcePath
  // is an in-memory getter that cannot fail, so making it a per-call network
  // request turns any hiccup -- teardown included -- into a JS exception inside
  // the editor. Fetch once; the host tells us when it changes.
  let docPath = "";

  const currentBody = getFromHostSync("/__host__/current");
  if (currentBody) docPath = JSON.parse(currentBody).path || "";

  const impl = {
    // --- lifecycle
    // Once per page, however many times the editor asks.
    //
    // It asks twice, about 7ms apart, on every single load -- measured in the
    // console log of both a good run and a stalled one. Each ask schedules
    // DesktopOfflineAppDocumentEndLoad, so the document was being fed into the
    // editor twice, and the two were racing.
    //
    // That race is where the intermittent stall happens. Captured with the
    // browser's console on a run that hung: everything up to the second
    // SetDocumentName, then silence -- no error, no further call, for 75
    // seconds. A good run goes straight on to `doc:onready`. The step in
    // between is this handover, and it is the only thing here that runs twice.
    //
    // Handing the same bytes over twice cannot be right whatever the editor's
    // reason for asking, so this is a contract rather than a workaround.
    LocalStartOpen: function () {
      log("LocalStartOpen", arguments);
      if (handedOver) return;
      handedOver = true;
      const payload = JSON.parse(getFromHostSync("/__host__/opened"));
      setTimeout(() => {
        w.DesktopOfflineAppDocumentEndLoad(DOC_DIR, payload.b64, payload.len);
      }, 0);
    },
    CheckUserId: () => "poc-user",
    // The real path of the open document, from the host. The title bar, "open
    // file location" and plain Save all hang off this.
    LocalFileGetSourcePath: () => docPath,
    SetDocumentName: function () {
      log("SetDocumentName", arguments);
    },
    onDocumentContentReady: function () {
      log("onDocumentContentReady", arguments);
      captureLater();
    },
    // The editor's own dirty flag, and the only reliable one: the change log
    // stays non-empty after a save, because it is the delta from the document
    // as it was opened. The host keeps it so that a crash -- or a window
    // closed without saving -- can be offered back on the next open.
    onDocumentModifiedChanged: function (m) {
      saved = !m;
      log("onDocumentModifiedChanged", arguments);
      postToHost("/__host__/modified", JSON.stringify({ modified: !!m }));
    },

    // --- save (POC: acknowledge, write nothing)
    LocalFileGetSaved: () => saved,
    LocalFileSetSaved: (v) => {
      saved = v;
    },
    LocalFileGetOpenChangesCount: () => 0,
    // LocalFileSave(params, password, docinfo, fileType, jsonOptions, oldPassword).
    // The host converts Editor.bin (+ the change log) back to a real file and
    // must answer with DesktopOfflineAppDocumentEndSave(error, hash, password).
    // Async on purpose: x2t takes about a second, and the editor expects the
    // call to return immediately and be told later.
    LocalFileSave: function (params, password, _docinfo, fileType) {
      log("LocalFileSave", arguments);
      const body = JSON.stringify({ fileType: fileType || 0, params: params || "" });
      postToHost("/__host__/save", body, (xhr) => {
        const reply = answer(xhr);
        // No reply, or one without an error code, is a failed save.
        const error = reply.error === undefined ? 2 : reply.error;
        if (error === 0) {
          saved = true;
          // Save As moves the document; keep the cached path in step without a
          // reload.
          docPath = reply.path || docPath;
        }
        w.DesktopOfflineAppDocumentEndSave(error, "", password || "");
      });
    },
    // The editor hands over its change log here, already joined with '","'.
    // Without it, saving would write back the document as it was opened.
    LocalFileSaveChanges: function (changes, index, count) {
      log("LocalFileSaveChanges", arguments);
      // index is null during ordinary typing -- it only carries a value when
      // undo has rewound the history. Send it as empty rather than as a number,
      // because index 0 means "truncate the whole log".
      const body = Array.isArray(changes)
        ? changes.join('","')
        : changes == null
          ? ""
          : String(changes);
      postToHostSync(
        "/__host__/changes?index=" +
          (index == null ? "" : index | 0) +
          "&count=" +
          (count | 0),
        body,
      );
    },
    // The host's "save finished, or there was nothing to save" acknowledgement
    // (AscDesktopEditor_Save calls it when asc_Save declines). Only long-lived
    // sessions reach it, so a short headless run never notices it is missing --
    // in a real window it throws and the editor shows its error modal.
    OnSave: function () {
      saved = true;
      log("OnSave", arguments);
    },
    AddChanges: function () {
      log("AddChanges", arguments);
    },

    // --- files
    IsLocalFile: () => true,
    IsLocalFileExist: () => false,
    IsImageFile: () => false,
    LocalFileGetImageUrlCorrect: (p) => p,
    // The return value is discarded: web-apps calls this to *ask*, and expects
    // the answer through window.onupdaterecents, which is what the C++ host
    // calls. Each record needs a format id the editor will accept -- for Words
    // that is anything above FILE_DOCUMENT and no higher than
    // FILE_PRESENTATION, and anything else is dropped without a word.
    LocalFileRecents: function () {
      log("LocalFileRecents", arguments);
      getFromHost("/__host__/recents", (xhr) => {
        const list = answer(xhr);
        w.onupdaterecents && w.onupdaterecents(Array.isArray(list) ? list : []);
      });
      return "[]";
    },
    LocalFileRecovers: () => "[]",

    // --- capability probes: everything off, so no optional subsystem starts
    isSupportNetworkFunctionality: () => false,
    isSupportPlugins: () => false,
    isSupportMacroses: () => false,
    isBlockchainSupport: () => false,
    IsSignaturesSupport: () => false,
    IsProtectionSupport: () => false,
    IsSupportMedia: () => false,
    IsSupportNativePrint: () => false,
    IsCloudCryptoSupport: () => false,
    IsNativeViewer: () => false,
    IsFilePrinting: () => false,
    isFileCrypt: () => false,
    GetCryptoMode: () => 0,
    getEngineVersion: () => "poc-0",
    // Must be a real array, not JSON: device_scale.js reads .length and
    // feeds the values straight into the canvas scale maths. A string
    // gets length 2 and produces a NaN-sized canvas.
    GetSupportedScaleValues: () => [],
    GetInstallPlugins: () => {
      const empty = { url: "/sdkjs-plugins/", pluginsData: [] };
      return JSON.stringify([empty, empty]);
    },
    GetBackupPlugins: () => JSON.stringify([]),
    getViewportSettings: () => ({}),
    _getViewportSettings: () => "{}",
    GetFontThumbnailHeight: () => 26,
    getDictionariesPath: () => "/dictionaries",

    // --- discovered by POC-0: sdk-all-min.js reads .length on the return of
    //     GetEncryptedHeader at load time, and web-apps asks for the font sprite.
    GetEncryptedHeader: () => "ENCRYPTED;",
    getFontsSprite: (sfx) => `/sdkjs/common/Images/fonts_thumbnail${sfx || ""}.png`,
    CryptoMode: 0,

    // --- called WITHOUT a feature check, so absence is never correct ----------
    // These are invoked directly (`AscDesktopEditor.X()`), not probed, so a
    // missing one is a TypeError mid-edit rather than a disabled feature. The
    // return values come from the C++ handlers in client_renderer_wrapper.cpp;
    // where that returns void, a no-op is the faithful implementation.
    // Slides, starting and ending a demonstration. sdkjs guards this on
    // `undefined !== window.AscDesktopEditor` and nothing else, so the moment
    // a bridge exists the call is made -- "show from the beginning" was a
    // TypeError and an asc_onError -25 until this was here.
    SetFullscreen: (on) =>
      postToHost("/__host__/fullscreen", on ? "1" : "0", null, "text/plain"),

    // Insert > Audio and Insert > Video, in Slides and Words. Also unguarded,
    // and worse than SetFullscreen: sdkjs blocks the whole editor with
    // sync_StartAction(BlockInteraction, Waiting) *before* calling, and waits
    // for the native host to end it. A missing method leaves the editor frozen
    // behind a TypeError, and a plain no-op leaves it frozen silently.
    //
    // Libera Suite carries no native media, so the honest answer is to give the
    // editor back and say why.
    AddAudio: (file) => mediaUnsupported("Audio", file),
    AddVideo: (file) => mediaUnsupported("Video", file),

    // Playing embedded media, which the native host does in its own window.
    // Nothing blocks around these, so the only cost of doing nothing is the
    // playback we do not have.
    MediaStart: () => undefined,

    // The presenter window -- upstream opens a second window with the notes
    // and the next slide, and drives it through these. sdkjs guards them on
    // `if (window["AscDesktopEditor"])` and nothing more, so all four are a
    // TypeError without a presenter window rather than a missing feature:
    // endReporter is called when a slideshow ends, which is every slideshow.
    startReporter: () => undefined,
    endReporter: () => undefined,
    sendToReporter: () => undefined,
    sendFromReporter: () => undefined,

    // Also called unguarded, and "nothing" is the faithful answer to each.
    //
    // GetOpenedFile returns the bytes of the file the host opened, for the
    // branches that re-read it -- csv import, binary_content:// URLs. We hand
    // the editor Editor.bin instead, so there is nothing to give back;
    // sdkjs checks the result and raises ConvertationOpenError, which is a
    // real error message rather than an exception.
    GetOpenedFile: () => undefined,
    // Insert > Text from file, after the file dialog. The callback is written
    // `if (!uint8Array) return`, so calling it with nothing is the supported
    // way to say the file could not be read.
    loadLocalFile: (_file, done) => {
      if (typeof done === "function") done(undefined);
    },
    // Where a saved file sits relative to the one that links to it. We do not
    // track that; an empty string means "no relative path", which is what a
    // document that has never been saved reports too.
    LocalFileGetRelativePath: () => "",
    // Tables handing the native host a workbook to cache. Nothing caches it.
    OpenWorkbook: () => undefined,
    // Tables telling the host a cell editor opened or closed, so the native
    // app can hold the file open. It *is* feature-checked, but the check sits
    // around both registrations and too far from the calls for
    // test_bridge_surface to see it -- and a no-op costs a line where being
    // wrong costs a frozen editor.
    onFileLockedClose: () => undefined,

    CheckNeedWheel: () => true, // C++: always true (compat stub)
    LoadJS: () => 0,
    GetImageBase64: () => "",
    GetImageFormat: (p) =>
      String(p || "")
        .split(".")
        .pop(),
    GetDropFiles: () => [],
    PluginUninstall: () => false,
    IsCachedPdfCloudPrintFileInfo: () => false,

    // void in C++ — features we do not carry, which the editor still calls
    // unguarded. Doing nothing is what the native host does for most of them.
    // Spell checking. Upstream's host answers this in C++ from bundled Hunspell
    // dictionaries. We do not have to: sdkjs already carries the same engine
    // compiled to wasm as a web worker, and only uses it when AscDesktopEditor
    // is absent. So we start that worker ourselves and forward both ways.
    //
    // The reply goes to window.asc_nativeOnSpellCheck, which is what the C++
    // host calls, and the worker's message is already in the shape the editor
    // wants: {..task.., usrCorrect: [...], usrSuggest: [...]}.
    SpellCheck: function (data) {
      log("SpellCheck", arguments);
      const checker = spellChecker();
      if (!checker) return;
      if (data === "clear") {
        // "clear" means abandon the queue, not "check the word clear".
        checker.restart();
        w.asc_nativeOnSpellCheck && w.asc_nativeOnSpellCheck("clear");
        return;
      }
      try {
        checker.command(JSON.parse(data));
      } catch (e) {
        report("error", `spellcheck: ${e}`);
      }
    },
    SetAdvancedOptions: () => {},
    SaveQuestion: () => {},
    LoadFontBase64: () => {},
    PreloadCryptoImage: () => {},
    NativeViewerOpen: () => {},
    startExternalConvertation: () => {},
    localSaveToDrawingFormat: () => {},
    localSaveToDrawingFormat2: () => {},
    emulateCloudPrinting: () => {},
    // Where printing actually arrives. sdkjs's asc_Print calls _printDesktop
    // first, which for Words hands the host this JSON and returns true -- so
    // nothing downstream runs, and an empty stub is a dead menu item and a dead
    // toolbar button. Upstream's host draws its own print preview; we have
    // none, so produce the PDF and let the desktop's PDF viewer, which has a
    // print dialog, take it from there. Nothing calls back: the editor starts
    // no blocking action and expects no reply.
    Print: function () {
      log("Print", arguments);
      postToHost(
        "/__host__/save",
        JSON.stringify({ fileType: 513, isPrint: true, params: "" }),
      );
    },
    Print_Start: () => {},
    Print_Page: () => {},
    Print_End: () => {},
    RemoveFile: () => {},
    ResaveFile: () => {},
    CallInAllWindows: () => {},
    GetDefaultCertificate: () => {},
    SelectCertificate: () => {},
    ViewCertificate: () => {},
    Sign: () => {},
    RemoveSignature: () => {},
    RemoveAllSignatures: () => {},
    PluginInstall: () => {},
    CompareDocumentFile: () => {},
    CompareDocumentUrl: () => {},
    MergeDocumentFile: () => {},
    MergeDocumentUrl: () => {},
    CryptoDownloadAs: () => {},
    OpenFileCrypt: () => {},
    buildCryptedStart: () => {},
    buildCryptedEnd: () => {},
    convertFile: () => {},
    openExternalReference: () => {},
    sendSystemMessage: () => {},
    DownloadFiles: () => {},

    // --- Insert > Image ------------------------------------------------------
    // Async on purpose: the dialog runs on the GUI thread, so a synchronous
    // request here would deadlock (GUI thread blocked waiting for the server,
    // server waiting for the GUI thread).
    OpenFilenameDialog: function (filter, ismulti, callback) {
      log("OpenFilenameDialog", arguments);
      const where = `/__host__/open?filter=${encodeURIComponent(filter || "")}`;
      postToHost(where, null, (xhr) => {
        // No path means cancelled, which is a normal answer.
        const path = answer(xhr).path || "";
        if (callback) callback(ismulti ? (path ? [path] : []) : path);
      });
    },

    // The native host copies the picked file into the document's media folder
    // and hands back the name it stored it under; the caller then resolves that
    // through g_oDocumentUrls. Returning the input path unchanged would produce
    // a URL nothing can serve.
    LocalFileGetImageUrl: (path) =>
      answer(postToHostSync("/__host__/media-import", String(path || ""))).name || "",

    // --- the catch-all channel web-apps uses for almost everything
    // web-apps talks to the host almost entirely through this one channel.
    // "create:new" is File > New: the editor delegates the whole job and does
    // nothing itself, so an unhandled command looks like a dead menu item.
    execCommand: function (cmd, param) {
      log("execCommand", arguments);

      if (cmd === "create:new") {
        const made = postToHostSync(
          `/__host__/new?type=${encodeURIComponent(param || "word")}`,
        );
        if (openedHere(made)) w.top.location.reload();
        return;
      }

      // File > Open File Location.
      if (cmd === "go:folder") {
        postToHost("/__host__/reveal");
        return;
      }

      // File > Open Recent. The id is the path we handed out; the host checks
      // it against its own list rather than trusting the page with a path.
      if (cmd === "open:recent") {
        postToHost("/__host__/open-recent", param || "{}", (xhr) => {
          if (openedHere(xhr)) w.top.location.reload();
        });
        return;
      }

      // File > Open arrives wrapped in an editor:event. Async, because it puts
      // a file dialog on the GUI thread.
      if (cmd === "editor:event") {
        let action = "";
        try {
          action = JSON.parse(param || "{}").action;
        } catch (_e) {
          /* not one we handle */
        }
        if (action !== "file:open") return;
        postToHost("/__host__/open-document", null, (xhr) => {
          if (openedHere(xhr)) w.top.location.reload();
        });
      }
    },
    CreateEditorApi: function () {
      log("CreateEditorApi", arguments);
    },
    _CreateEditorApi: function () {
      log("_CreateEditorApi", arguments);
    },
  };

  // Hand the editor back after a feature we do not carry. sdkjs blocks
  // interaction before calling the native host and expects the host to end
  // the action; without this the window is alive but frozen, which is the
  // worst of the three possible outcomes.
  function mediaUnsupported(kind, file) {
    report("unsupported", `${kind} insertion is not implemented (${file || "?"})`);
    const api = (w.Asc && w.Asc.editor) || w.editor;
    const types = w.Asc || {};
    if (api && api.sync_EndAction && types.c_oAscAsyncActionType) {
      api.sync_EndAction(
        types.c_oAscAsyncActionType.BlockInteraction,
        types.c_oAscAsyncAction.Waiting,
      );
    }
  }

  w.AscDesktopEditor = new Proxy(impl, {
    get: (t, k) => {
      if (k in t) {
        const v = t[k];
        return typeof v !== "function"
          ? v
          : function () {
              const r = v.apply(t, arguments);
              log(k, arguments, r);
              return r;
            };
      }
      // Do NOT hand back a stub for unknown names. The editor feature-detects
      // with `AscDesktopEditor.X ? X() : fallback`, so pretending to have a
      // method changes behaviour. Record the probe and stay absent.
      if (typeof k === "string" && k[0] !== "@" && k !== "then") {
        calls.push({ frame: TAG, name: `PROBED:${k}`, args: [] });
      }
      return undefined;
    },
  });

  // The page photographs itself, rather than the harness asking Chromium for a
  // screenshot. --screenshot only fires when --virtual-time-budget runs out, and
  // when that budget is even slightly short the browser quits mid-load: the run
  // stops at a different place each time, with no error and no incomplete
  // response. Capturing from inside the page needs neither flag, and yields the
  // document canvas alone instead of a window full of chrome to crop.

  (function watchEditorState() {
    const api = (w.Asc && w.Asc.editor) || w.editor;
    if (!api || !api.asc_registerCallback) {
      setTimeout(watchEditorState, 50);
      return;
    }
    const send = (what) => (value) => {
      const state = {};
      state[what] = !!value;
      postToHost("/__host__/can", JSON.stringify(state));
    };
    api.asc_registerCallback("asc_onCanUndo", send("undo"));
    api.asc_registerCallback("asc_onCanRedo", send("redo"));
  })();

  (function watchEditorErrors() {
    const api = (w.Asc && w.Asc.editor) || w.editor;
    if (!api || !api.asc_registerCallback) {
      return void setTimeout(watchEditorErrors, 50);
    }
    api.asc_registerCallback("asc_onError", (code, level) => {
      report("asc_onError", `code=${code} level=${level}`);
    });
  })();

  console.log(`[libera:${TAG}] bridge installed`);
})(window.__libera__);
