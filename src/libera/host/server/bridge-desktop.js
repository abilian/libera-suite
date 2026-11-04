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
  if (!M || M.desktop) return;
  M.desktop = true;
  const w = M.w;
  const {
    TAG,
    answer,
    calls,
    getFromHost,
    getFromHostSync,
    hostUrl,
    log,
    openedHere,
    postToHost,
    postToHostSync,
    report,
    sendReport,
  } = M;
  const { addPersonalWord, captureLater, spellChecker } = M.page;
  // Our strings in the interface language, from the prelude (server/editor.py).
  const tr = (english) => (w.LIBERA_STRINGS || {})[english] || english;

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
    const made = postToHostSync("/__host__/new", JSON.stringify({ type }));
    if (made.status !== 200) {
      // `libera --serve` has one window, and a new document of another kind
      // cannot take the place of this one. The host says so, in the body: the
      // status line is Latin-1 only, so no explanation goes there.
      w.alert(made.responseText || tr("Libera Suite could not create the document."));
      return;
    }
    if (openedHere(made)) w.top.location.reload();
  }

  // File > Open and File > Close, from the editor's File tab or a key.
  function openDocument() {
    postToHost("/__host__/open-document", null, (xhr) => {
      if (openedHere(xhr)) w.top.location.reload();
    });
  }

  function closeWindow() {
    postToHost("/__host__/close");
  }

  // -- Ctrl-N, Ctrl-O and Ctrl-W on Windows -----------------------------------
  //
  // No menu bar fires them there and the editor handles none of them, so the
  // page runs what the editor's File tab would. The host says which keys
  // (shortcuts.PAGE_RUNS) and sends none on macOS or Linux, whose menu bars have them. Every frame installs its
  // own, on the window and capturing, because a keydown in the editor's iframe
  // never reaches the top document.
  const PAGE_KEYS = w.LIBERA_PAGE_KEYS || {};
  const RUNS = { new: () => createNew(""), open: openDocument, close: closeWindow };
  w.addEventListener(
    "keydown",
    (e) => {
      // A held key repeats, and each repeat would be another window.
      if (!e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
      const key = (e.key || "").toLowerCase();
      const action = Object.keys(PAGE_KEYS).find(
        (name) => PAGE_KEYS[name].key === key && PAGE_KEYS[name].shift === e.shiftKey,
      );
      if (!action) return;
      // Both, unlike bridge-page.js's Cmd-N: no menu waits for this key, and
      // a webview left to it may act on Ctrl-N or Ctrl-W as a browser would.
      e.preventDefault();
      e.stopImmediatePropagation();
      RUNS[action]();
    },
    true,
  );

  // -- files dropped on the window --------------------------------------------
  //
  // A page is told a dropped file's name and never its path, so the host is
  // asked, before anything in the page handles the drop: it has the paths from
  // the drag itself, opens the documents among them in windows of their own,
  // and hands back the rest for GetDropFiles. Every frame installs its own, as
  // for keys: a drop on the editor lands in its iframe.
  //
  // Every file drop is cancelled whatever the page does with it: left to the
  // webview, it opens the file in place of the editor.
  //
  // WebKitGTK tells a page neither files nor names. A drag from a file manager
  // is a "text/uri-list" with no files, whose getData answers "" because the
  // URIs are file paths, so the host is asked for whatever the drag carried. A
  // link is the same type with a list that does read back, and sdkjs pastes it.
  const IMAGE_FILE = /\.(png|jpe?g|gif|bmp|tiff?|svg|webp|emf|wmf)$/i;
  let dropped = [];
  const carriesFiles = (e) => {
    const types = Array.from((e.dataTransfer && e.dataTransfer.types) || []);
    return types.includes("Files") || types.includes("text/uri-list");
  };
  w.addEventListener(
    "drop",
    (e) => {
      if (!carriesFiles(e)) return;
      e.preventDefault();
      const data = e.dataTransfer;
      const unnamed = !data.files.length;
      if (unnamed && data.getData("text/uri-list")) return;
      // WebView2 hands the paths over only in this message, which pywebview
      // posts from a drop handler of its own; there is none, so it is posted
      // here, before the host is asked for them.
      const webview2 = w.top.chrome && w.top.chrome.webview;
      if (webview2 && webview2.postMessageWithAdditionalObjects) {
        webview2.postMessageWithAdditionalObjects("FilesDropped", data.files);
      }
      const names = unnamed ? null : Array.from(data.files, (file) => file.name);
      dropped =
        answer(postToHostSync("/__host__/drop", JSON.stringify({ names }))).paths || [];
      // With no image to insert, sdkjs pastes the drop's text/html, and for
      // these WebKit makes that a link to the file. Its handler still has to
      // run, because it ends the drop target it showed, so it finds nothing.
      if (unnamed) Object.defineProperty(data, "getData", { value: () => "" });
    },
    true,
  );
  // Every file drag is accepted, on dragenter as on dragover: a move onto a
  // new element fires only dragenter, and WebKit answers that position from
  // it. A release after one, so anywhere with many small elements under the
  // pointer, was no drop at all on GTK. And it has to be said here, first, and
  // made to stick. Over the canvas, sdkjs answers "none" on dragover for any file
  // whose type is not an image's (CanDropFiles, isValidImageDragItem), and
  // with "none" there is no drop at all: a document dropped on the page never
  // arrived. A listener after it cannot undo that, because a handler on the
  // body stops the event there. So "copy" now, and the property pinned for the
  // rest of this event, which sdkjs then reads as "copy" too and shows where
  // an image would go. "copy" is also the cue: the pointer shows the drop
  // will be taken.
  const acceptFiles = (e) => {
    if (!carriesFiles(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    Object.defineProperty(e.dataTransfer, "dropEffect", {
      configurable: true,
      get: () => "copy",
      set: () => {},
    });
  };
  w.addEventListener("dragenter", acceptFiles, true);
  w.addEventListener("dragover", acceptFiles, true);

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
    dialog.setAttribute("aria-label", tr("Create New"));
    dialog.style.cssText =
      `background:${card};color:${text};border-radius:10px;` +
      "padding:18px 22px 22px;box-shadow:0 12px 40px rgba(0,0,0,.3);";
    const title = doc.createElement("div");
    title.textContent = tr("Create New");
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

  // -- signatures ------------------------------------------------------------
  //
  // The host signs and checks the file on disk (host/signing.py); the editor
  // shows what it is told. DesktopOfflineAppDocumentSignatures takes the list
  // as a JSON string, on open and after every change, and a signed document
  // stays read-only until a shorter list arrives: removing a signature changes
  // nothing in the editor by itself (sdkjs common/Local/common.js).
  function showSignatures(xhr) {
    if (xhr.status !== 200) {
      report("host", `the host could not list the signatures (HTTP ${xhr.status})`);
      return;
    }
    if (w.DesktopOfflineAppDocumentSignatures)
      w.DesktopOfflineAppDocumentSignatures(xhr.responseText);
  }

  // The answers to GetDefaultCertificate and SelectCertificate, an object with
  // a non-empty string id; "sertificate" is the editor's spelling.
  function answerCertificate(name, certificate) {
    if (w.OnNativeReturnCallback) w.OnNativeReturnCallback(name, certificate);
  }

  // A panel over the editor, as Create New's: the editor draws its own
  // dialogs in the page, and so does this one (decided 2026-11-01).
  function panel(titleText) {
    const doc = w.top.document;
    const dark =
      w.document.documentElement.classList.contains("theme-type-dark") ||
      (w.document.body?.classList.contains("theme-type-dark") ?? false);
    const [card, text, line] = dark
      ? ["#2a2a2a", "#e8e5e0", "#4a4a4a"]
      : ["#fff", "#1e1a17", "#d8d2c8"];
    const backdrop = doc.createElement("div");
    backdrop.className = "libera-panel";
    backdrop.style.cssText =
      "position:fixed;inset:0;z-index:100000;display:flex;align-items:center;" +
      "justify-content:center;background:rgba(0,0,0,.35);" +
      "font:13px system-ui,-apple-system,'Segoe UI',sans-serif;";
    const dialog = doc.createElement("div");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", titleText);
    dialog.style.cssText =
      `background:${card};color:${text};border-radius:10px;width:440px;` +
      "padding:18px 22px;box-shadow:0 12px 40px rgba(0,0,0,.3);";
    const title = doc.createElement("div");
    title.textContent = titleText;
    title.style.cssText = "font-weight:600;font-size:15px;margin-bottom:14px;";
    dialog.append(title);
    backdrop.append(dialog);
    // Esc closes, before the editor sees it, in its frame as here.
    const docs = [doc, w.document];
    const onKey = (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      close();
    };
    const close = () => {
      backdrop.remove();
      for (const d of docs) d.removeEventListener("keydown", onKey, true);
    };
    for (const d of docs) d.addEventListener("keydown", onKey, true);
    const button = (label, primary) => {
      const b = doc.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.style.cssText =
        `padding:6px 14px;border-radius:6px;border:1px solid ${line};font:inherit;` +
        (primary
          ? "background:#446995;color:#fff;border-color:#446995;"
          : `background:transparent;color:${text};`);
      return b;
    };
    const buttons = doc.createElement("div");
    buttons.style.cssText =
      "display:flex;justify-content:flex-end;gap:8px;margin-top:16px;";
    doc.body.append(backdrop);
    return { doc, dialog, buttons, button, close, line };
  }

  // A key file, its certificate when the key holds none, and the passphrase.
  // The files are chosen in the host's open dialog, which lets the host read
  // them; the passphrase goes to the host, which keeps it for this window.
  function chooseCertificate() {
    const p = panel(tr("Choose a Certificate"));
    const chosen = { key: "", cert: "" };
    const field = (labelText, which) => {
      const row = p.doc.createElement("div");
      row.style.cssText = "margin-bottom:10px;";
      const label = p.doc.createElement("div");
      label.textContent = labelText;
      label.style.cssText = "margin-bottom:4px;";
      const line = p.doc.createElement("div");
      line.style.cssText = "display:flex;gap:8px;align-items:center;";
      const name = p.doc.createElement("span");
      name.style.cssText =
        "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:.8;";
      name.dataset.file = which;
      const pick = p.button(tr("Choose…"));
      pick.dataset.choose = which;
      pick.addEventListener("click", () => {
        postToHost(
          "/__host__/choose-file",
          JSON.stringify({ filter: "certificates" }),
          (xhr) => {
            const path = answer(xhr).path || "";
            if (!path) return;
            chosen[which] = path;
            name.textContent = path.split(/[\\/]/).pop();
            name.title = path;
          },
        );
      });
      line.append(name, pick);
      row.append(label, line);
      p.dialog.append(row);
    };
    field(tr("Key file"), "key");
    field(tr("Certificate file, if the key file holds none"), "cert");
    const passLabel = p.doc.createElement("div");
    passLabel.textContent = tr("Passphrase");
    passLabel.style.cssText = "margin-bottom:4px;";
    const pass = p.doc.createElement("input");
    pass.type = "password";
    pass.autocomplete = "off";
    pass.style.cssText = `width:100%;box-sizing:border-box;padding:5px;border:1px solid ${p.line};border-radius:6px;font:inherit;`;
    const problem = p.doc.createElement("div");
    problem.setAttribute("role", "alert");
    problem.style.cssText = "color:#c0392b;min-height:1.3em;margin-top:8px;";
    const cancel = p.button(tr("Cancel"));
    const ok = p.button(tr("OK"), true);
    cancel.addEventListener("click", p.close);
    ok.addEventListener("click", () => {
      if (!chosen.key) {
        problem.textContent = tr("Choose a key file.");
        return;
      }
      const body = JSON.stringify({
        key: chosen.key,
        cert: chosen.cert,
        passphrase: pass.value,
      });
      postToHost("/__host__/certificate", body, (xhr) => {
        if (xhr.status === 200) {
          p.close();
          answerCertificate("on_signature_selectsertificate_ret", answer(xhr));
        } else if (xhr.status === 403) {
          problem.textContent = tr(
            "The key did not load: a wrong passphrase, or a file that is not a key.",
          );
        } else {
          problem.textContent = tr("The certificate could not be read.");
          report("host", `the host refused the certificate (HTTP ${xhr.status})`);
        }
      });
    });
    pass.addEventListener("keydown", (event) => {
      if (event.key === "Enter") ok.click();
    });
    p.buttons.append(cancel, ok);
    p.dialog.append(passLabel, pass, problem, p.buttons);
  }

  // ViewCertificate: who signed, who vouched for them, until when, and the
  // certificate itself as OpenSSL prints it.
  function showSigner(index) {
    getFromHost(`/__host__/signer?index=${encodeURIComponent(index)}`, (xhr) => {
      if (xhr.status !== 200) {
        report("host", `the host could not show the certificate (HTTP ${xhr.status})`);
        return;
      }
      const found = answer(xhr);
      const cert = found.certificate || {};
      const p = panel(tr("Certificate"));
      for (const text of [
        tr("Signed by {name}").replace("{name}", cert.name || ""),
        tr("Issued by {issuer}").replace("{issuer}", cert.issuer || ""),
        tr("Valid {dates}").replace("{dates}", cert.date || ""),
      ]) {
        const line = p.doc.createElement("div");
        line.textContent = text;
        line.style.cssText = "margin-bottom:4px;";
        p.dialog.append(line);
      }
      const pre = p.doc.createElement("pre");
      pre.textContent = found.text || "";
      pre.style.cssText = `max-height:240px;overflow:auto;font:11px ui-monospace,Menlo,monospace;border:1px solid ${p.line};border-radius:6px;padding:8px;`;
      const close = p.button(tr("Close"), true);
      close.addEventListener("click", p.close);
      p.buttons.append(close);
      p.dialog.append(pre, p.buttons);
      close.focus();
    });
  }

  // -- the editor -------------------------------------------------------------
  //
  // Its API, where the editor's own code puts it.
  const editorApi = () => (w.Asc && w.Asc.editor) || w.editor;

  // `fn(api)` once the editor exists. Only a frame ever has one: the top
  // window is api.js's page, which builds the editor's iframe and no editor,
  // and a wait there polled forty times a second for the window's life.
  function whenEditor(fn) {
    if (TAG === "top") return;
    const api = editorApi();
    if (api && api.asc_registerCallback) fn(api);
    else setTimeout(() => whenEditor(fn), 50);
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
  // Whether File > Protect is offered: the host says, from the document's
  // format. And the password the file on disk was last written with, which
  // the editor is given back when a save that carried another did not take.
  let protectable = false;
  let confirmed = "";
  // Whether the editor offers signatures: an OOXML file with no password, and
  // a payload with libera-sign (host/signing.is_signable).
  let signable = false;
  // The PDF editor, which reads the file itself and asks for its password.
  let readsItself = false;

  const currentBody = getFromHostSync("/__host__/current");
  if (currentBody) {
    const current = JSON.parse(currentBody);
    docPath = current.path || "";
    protectable = !!current.protectable;
    readsItself = !!current.readsItself;
    signable = !!current.signable;
  }

  // The password the PDF editor opened the PDF with: the host opens it with
  // that to save it, a save on close included, and gives the file the
  // editor's, which differs once File > Protect has changed it.
  function reportOpeningPassword() {
    const api = editorApi();
    confirmed = (api && api.currentPassword) || "";
    const body = JSON.stringify({ password: confirmed });
    postToHost("/__host__/opening-password", body, (xhr) => {
      if (xhr.status !== 204) {
        report(
          "error",
          `the host did not take the PDF's password (HTTP ${xhr.status})`,
        );
      }
    });
  }

  // The converted document, or the question of its password: x2t could not
  // open it without one (90), or not with the one typed (91). The editor's
  // dialog takes either code, and its answer is SetAdvancedOptions.
  function handOver(payload) {
    if (payload.needPassword) {
      w.asc_initAdvancedOptions(payload.needPassword);
      return;
    }
    // The password the host has for the document, a reload's above all: the
    // editor's is gone with its page, and each save carries the editor's,
    // so one it does not know would be saved as none. `true`: on open, which
    // saves nothing.
    const api = editorApi();
    confirmed = payload.password || "";
    if (payload.password && api && api.asc_setCurrentPassword) {
      api.asc_setCurrentPassword(payload.password, true);
    }
    setTimeout(() => {
      w.DesktopOfflineAppDocumentEndLoad(DOC_DIR, payload.b64, payload.len);
    }, 0);
  }

  const impl = {
    // --- lifecycle
    // Once per page, however many times the editor asks.
    //
    // The console shows it asked twice on every load, and the two handovers
    // were once blamed for the intermittent stall at "Loading document: 8%".
    // They were not its cause: that was a font request reset by the host's
    // listen backlog -- see Server.request_queue_size in listener.py. Handing
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
      // Someone else has the file open (their lock file says so). The editor's
      // locked mode has to be on before the document is ready: it then marks
      // the document read-only, says "locked for editing", and lets edits go
      // to a copy -- the host sends a plain Save to Save As (plan_save).
      // `true`: the host set it, so the editor does not report it back.
      const api = editorApi();
      if (w.LIBERA_LOCKED_BY && api && api.asc_setLocalRestrictions) {
        api.asc_setLocalRestrictions(w.Asc.c_oAscLocalRestrictionType.Locked, true);
      }
      handOver(payload);
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
      if (readsItself) reportOpeningPassword();
      if (signable) getFromHost("/__host__/signatures", showSignatures);
      // At once, not on the next one-second tick: it is the moment the
      // document is on screen, and build/src/libera_build/bench.py times it.
      sendReport();
      captureLater();
    },
    // The editor's own dirty flag, and the only reliable one: the change log
    // stays non-empty after a save, because it is the delta from the document
    // as it was opened. The host keeps it so that a crash -- or a window
    // closed without saving -- can be offered back on the next open.
    onDocumentModifiedChanged: function (m) {
      saved = !m;
      log("onDocumentModifiedChanged", arguments);
      postToHost("/__host__/modified", JSON.stringify({ modified: !!m }), (xhr) => {
        // Checked, as the change log is: a flag the host did not keep is a
        // crash with nothing offered back on the next open.
        if (xhr.status !== 204) {
          report(
            "error",
            `the host did not keep the unsaved mark (HTTP ${xhr.status})`,
          );
        }
      });
    },

    // --- save
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
    LocalFileSave: (params, password, _docinfo, fileType) => {
      // The document's password as the editor has it, "" for none: the host
      // saves under it (saving.SaveRequest).
      const body = JSON.stringify({
        fileType: fileType || 0,
        params: params || "",
        password: password || "",
      });
      postToHost("/__host__/save", body, (xhr) => {
        const reply = answer(xhr);
        // No reply, or one without an error code, is a failed save.
        const error = reply.error === undefined ? 2 : reply.error;
        if (error === 0) {
          saved = true;
          // Save As moves the document; keep the cached path in step without a
          // reload.
          docPath = reply.path || docPath;
          // Saved as text, the file has none, and the editor's would go to the
          // next Save As (saving._drops_password).
          confirmed = reply.protected ? password || "" : "";
          // A Save As leaves the signed file for one x2t wrote without its
          // signatures, or for a format that has none: the editor still shows
          // the old list, read-only, until it is sent the new one.
          if (signable) getFromHost("/__host__/signatures", showSignatures);
          const api = editorApi();
          if (password && !reply.protected && api && api.asc_setCurrentPassword)
            api.asc_setCurrentPassword("", true);
        } else if (protectable && (password || "") !== confirmed) {
          // File > Protect saves at once, and a save cancelled or failed left
          // the editor with a password the file never got: its next save would
          // write it unasked. The host has kept the file's (saving.py).
          const api = editorApi();
          if (api && api.asc_setCurrentPassword)
            api.asc_setCurrentPassword(confirmed, true);
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
        "text/plain",
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
    IsImageFile: (path) => IMAGE_FILE.test(String(path || "")),
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
    IsSignaturesSupport: () => signable,
    // File > Protect: set, change or remove a document's password.
    IsProtectionSupport: () => protectable,
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
    // The height allfontsgen draws each name at. The font menu reads its sprite
    // in rows of this many pixels times the scale, and shows each row this
    // high: at 26 every 28-pixel picture was squeezed, and lost lines of pixels.
    GetFontThumbnailHeight: () => 28,
    getDictionariesPath: () => "/dictionaries",

    // --- discovered by POC-0: sdk-all-min.js reads .length on the return of
    //     GetEncryptedHeader at load time, and web-apps asks for the font sprite.
    GetEncryptedHeader: () => "ENCRYPTED;",
    // The session's own pictures, which match its font list (bridge-page.js).
    getFontsSprite: (sfx) =>
      hostUrl(`/sdkjs/common/Images/fonts_thumbnail${sfx || ""}.png`),
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
      postToHost("/__host__/fullscreen", JSON.stringify({ on: !!on })),

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
    // The Wayland clipboard: sdkjs writes through it only when
    // _isNativeClipboardAvailable() also finds RendererProcessVariable.isWayland
    // and cefQuery, which this host defines neither of, so it is never called.
    // The check is in a helper, out of test_bridge_surface's sight.
    nativeClipboardWrite: () => undefined,

    CheckNeedWheel: () => true, // C++: always true (compat stub)
    LoadJS: () => 0,
    // The sign dialog's own picture, a file the user chose: synchronous, a
    // data: URL the dialog draws as it is.
    GetImageBase64: (path) =>
      getFromHostSync(
        `/__host__/image?path=${encodeURIComponent(String(path || ""))}`,
      ) || "",
    GetImageFormat: (p) =>
      String(p || "")
        .split(".")
        .pop(),
    // The paths of what the drop now being handled brought, which sdkjs asks
    // for from its own drop handler (AscCommon.InitDragAndDrop) and inserts
    // the images among. Once: the next drop starts from nothing.
    GetDropFiles: () => {
      const paths = dropped;
      dropped = [];
      return paths;
    },
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
      let request;
      try {
        request = JSON.parse(data);
      } catch (e) {
        report("error", `spellcheck: ${e}`);
        return;
      }
      // Add to dictionary. The worker handles only "spell" and "suggest" and
      // dropped this, so an added word was flagged again next session. The
      // editor re-checks the word itself straight after.
      if (request.type === "add") {
        (request.usrWords || []).forEach(addPersonalWord);
        return;
      }
      // Clear the user's dictionary: sdkjs can send it, nothing in the editor
      // does. Not the bare "clear" above, which abandons the queue; kept away
      // from the worker, which does not know it either.
      if (request.type === "clear") return;
      checker.command(request);
    },
    // The password the editor's dialog was given, as the editor writes it for
    // x2t's job: "<m_sPassword>...</m_sPassword>", escaped as XML. Never
    // logged. Cancelling the dialog closes the window instead.
    SetAdvancedOptions: (param) => {
      const job = new DOMParser().parseFromString(
        `<job>${param}</job>`,
        "application/xml",
      );
      const password = job.querySelector("m_sPassword");
      if (password === null) return;
      postToHost(
        "/__host__/password",
        JSON.stringify({ password: password.textContent }),
        (xhr) => {
          if (xhr.status === 200) handOver(answer(xhr));
          else
            report(
              "error",
              `the host could not open the document (HTTP ${xhr.status})`,
            );
        },
      );
    },
    // Signing a document with edits: it is signed as it is on disk, so the
    // host asks to save it first, and the editor saves, then signs.
    SaveQuestion: () => {
      postToHost("/__host__/save-question", "{}", (xhr) => {
        if (w.DesktopSaveQuestionReturn)
          w.DesktopSaveQuestionReturn(!!answer(xhr).save);
      });
    },
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
          // 1 is the save dialog cancelled, which is the user's answer, not a
          // failure: it alerted "could not print" all the same. No reply, or
          // one without an error code, is a failure, as LocalFileSave reads it.
          const error = answer(xhr).error;
          if (error !== 0 && error !== 1) {
            w.alert(tr("Libera Suite could not print this document."));
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
    GetDefaultCertificate: () => {
      getFromHost("/__host__/certificate", (xhr) => {
        answerCertificate("on_signature_defaultcertificate_ret", answer(xhr));
      });
    },
    SelectCertificate: () => chooseCertificate(),
    ViewCertificate: (index) => showSigner(index),
    Sign: (id, guid, imageValid, imageInvalid) => {
      const body = JSON.stringify({
        id: String(id || ""),
        guid: String(guid || ""),
        imageValid: String(imageValid || ""),
        imageInvalid: String(imageInvalid || ""),
      });
      postToHost("/__host__/sign", body, showSignatures);
    },
    RemoveSignature: (guid) => {
      const body = JSON.stringify({ guid: String(guid || "") });
      postToHost("/__host__/remove-signature", body, showSignatures);
    },
    RemoveAllSignatures: () => {
      postToHost(
        "/__host__/remove-signature",
        JSON.stringify({ guid: "" }),
        showSignatures,
      );
    },
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
      const asked = JSON.stringify({ filter: String(filter || "") });
      postToHost("/__host__/choose-file", asked, (xhr) => {
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
      answer(
        postToHostSync(
          "/__host__/media-import",
          JSON.stringify({ path: String(path || "") }),
        ),
      ).name || "",

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
        // File > Close. Ignored, it left the window open and only hid the
        // menu, which is all Back does; the host closes the window the way
        // its close button would, asking first about unsaved changes.
        if (action === "file:close") closeWindow();
        else if (action === "file:open") openDocument();
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
    const api = editorApi();
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

  // The arguments that carry a password, by method: logged as "(a password)",
  // since the log reaches the console and the host's report. LocalFileSave's
  // sixth, from Words and the PDF editor, is the password before the last
  // File > Protect (word/Local/api.js).
  const SECRET_ARGS = { LocalFileSave: [1, 5], SetAdvancedOptions: [0] };
  function redacted(name, args) {
    const shown = Array.from(args);
    for (const at of SECRET_ARGS[name] || []) {
      if (shown[at]) shown[at] = "(a password)";
    }
    return shown;
  }

  w.AscDesktopEditor = new Proxy(impl, {
    get: (t, k) => {
      if (k in t) {
        const v = t[k];
        return typeof v !== "function"
          ? v
          : function () {
              const r = v.apply(t, arguments);
              log(k, redacted(k, arguments), r);
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
  whenEditor((api) => {
    const send = (what) => (value) => {
      const state = {};
      state[what] = !!value;
      postToHost("/__host__/can", JSON.stringify(state));
    };
    api.asc_registerCallback("asc_onCanUndo", send("undo"));
    api.asc_registerCallback("asc_onCanRedo", send("redo"));
  });

  // The editor reports document trouble through its own asc_onError event and
  // a modal, not through a JS exception -- so a run can look clean to
  // window.onerror while the user is staring at "An error occurred during the
  // work with the document". Hook it. asc_registerCallback is a quoted export,
  // so it survives minification.
  whenEditor((api) => {
    api.asc_registerCallback("asc_onError", (code, level) => {
      report("asc_onError", `code=${code} level=${level}`);
    });
  });

  console.log(`[libera:${TAG}] bridge installed`);
})(window.__libera__);
