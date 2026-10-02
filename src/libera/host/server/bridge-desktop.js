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

  // -- File > Create New -------------------------------------------------------
  //
  // The editor asks for a new document of its own kind, because that is all it
  // knows to ask for, so Create New in Words could only make another Words
  // document. The choice is offered here instead, over the whole window: one
  // button per kind the host can create. The list is the host's
  // (/__host__/apps, which the start window draws too), so a kind is offered in
  // both or in neither, and the icons are the editor's own format icons, served
  // from the payload. Esc, or a click outside, leaves everything as it was.
  const CHOOSER = "libera-create-new";
  const ICONS = "/web-apps/apps/common/main/resources/img/doc-formats/large/";

  function createNew(type) {
    const made = postToHostSync(`/__host__/new?type=${encodeURIComponent(type)}`);
    if (made.status !== 200) {
      // `libera --serve` has one window, and a new document of another kind
      // cannot take the place of this one. The host says so; so does this.
      w.alert(made.statusText || "Libera Suite could not create the document.");
      return;
    }
    if (openedHere(made)) w.top.location.reload();
  }

  function chooseNewKind(own) {
    const doc = w.top.document;
    if (doc.getElementById(CHOOSER)) return;
    getFromHost("/__host__/apps", (xhr) => {
      let kinds = [];
      try {
        kinds = JSON.parse(xhr.responseText).filter((app) => app.creates);
      } catch (_e) {
        // No list to offer: the editor's own kind is still a new document.
      }
      if (kinds.length) showChooser(doc, kinds, own);
      else createNew(own);
    });
  }

  function showChooser(doc, kinds, own) {
    const page = w.document.documentElement;
    const dark =
      page.classList.contains("theme-type-dark") ||
      (w.document.body?.classList.contains("theme-type-dark") ?? false);
    const [card, text, line, raised] = dark
      ? ["#2a2a2a", "#e8e5e0", "#4a4a4a", "#333"]
      : ["#fff", "#1e1a17", "#d8d2c8", "#fff"];

    const backdrop = doc.createElement("div");
    backdrop.id = CHOOSER;
    backdrop.style.cssText =
      "position:fixed;inset:0;z-index:100000;display:flex;align-items:center;" +
      "justify-content:center;background:rgba(0,0,0,.35);" +
      "font:14px system-ui,-apple-system,'Segoe UI',sans-serif;";
    const dialog = doc.createElement("div");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", "Create New");
    dialog.style.cssText =
      `background:${card};color:${text};border-radius:10px;` +
      "padding:18px 22px 22px;box-shadow:0 12px 40px rgba(0,0,0,.3);";
    const title = doc.createElement("div");
    title.textContent = "Create New";
    title.style.cssText = "font-weight:600;font-size:15px;margin-bottom:14px;";
    const row = doc.createElement("div");
    row.style.cssText = "display:flex;gap:12px;";

    // Return and Esc, caught before the editor sees them, in its frame as well
    // as here: a chooser opened by a key leaves the focus in the editor, which
    // takes it back on the key's way up, and would type the Return into the
    // document. Return takes the focused choice, else the editor's own kind.
    const docs = [doc, w.document];
    const buttons = [];
    const onKey = (event) => {
      if (event.key !== "Escape" && event.key !== "Enter") return;
      event.preventDefault();
      event.stopPropagation();
      if (event.key === "Escape") {
        close();
        return;
      }
      const focused = buttons.find((b) => b === doc.activeElement);
      (focused || preferred()).click();
    };
    const close = () => {
      backdrop.remove();
      for (const d of docs) d.removeEventListener("keydown", onKey, true);
    };
    const preferred = () =>
      buttons.find((b) => b.dataset.doctype === own) || buttons[0];

    for (const app of kinds) {
      const button = doc.createElement("button");
      button.type = "button";
      button.dataset.doctype = app.doctype;
      button.style.cssText =
        "display:flex;flex-direction:column;align-items:center;gap:8px;" +
        `width:120px;padding:14px 8px;border:1px solid ${line};border-radius:8px;` +
        `background:${raised};color:inherit;font:inherit;cursor:pointer;`;
      const icon = doc.createElement("img");
      icon.src = `${ICONS}${app.ext}.svg`;
      icon.alt = "";
      icon.width = 48;
      icon.height = 48;
      const label = doc.createElement("span");
      label.textContent = app.kind;
      button.append(icon, label);
      button.addEventListener("click", () => {
        close();
        createNew(app.doctype);
      });
      row.append(button);
      buttons.push(button);
    }

    backdrop.addEventListener("mousedown", (event) => {
      if (event.target === backdrop) close();
    });
    for (const d of docs) d.addEventListener("keydown", onKey, true);
    dialog.append(title, row);
    backdrop.append(dialog);
    doc.body.append(backdrop);
    // The editor's own kind has the focus, so Return does what Create New
    // did before there was a choice.
    preferred().focus();
  }

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
    // The console shows it asked twice on every load, and the two handovers
    // were once blamed for the intermittent stall at "Loading document: 8%".
    // They were not its cause: that was a font request reset by the host's
    // listen backlog -- see Server.request_queue_size in handler.py. Handing
    // the same bytes over twice cannot be right whatever the editor's reason
    // for asking, so this stays, as a contract rather than a workaround.
    LocalStartOpen: function () {
      log("LocalStartOpen", arguments);
      if (handedOver) return;
      handedOver = true;
      const opened = getFromHostSync("/__host__/opened");
      if (opened === null) {
        // Said as what it is. Parsed regardless, the null threw "Cannot read
        // properties of null" from a timer, and that was the reload offer's text.
        report("error", "the host has no converted document to hand over");
        return;
      }
      const payload = JSON.parse(opened);
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
      const sent = postToHostSync(
        "/__host__/changes?index=" +
          (index == null ? "" : index | 0) +
          "&count=" +
          (count | 0),
        body,
      );
      // An XHR answers a 500 without throwing. An edit the log did not take
      // is one no save will write, so say it as an error: the host offers a
      // reload, which puts the editor back in step with what is on disk.
      if (sent.status !== 204) {
        report("error", `the change log did not take an edit (HTTP ${sent.status})`);
      }
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
        (xhr) => {
          // Nothing in the editor waits for this, so a failure is ours to say.
          if (answer(xhr).error !== 0) {
            w.alert("Libera Suite could not print this document.");
          }
        },
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
        chooseNewKind(String(param || "word"));
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

  // The editor is an offline desktop editor, and it decides so once: from
  // asc_isOffline() when its permissions arrive, which picks Save As over
  // Download As in the File menu, among much else. The SDK's base answer is
  // "is this page a file: URL", which over http is no; the desktop half of the
  // SDK, sdk-all.js, answers yes, but it loads by a <script> tag after
  // sdk-all-min.js and raced the permissions. A slow load lost, and the File
  // menu offered Download As. Measured in WebKit with sdk-all.js held back
  // three seconds: Download As three times in three, Save As three in three
  // on time.
  //
  // So the answer is made the desktop one as soon as sdk-all-min.js has run,
  // which defines it, and before the editor built on it can ask. On every API
  // class that has its own copy: each editor's API copies the base method when
  // it is defined, so patching the base alone changed nothing. A capturing
  // listener, because a script's load event does not bubble, and on the
  // document, because a load event never reaches the window at all.
  w.document.addEventListener(
    "load",
    (e) => {
      const src = (e.target && e.target.src) || "";
      if (!src.includes("/sdk-all-min.js")) return;
      const classes = [w.AscCommon.baseEditorsApi, ...Object.values(w.Asc || {})];
      for (const api of classes) {
        if (
          typeof api === "function" &&
          Object.hasOwn(api.prototype || {}, "asc_isOffline")
        ) {
          api.prototype.asc_isOffline = () => true;
        }
      }
    },
    true,
  );

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

  // Tell the host what the editor can do, so the menu bar can grey out an
  // item that would decline. Pushed, not asked for: a menu is validated on the
  // GUI thread, and asking the editor from there would deadlock.
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

  // The editor reports document trouble through its own asc_onError event and
  // a modal, not through a JS exception -- so a run can look clean to
  // window.onerror while the user is staring at "An error occurred during the
  // work with the document". Hook it. asc_registerCallback is a quoted export,
  // so it survives minification.
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
