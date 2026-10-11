// Renders the raster brand assets from the SVG mark, so the PNGs Next serves
// (apple-icon and the Open Graph image) never drift from the logo component.
//
//   node scripts/render-brand-assets.mjs
//
// Needs network access once: the Open Graph card loads Prompt and Noto Sans
// Thai from Google Fonts so its text matches the app.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const iconSvg = readFileSync(resolve(appRoot, "src/app/icon.svg"), "utf8");

// The same geometry as PasaScopeLogoMark in src/components/pasascope-logo.tsx.
const markSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 88 56" width="264" height="168">
  <defs>
    <linearGradient id="bubble" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0A66D6"/><stop offset="1" stop-color="#2E9BE6"/>
    </linearGradient>
    <mask id="gap"><rect width="88" height="56" fill="#fff"/><circle cx="54" cy="24" r="22" fill="#000"/></mask>
  </defs>
  <path d="M20 4h10a18 18 0 0 1 18 18v2a18 18 0 0 1-18 18H22l-11 9 2.5-11.6A18 18 0 0 1 2 24v-2A18 18 0 0 1 20 4z" fill="url(#bubble)" mask="url(#gap)"/>
  <circle cx="54" cy="24" r="17" fill="#fff" stroke="#F0566A" stroke-width="5.5"/>
  <g stroke="#F0566A" stroke-width="3.2" stroke-linecap="round">
    <path d="M44 20v8"/><path d="M49 16.5v15"/><path d="M54 13v22"/><path d="M59 16.5v15"/><path d="M64 20v8"/>
  </g>
  <path d="M66.5 36.5 80 50" stroke="#F0566A" stroke-width="7" stroke-linecap="round"/>
</svg>`;

// iOS applies its own corner mask, so the apple icon is rendered full-bleed.
const appleIconHtml = `<!doctype html><html><body style="margin:0">${iconSvg.replace("<svg ", '<svg width="180" height="180" ').replace('rx="15"', 'rx="0"')}</body></html>`;

const openGraphHtml = `<!doctype html><html lang="th"><head>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@500;600&family=Noto+Sans+Thai:wght@400;500&display=block" rel="stylesheet">
<style>
  body { margin: 0; width: 1200px; height: 630px; background: #F4F8FD; font-family: "Noto Sans Thai", sans-serif; color: #16233F; overflow: hidden; position: relative; }
  .wave { position: absolute; border-radius: 50%; background: #DCEEFF; }
  .card { position: absolute; inset: 64px; border-radius: 40px; background: #FFFFFF; border: 2px solid #D9E6F5; box-shadow: 0 24px 60px rgba(30, 80, 160, 0.14); display: flex; align-items: center; gap: 56px; padding: 0 80px; }
  h1 { margin: 0; font: 600 92px/1 "Prompt", sans-serif; letter-spacing: -0.01em; }
  h1 span { color: #C22F47; }
  .thai { margin: 14px 0 0; font: 500 34px/1.3 "Prompt", sans-serif; color: #0A56B5; }
  .line { margin: 26px 0 0; font-size: 28px; line-height: 1.45; color: #42527A; max-width: 620px; }
</style></head><body>
  <div class="wave" style="width:900px;height:900px;left:-380px;top:260px"></div>
  <div class="wave" style="width:700px;height:700px;right:-300px;top:-420px"></div>
  <div class="card">
    ${markSvg}
    <div>
      <h1>Pasa<span>Scope</span></h1>
      <p class="thai">ภาษา-สโคป</p>
      <p class="line">Thai pediatric language-sample review for speech-language therapists. Decision support, not diagnosis.</p>
    </div>
  </div>
</body></html>`;

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ deviceScaleFactor: 1 });

  await page.setViewportSize({ width: 180, height: 180 });
  await page.setContent(appleIconHtml);
  await page.screenshot({ path: resolve(appRoot, "src/app/apple-icon.png") });

  await page.setViewportSize({ width: 1200, height: 630 });
  await page.setContent(openGraphHtml, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: resolve(appRoot, "src/app/opengraph-image.png") });
} finally {
  await browser.close();
}

console.log("Rendered src/app/apple-icon.png and src/app/opengraph-image.png");
