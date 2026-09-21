// The bridge's plumbing: who we are, how we reach the host, what we report.
//
// Three files, served in this order and sharing one namespace rather than one
// closure, so a stack trace names a real file:
//
//     bridge-runtime.js   this -- session, transport, logging, reporting
//     bridge-page.js      shims the editor's page needs from a desktop host
//     bridge-desktop.js   window.AscDesktopEditor itself
//
// Plain scripts, not modules: the editor must find AscDesktopEditor already
// there when its own code runs, and a module is deferred.

((w) => {
  if (w.__libera__) return;

  const TAG = w === w.top ? "top" : "frame";

  // Which window's document this frame belongs to. The editor loads itself in
  // an iframe and forwards only the parameters it knows about, so the session
  // never reaches the inner frame's URL -- but the frames are same-origin, so
  // the top window's search string is readable from either.
  const SESSION = (() => {
    try {
      const m = /[?&]session=([^&]*)/.exec(w.top.location.search);
      return m ? m[1] : "";
    } catch (_e) {
      return "";
    }
  })();

  // Every /__host__/ URL goes through here: a request about a document has to
  // reach the session that holds it.
  function hostUrl(path) {
    if (!SESSION) return path;
    return `${path + (path.indexOf("?") === -1 ? "?" : "&")}session=${SESSION}`;
  }

  // ...and every host call goes through one of these. The five-line
  // XMLHttpRequest dance was written out at a dozen call sites, which is a
  // dozen chances to get the session, the content type or the error handling
  // subtly different from the others.
  //
  // XMLHttpRequest throughout, and staying that way: four of these calls are
  // synchronous because the editor makes them expecting the work to be
  // finished when the call returns, and fetch cannot do that. One idiom that
  // covers every case beats two that each cover half.

  function getFromHost(path, done) {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", hostUrl(path), true);
    if (done) xhr.onloadend = () => done(xhr);
    xhr.send(null);
  }

  function postToHost(path, body, done, contentType) {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", hostUrl(path), true);
    xhr.setRequestHeader("Content-Type", contentType || "application/json");
    if (done) xhr.onloadend = () => done(xhr);
    xhr.send(body === undefined ? null : body);
  }

  function getFromHostSync(path) {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", hostUrl(path), false);
    xhr.send(null);
    return xhr.status === 200 ? xhr.responseText : null;
  }

  function postToHostSync(path, body) {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", hostUrl(path), false);
    xhr.send(body === undefined ? null : body);
    return xhr;
  }

  // A reply the host could not give, or gave as something other than JSON, is
  // the same as no reply: every caller here has a sensible default for it.
  function answer(xhr) {
    try {
      return JSON.parse(xhr.responseText) || {};
    } catch (_e) {
      return {};
    }
  }

  // Did the host put the document in *this* window? Opening a document gets
  // it a window of its own, and reloading this one would then throw away
  // whatever is open here -- which is the bug that made windows necessary.
  // Only a host with nowhere else to put it answers "here".
  function openedHere(xhr) {
    return !!answer(xhr).here;
  }
  // One log for the whole window, shared by every frame's bridge.
  w.top.__libera_calls = w.top.__libera_calls || [];
  const calls = w.top.__libera_calls;

  function preview(args) {
    return Array.prototype.map
      .call(args, (a) => {
        const s = typeof a === "string" ? a : a === null ? "null" : typeof a;
        return s.length > 60 ? `${s.slice(0, 60)}\u2026` : s;
      })
      .join(", ");
  }

  function log(name, args, ret) {
    const p = preview(args);
    calls.push({ frame: TAG, name: name, args: p });
    console.log(
      "[libera:" +
        TAG +
        "] " +
        name +
        "(" +
        p +
        ")" +
        (ret === undefined ? "" : ` -> ${ret}`),
    );
  }

  const out = [];
  function report(kind, text) {
    out.push({ frame: TAG, kind: kind, text: String(text) });
  }
  w.addEventListener("error", (e) => {
    report("error", `${e.message || e.type} @ ${e.filename || "?"}:${e.lineno || 0}`);
  });
  w.addEventListener("unhandledrejection", (e) => {
    report("reject", e.reason);
  });
  const _err = console.error;
  console.error = function () {
    report("console.error", Array.prototype.join.call(arguments, " "));
    _err.apply(console, arguments);
  };

  setInterval(() => {
    if (!out.length && !calls.length) return;
    postToHost(
      "/__host__/report",
      JSON.stringify({ events: out.splice(0), calls: calls.splice(0) }),
    );
  }, 1000);

  // The editor reports document trouble through its own asc_onError event and
  // a modal, not through a JS exception -- so a run can look clean to
  // window.onerror while the user is staring at "An error occurred during the
  // work with the document". Hook it. asc_registerCallback is a quoted export,
  // so it survives minification.
  // Tell the host what the editor can do, so the menu bar can grey out an
  // item that would decline. Pushed, not asked for: a menu is validated on the
  // GUI thread, and asking the editor from there would deadlock.

  // Everything the other two files need from this one. A namespace rather
  // than a closure, because they are separate scripts.
  w.__libera__ = {
    w,
    TAG,
    SESSION,
    hostUrl,
    getFromHost,
    postToHost,
    postToHostSync,
    getFromHostSync,
    answer,
    openedHere,
    log,
    report,
    calls,
  };
})(window);
