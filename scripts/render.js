#!/usr/bin/env node
// Render a scene file to PNG frames using the real desmos.com calculator (no API key).
//
//   node scripts/render.js scene.json out/prefix [--frames 0:10] [--only 3]
//
// scene.json:
// {
//   "size": [960, 540],
//   "bounds": {"left": -16, "right": 16, "bottom": -9, "top": 9},
//   "settings": {"showGrid": false, "showXAxis": false, "showYAxis": false},
//   "expressions": [ {"id": "T", "latex": "T=0"}, {"latex": "...", "color": "#fff", ...} ],
//   "clock": {"var": "T", "fps": 30, "seconds": 2},          // T steps by 1/fps
//   "camera": "optional latex-free JS expression of T returning bounds, e.g.
//              \"({left:-16+T, right:16+T, bottom:-9, top:9})\""
// }
// Prints per-frame ms and a summary so performance can be compared between techniques.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');

(async () => {
  const [scenePath, outPrefix, ...rest] = process.argv.slice(2);
  if (!outPrefix) { console.error('usage: render.js scene.json out/prefix [--frames a:b] [--only n]'); process.exit(1); }
  const scene = JSON.parse(fs.readFileSync(scenePath, 'utf8'));
  const [W, H] = scene.size || [960, 540];
  const clock = scene.clock || { var: 'T', fps: 1, seconds: 0 };
  const total = Math.max(1, Math.round(clock.fps * clock.seconds) + 1);
  let [a, b] = [0, total];
  const fi = rest.indexOf('--frames'); if (fi >= 0) [a, b] = rest[fi + 1].split(':').map(Number);
  const oi = rest.indexOf('--only'); if (oi >= 0) { a = +rest[oi + 1]; b = a + 1; }
  fs.mkdirSync(path.dirname(outPrefix), { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.on('pageerror', e => console.error('page error', e.message));
  await page.goto('https://www.desmos.com/calculator', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForFunction(() => window.Calc && Calc.setExpressions, null, { timeout: 90000 });
  const t0 = Date.now();
  const errs = await page.evaluate(async (scene) => {
    // setState, not setExpressions: the public setExpression API silently drops
    // state-only fields such as colorLatex (colour from an expression).
    const st = Calc.getState();
    st.graph = Object.assign({}, st.graph, { showGrid: false, showXAxis: false, showYAxis: false }, scene.graph || {});
    // Definitions like `A=(1,2)`, `P=[...]` or `E(x)=...` would be drawn too; hide them
    // unless the scene says "hidden": false explicitly.
    const isDef = l => /^[A-Za-z](_\{[^}]*\})?(\\left\([^=]*\\right\))?=/.test(l || '');
    st.expressions = { list: scene.expressions.map((e, i) => Object.assign(
      { type: 'expression', id: 'e' + i, color: '#ffffff', hidden: isDef(e.latex) }, e)) };
    Calc.setState(st, { allowUndo: false });
    if (scene.settings) Calc.updateSettings(scene.settings);
    if (scene.bounds) Calc.setMathBounds(scene.bounds);
    await new Promise(r => Calc.asyncScreenshot({ width: 64, height: 36 }, r));
    // report expressions that failed to evaluate
    const a = Calc.expressionAnalysis || {};
    return Object.entries(a).filter(([, v]) => v.isError).map(([k, v]) => k + ': ' + v.errorMessage);
  }, scene);
  if (errs.length) console.error('expression errors:\n  ' + errs.join('\n  '));
  console.log('setup', Date.now() - t0, 'ms');

  const times = [];
  for (let i = a; i < Math.min(b, total); i++) {
    const T = clock.seconds ? i / clock.fps : 0;
    const t1 = Date.now();
    const uri = await page.evaluate(async ({ T, clock, cam, W, H }) => {
      if (clock.var) Calc.setExpression({ id: clock.var, latex: `${clock.var}=${T.toFixed(5)}` });
      if (cam) Calc.setMathBounds((new Function('T', 'return ' + cam))(T));
      return await new Promise(r => Calc.asyncScreenshot({ width: W, height: H, targetPixelRatio: 1, mode: 'stretch', mathBounds: Calc.graphpaperBounds.mathCoordinates }, r));
    }, { T, clock, cam: scene.camera, W, H });
    fs.writeFileSync(`${outPrefix}_${String(i).padStart(4, '0')}.png`, Buffer.from(uri.split(',')[1], 'base64'));
    times.push(Date.now() - t1);
  }
  const avg = times.reduce((s, x) => s + x, 0) / Math.max(1, times.length);
  console.log(`frames ${times.length}  avg ${avg.toFixed(0)} ms  max ${Math.max(...times)} ms`);
  await browser.close();
})();
