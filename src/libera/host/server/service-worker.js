// The editor's service worker, as Libera Suite serves it: one that caches nothing.
//
// The editor registers /document_editor_service_worker.js at the origin root,
// and upstream's worker answers every web-apps/, sdkjs/ and fonts/ request
// cache-first, from a cache named after a version it reads out of its own URL
// path. DocumentServer serves it under a version directory; this host serves
// it at the root, so the version was always the default "0.0.0-0" and every
// payload shared one cache for good.
//
// That broke on the files a payload generates on the machine it is installed
// on. Upstream's worker exempts AllFonts.js for its desktop editor, which it
// recognises by an "AscDesktopEditor" user agent; ours is a plain WebView, so
// a freshly installed payload with 32 web fonts ran on a cached index of 188,
// asked for fonts that were not there, and never drew the document. On every
// platform, not only Windows.
//
// Nothing here is worth caching in the first place: the files come from this
// machine over loopback, and the host marks them for revalidation by ETag.
// So no fetch handler -- every request goes to the host -- and on activation
// the caches the old worker filled are deleted. Browsers compare the worker
// script on navigation, so an installation that already has the old one
// replaces it by itself.

const CACHE_PREFIXES = ["document_editor_static_", "document_editor_dynamic_"];

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys()) {
        if (CACHE_PREFIXES.some((prefix) => name.startsWith(prefix))) {
          await caches.delete(name);
        }
      }
      await self.clients.claim();
    })(),
  );
});
