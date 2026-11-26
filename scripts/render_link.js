#!/usr/bin/env node
// Render every frame of a video_link.py state (what the playable link shows) to PNGs.
//   node scripts/render_link.js state.json out_dir [--size 1920x1080]
// Steps k = 1..M with the ticker stopped and captures the state's viewport exactly.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
(async () => {
  const [file, out, ...rest] = process.argv.slice(2);
  const si = rest.indexOf('--size'); const [W, H] = (si >= 0 ? rest[si + 1] : '1920x1080').split('x').map(Number);
  const st = JSON.parse(fs.readFileSync(file, 'utf8'));
  st.expressions.ticker.playing = false;
  const v = st.graph.viewport; const mb = { left: v.xmin, right: v.xmax, bottom: v.ymin, top: v.ymax };
  const M = +st.expressions.list.find(e => e.id === 'k').slider.max;
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('https://www.desmos.com/calculator', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForFunction(() => window.Calc && Calc.setState, null, { timeout: 90000 });
  await page.evaluate(s => Calc.setState(s, { allowUndo: false }), st);
  const t0 = Date.now();
  for (let k = 1; k <= M; k++) {
    const uri = await page.evaluate(async ({ k, mb, W, H }) => {
      Calc.setExpression({ id: 'k', latex: 'k=' + k });
      return await new Promise(r => Calc.asyncScreenshot({ width: W, height: H, targetPixelRatio: 1, mode: 'stretch', mathBounds: mb }, r));
    }, { k, mb, W, H });
    fs.writeFileSync(path.join(out, `k${String(k).padStart(4, '0')}.png`), Buffer.from(uri.split(',')[1], 'base64'));
  }
  const errs = await page.evaluate(() => Object.values(Calc.expressionAnalysis || {}).filter(x => x.isError).length);
  console.log('frames', M, 'errors', errs, 'avg ms', Math.round((Date.now() - t0) / M));
  await browser.close();
})();
