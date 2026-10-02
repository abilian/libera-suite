// The header's language selector, made to land on the same page.
//
// Zensical renders one link per edition, each pointing at that edition's
// root: /en/, /fr/, /de/ and so on. Switching from /en/main/install/ would
// land on /fr/. This rewrites each link to the same page in the other edition,
// which exists because preprocess.py refuses to build editions whose pages
// differ. The one exception is develop/, which is English-only: from there,
// the other editions' links stay at their roots.
//
// A choice made here is remembered in a cookie, for the whole site, and the
// chooser at the site root (docs/index.html) goes straight to it next time.
//
// `zensical serve` serves one edition on its own, so there is nothing to switch
// to. When the current path is under no edition's prefix, the selector is
// hidden rather than left pointing at pages that are not there; `make preview`
// serves the whole site, where it works.
(function () {
  var COOKIE = "libera-docs-lang";
  var ENGLISH_ONLY = "develop/";

  function remember(lang) {
    document.cookie =
      COOKIE + "=" + lang + "; path=/; max-age=31536000; SameSite=Lax";
  }

  function hide(links) {
    Array.prototype.forEach.call(links, function (link) {
      var option = link.closest(".md-header__option");
      if (option) option.hidden = true;
    });
  }

  function rewrite() {
    var links = document.querySelectorAll("a.md-select__link[hreflang]");
    if (!links.length) return;
    var editions = Array.prototype.map.call(links, function (link) {
      return {
        link: link,
        lang: link.getAttribute("hreflang"),
        base: new URL(link.getAttribute("href"), location.href).pathname,
      };
    });

    var here = editions.filter(function (edition) {
      return location.pathname.indexOf(edition.base) === 0;
    })[0];
    if (!here) {
      hide(links);
      return;
    }

    var rest = location.pathname.slice(here.base.length);
    var englishOnly = rest.indexOf(ENGLISH_ONLY) === 0;
    editions.forEach(function (edition) {
      if (!englishOnly) {
        edition.link.setAttribute("href", edition.base + rest + location.hash);
      }
      edition.link.addEventListener("click", function () {
        remember(edition.lang);
      });
    });
  }

  rewrite();
  // navigation.instant swaps pages without a reload and rebuilds the header,
  // so the links are rewritten after every swap.
  if (window.document$ && window.document$.subscribe) {
    window.document$.subscribe(rewrite);
  }
})();
