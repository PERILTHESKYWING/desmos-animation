#!/usr/bin/env node
// Publish a scene (render.js format) or a raw Desmos state as a desmos.com link.
// No account needed: uses the calculator's own "Share a Snapshot" button.
//
//   node scripts/share.js scene.json [--title "My graph"] [--state]
//
// With a scene that has a "clock", a ticker is added so the graph plays live:
//   T -> mod(T + dt/1000, seconds)
// Prints the https://www.desmos.com/calculator/<hash> link.
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const file = args[0];
  if (!file) { console.error('usage: share.js scene.json [--title t] [--state]'); process.exit(1); }
  const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  const ti = args.indexOf('--title'); const title = ti >= 0 ? args[ti + 1] : null;
  const isState = args.includes('--state') || (raw.expressions && raw.expressions.list);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('https://www.desmos.com/calculator', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForFunction(() => window.Calc && Calc.setState, null, { timeout: 90000 });
  await page.evaluate(({ raw, isState }) => {
    if (isState) { Calc.setState(raw, { allowUndo: false }); return; }
    const scene = raw;
    const isDef = l => /^[A-Za-z](_\{[^}]*\})?(\\left\([^=]*\\right\))?=/.test(l || '');
    const st = Calc.getState();
    st.graph = Object.assign({}, st.graph, { showGrid: false, showXAxis: false, showYAxis: false }, scene.graph || {});
    const list = scene.expressions.map((e, i) => Object.assign({ type: 'expression', id: 'e' + i, color: '#ffffff', hidden: isDef(e.latex) }, e));
    if (scene.folders) {  // optional: collapse heavy data into a closed folder so the list stays fast
      for (const [fid, title] of Object.entries(scene.folders)) list.unshift({ type: 'folder', id: fid, title, collapsed: true });
    }
    st.expressions = { list };
    const c = scene.clock;
    if (c && c.var && c.seconds) {
      st.expressions.ticker = { handlerLatex: `${c.var}\\to\\operatorname{mod}\\left(${c.var}+\\frac{\\operatorname{dt}}{1000},${c.seconds}\\right)`, open: true, playing: true };
    }
    Calc.setState(st, { allowUndo: false });
    if (scene.bounds) Calc.setMathBounds(scene.bounds);
  }, { raw, isState });
  if (title) await page.evaluate(t => { try { Calc._calc.globalHotkeys.mygraphsController.setGraphTitle?.(t); } catch (e) {} }, title);
  await page.waitForTimeout(3000);
  await page.click('[aria-label="Share Graph"]');
  await page.getByText('Share a Snapshot').click();
  const link = await page.waitForFunction(() => {
    const v = [...document.querySelectorAll('input,textarea')].map(i => i.value).find(v => /desmos\.com\/calculator\/\w+/.test(v));
    return v || null;
  }, null, { timeout: 120000 });
  console.log(await link.jsonValue());
  await browser.close();
})();
