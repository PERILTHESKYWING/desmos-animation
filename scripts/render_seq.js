#!/usr/bin/env node
// Render a directory of per-frame scenes (video2desmos.py output) with one browser.
//
//   node scripts/render_seq.js scenes_dir out_dir [--from 1 --to 180]
//
// Each fNNNN.json is loaded with Calc.setState and captured with asyncScreenshot.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');

(async () => {
  const [dir, out, ...rest] = process.argv.slice(2);
  const opt = k => { const i = rest.indexOf(k); return i >= 0 ? +rest[i + 1] : null; };
  fs.mkdirSync(out, { recursive: true });
  let files = fs.readdirSync(dir).filter(f => /^f\d+\.json$/.test(f)).sort();
  const from = opt('--from'), to = opt('--to');
  files = files.filter(f => { const n = +f.slice(1, 5); return (!from || n >= from) && (!to || n <= to); });
  let browser, page, base;
  const open = async () => {  // (re)open: heavy frames can crash the renderer tab
    if (browser) await browser.close().catch(() => {});
    browser = await chromium.launch();
    page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await page.goto('https://www.desmos.com/calculator', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForFunction(() => window.Calc && Calc.setState, null, { timeout: 90000 });
    base = await page.evaluate(() => Calc.getState());
  };
  await open();
  let total = 0;
  for (const f of files) {
    if (fs.existsSync(path.join(out, f.replace('.json', '.png')))) continue;  // resume
    const scene = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const [W, H] = scene.size;
    const t0 = Date.now();
    let res;
    for (let attempt = 0; attempt < 3 && !res; attempt++) {
      try { res = await page.evaluate(async ({ scene, base, W, H }) => {
      const st = JSON.parse(JSON.stringify(base));
      st.graph = Object.assign({}, st.graph, { showGrid: false, showXAxis: false, showYAxis: false });
      st.expressions = { list: scene.expressions.map((e, i) => Object.assign({ type: 'expression', id: 'e' + i, color: '#ffffff' }, e)) };
      Calc.setState(st, { allowUndo: false });
      Calc.setMathBounds(scene.bounds);
      const uri = await new Promise(r => Calc.asyncScreenshot({ width: W, height: H, targetPixelRatio: 1, mode: 'stretch', mathBounds: scene.bounds }, r));
      const errs = Object.entries(Calc.expressionAnalysis || {}).filter(([, v]) => v.isError).map(([k, v]) => k + ': ' + v.errorMessage);
      return { uri, errs };
    }, { scene, base, W, H }); }
      catch (e) { console.error(f, 'attempt', attempt + 1, e.message.split('\n')[0]); await open(); }
    }
    if (!res) { console.error(f, 'FAILED'); continue; }
    if (res.errs.length) console.error(f, 'errors:', res.errs.slice(0, 3).join(' | '));
    fs.writeFileSync(path.join(out, f.replace('.json', '.png')), Buffer.from(res.uri.split(',')[1], 'base64'));
    const ms = Date.now() - t0; total += ms;
    console.log(f, ms, 'ms');
  }
  console.log('avg', Math.round(total / Math.max(1, files.length)), 'ms');
  await browser.close();
})();
