// What the editor's page expects from a desktop host, and would otherwise get
// from CEF: rewritten media and font URLs, a localStorage that exists, a
// window.open that reaches a browser, a spell checker, and the canvas capture
// the regression harness photographs itself with.
//
// Loaded after bridge-runtime.js and before bridge-desktop.js.

((M) => {
  if (!M || M.page) return;
  const w = M.w;
  const { TAG, hostUrl, postToHost, report } = M;

  // -- ascdesktop://fonts/<id> ------------------------------------------------
  // sdkjs hard-codes this scheme in LoadFontAsync. A real host registers a
  // scheme handler (QWebEngineUrlSchemeHandler); here we just rewrite the URL,
  // which exercises the same code path.
  // -- localStorage ------------------------------------------------------------
  // pywebview's GTK/WebKit backend leaves window.localStorage (and indexedDB)
  // *undefined* rather than throwing. web-apps guards with
  // `try { return !!(ls = window.localStorage) } catch (e) { ...fallback... }`,
  // which only catches a throw -- so on Linux the fallback never installs and
  // the theme init dies on `localstorage.getItem`. Fill it in before anything
  // else runs. sessionStorage does exist there, and survives the reload that
  // File > New does.
  //
  // ponytail: aliased, not namespaced, so the two share a key space. Prefix if
  // that ever collides. Note it does not persist across restarts -- a real host
  // would back this with the server.
  if (!w.localStorage && w.sessionStorage) {
    Object.defineProperty(w, "localStorage", {
      value: w.sessionStorage,
      configurable: true,
    });
    console.log(`[libera:${TAG}] localStorage shimmed onto sessionStorage`);
  }

  // -- document media ---------------------------------------------------------
  // DesktopOfflineAppDocumentEndLoad forces the document URL to file://, and
  // images resolve against it, so an http-served page silently drops every
  // picture. The mapping lives on a minified-away global, but the image load
  // itself goes through HTMLImageElement.src, which is a stable browser API.
  const MEDIA = "file:///doc/media/";
  const srcDesc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  Object.defineProperty(HTMLImageElement.prototype, "src", {
    configurable: true,
    enumerable: true,
    get: srcDesc.get,
    set: function (v) {
      if (typeof v === "string" && v.indexOf(MEDIA) === 0) {
        v = hostUrl(`/__host__/media/${v.slice(MEDIA.length)}`);
      }
      srcDesc.set.call(this, v);
    },
  });

  const FONTS = "ascdesktop://fonts/";
  const open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (_method, url) {
    if (typeof url === "string" && url.indexOf(FONTS) === 0) {
      arguments[1] = hostUrl(`/__host__/fonts/${url.slice(FONTS.length)}`);
    }
    return open.apply(this, arguments);
  };

  function captureLater() {
    // Armed by the host (see host_get) only when a shot was requested; a real
    // window has no reason to photograph itself.
    if (!w.LIBERA_SHOT) return;
    // onDocumentContentReady fires before the first paint settles.
    w.setTimeout(captureCanvas, 1500);
  }

  function captureCanvas() {
    const all = w.document.getElementsByTagName("canvas");
    let best = null;
    for (let i = 0; i < all.length; i++) {
      if (!best || all[i].width * all[i].height > best.width * best.height)
        best = all[i];
    }
    if (!best || !best.width || !best.height) {
      return void report("error", "render capture: no canvas to photograph");
    }
    let png;
    try {
      png = best.toDataURL("image/png");
    } catch (e) {
      // A tainted canvas would mean the editor drew a cross-origin image.
      return void report("error", `render capture: ${e}`);
    }
    postToHost(
      "/__host__/shot",
      png.substring(png.indexOf(",") + 1),
      null,
      "text/plain",
    );
  }

  // Started on the first check rather than at load: a document nobody types in
  // never pays for the worker or the dictionary downloads.
  let checker = null;
  function spellChecker() {
    if (checker) return checker;
    if (typeof w.CSpellchecker !== "function") {
      report("error", "spellcheck: sdkjs/common/spell/spell.js is not loaded");
      return null;
    }
    checker = new w.CSpellchecker({
      enginePath: "/sdkjs/common/spell/spell",
      dictionariesPath: "/dictionaries",
    });
    checker.oncommand = (res) => {
      w.asc_nativeOnSpellCheck && w.asc_nativeOnSpellCheck(res);
    };
    return checker;
  }

  // WKWebView drops script-opened windows on the floor: pywebview forwards a
  // new window only when the navigation came from a clicked link, and
  // window.open() from script reports WKNavigationTypeOther. Every external
  // link the editor offers -- Suggest a feature, help, learn more -- is a
  // window.open(), so hand them to the host, which has a real browser.
  const nativeOpen = w.open;
  w.open = function (url) {
    if (typeof url === "string" && /^https?:\/\//i.test(url)) {
      postToHost("/__host__/open-url", url, null, "text/plain");
      return null;
    }
    return nativeOpen.apply(w, arguments);
  };

  // -- shortcuts the native menu already owns ---------------------------------
  // AppKit fires a menu item's key equivalent whether or not the page also
  // handles the key: the web view gets performKeyEquivalent: first, does not
  // claim Cmd-N, and the menu then fires too. Both ends make a window, so
  // Cmd-N made two.
  //
  // The menu bar is the canonical dispatcher on a Mac, so the page yields --
  // without *claiming* the key, which is the subtle part; see below.
  //
  // The list comes from the host, and menu.PAGE_YIELDS is where it is defined:
  // one definition for the menu item and for this, so changing the menu's
  // shortcut cannot leave the page yielding the wrong key. Empty on Linux,
  // whose menu bar carries no accelerators, and under `libera --serve`, which
  // has no menu bar at all.
  const OWNED = w.LIBERA_OWNED_KEYS || [];
  if (OWNED.length) {
    // On the window, capturing: the earliest phase there is, so it runs
    // before whatever the editor binds. Every frame installs its own, because
    // a keydown in the iframe never reaches the top document -- and the
    // editor is in the iframe.
    w.addEventListener(
      "keydown",
      (e) => {
        if (!e.metaKey || e.ctrlKey || e.altKey) return;
        const key = (e.key || "").toLowerCase();
        if (OWNED.some((o) => o.key === key && o.shift === e.shiftKey)) {
          // stopImmediatePropagation, and deliberately NOT preventDefault.
          //
          // They do opposite things here. stopImmediatePropagation stops the
          // editor's own handler, which is all we want. preventDefault marks
          // the event handled, and WKWebView reports that back to AppKit as
          // "the page took it" -- so the menu item never fires either and
          // Cmd-N does nothing at all. Calling both is how this was broken
          // the first time.
          e.stopImmediatePropagation();
        }
      },
      true,
    );
  }

  w.RendererProcessVariable = {
    theme: { id: "theme-light", type: "light", system: "light" },
    rtl: false,
  };

  // Ship what we saw back to the host, so the POC is checkable without a
  // human reading a console. Errors included -- those are the real signal.

  M.page = { captureLater, spellChecker };
})(window.__libera__);
