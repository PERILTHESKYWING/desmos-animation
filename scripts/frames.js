#!/usr/bin/env node
// Render frames of any saved Desmos graph by setting its variables, no API key.
//
//   node scripts/frames.js <hash> <out-prefix> '<plan json>' [width height]
//
// plan = [[{"a": 5, "k": 3}, "label"], ...]  Each entry sets existing variables
// (matched by "name=" at the start of an expression), waits for the graph to
// settle via Calc.asyncScreenshot, and writes <out-prefix>_NNN.png.
// Then: ffmpeg -framerate 30 -i out_%03d.png -pix_fmt yuv420p out.mp4
//
// Needs Playwright with Chromium (preinstalled in the cloud env:
// NODE_PATH=$(npm root -g) node scripts/frames.js ...).
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const [hash, out, spec, w = '960', h = '540'] = process.argv.slice(2);
  if (!spec) { console.error('usage: frames.js <hash> <out-prefix> <plan-json> [w h]'); process.exit(1); }
  const plan = JSON.parse(spec.startsWith('@') ? fs.readFileSync(spec.slice(1), 'utf8') : spec);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto('https://www.desmos.com/calculator/' + hash, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForFunction(() => window.Calc && Calc.getState, null, { timeout: 90000 });
  await page.waitForTimeout(2000);
  for (let i = 0; i < plan.length; i++) {
    const [vals, label = ''] = plan[i];
    const t0 = Date.now();
    const uri = await page.evaluate(async ({ vals, w, h }) => {
      const ex = Calc.getExpressions();
      for (const [k, v] of Object.entries(vals)) {
        const e = ex.find(e => e.latex && e.latex.replace(/\s/g, '').startsWith(k + '='));
        if (!e) throw new Error('no variable ' + k);
        Calc.setExpression({ id: e.id, latex: k + '=' + v });
      }
      return await new Promise(r => Calc.asyncScreenshot({ width: w, height: h, targetPixelRatio: 1, mode: 'preserveX' }, r));
    }, { vals, w: +w, h: +h });
    fs.writeFileSync(`${out}_${String(i).padStart(3, '0')}.png`, Buffer.from(uri.split(',')[1], 'base64'));
    console.log(i, label, Date.now() - t0, 'ms');
  }
  await browser.close();
})();
