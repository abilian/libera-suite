#!/usr/bin/env python3
"""The Open Graph cards: the picture a link to the site shows when it is shared.

    uv run --project .. --with playwright python cards.py

One per edition, in its own language, from `card_tagline` and `card_line` in
editions.toml, written to src/assets/og/card-<lang>.jpg, which is where
overrides/main.html points og:image. 1200 by 630 is the size the networks crop
least.

The wordmark is figures/brand/wordmark-suite.svg, copied from the branding
repository like the application's icon; do not edit it here. Lato comes from
Google Fonts, so drawing the cards needs the network. Regenerate after changing
a tagline, the brand or the Words screenshot.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from string import Template

import tomllib
from playwright.sync_api import sync_playwright

DOCS = Path(__file__).parent
OUT = DOCS / "src" / "assets" / "og"

CARD = Template("""<!doctype html>
<meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=block">
<style>
  body { margin: 0; width: 1200px; height: 630px; overflow: hidden; position: relative;
         background: #F6F1E9; color: #1E1A17; font-family: Lato, sans-serif; }
  .text { position: absolute; left: 72px; top: 64px; width: 580px; }
  .wordmark { display: block; height: 80px; margin-left: -6px; }
  h1 { margin: 40px 0 18px; font-size: 54px; line-height: 1.08; color: #B5462B; }
  p { margin: 0; font-size: 26px; line-height: 1.35; color: #5E554E; }
  .formats { display: flex; gap: 10px; margin-top: 30px; }
  .formats span { padding: 6px 14px; border-radius: 8px; color: #F6F1E9;
                  font-size: 21px; font-weight: 700; }
  .words { background: #6F6BAD; }
  .tables { background: #00877C; }
  .slides { background: #A28137; }
  .url { position: absolute; left: 72px; bottom: 40px;
         font-size: 22px; font-weight: 700; }
  .shot { position: absolute; left: 690px; top: 96px; width: 760px; border-radius: 16px;
          box-shadow: 0 24px 64px rgba(30, 26, 23, 0.28); }
</style>
<div class="text">
  <img class="wordmark" src="$wordmark" alt="">
  <h1>$tagline</h1>
  <p>$line</p>
  <div class="formats">
    <span class="words">.docx</span><span class="words">.odt</span>
    <span class="tables">.xlsx</span><span class="tables">.ods</span>
    <span class="slides">.pptx</span><span class="slides">.odp</span>
  </div>
</div>
<img class="shot" src="$shot" alt="">
<div class="url">docs.liberasuite.eu</div>
""")


def data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def main() -> None:
    editions = tomllib.loads((DOCS / "editions.toml").read_text("utf-8"))
    images = {
        "wordmark": data_uri(
            DOCS / "figures/brand/wordmark-suite.svg", "image/svg+xml"
        ),
        "shot": data_uri(DOCS / "src/assets/words.png", "image/png"),
    }
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        for lang, strings in editions.items():
            page.set_content(
                CARD.substitute(
                    images,
                    tagline=html.escape(strings["card_tagline"]),
                    line=html.escape(strings["card_line"]),
                ),
                wait_until="networkidle",
            )
            page.evaluate("document.fonts.ready")
            out = OUT / f"card-{lang}.jpg"
            page.screenshot(path=out, type="jpeg", quality=88)
            print(f"cards: {out.relative_to(DOCS)}")
        browser.close()


if __name__ == "__main__":
    main()
