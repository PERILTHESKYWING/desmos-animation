# Reusable lessons from the example graphs

Distilled from four dissections (see `dissections/`). This list is the seed for the skill's technique files. Each item names the graph it was verified in.

## Pipeline (verified in this repo)

- **Get any graph's state with one GET**, no key and no browser: `curl -H 'Accept: application/json' https://www.desmos.com/calculator/<hash>` returns title, metadata and the full `state`. `scripts/fetch.py` wraps it and prints a technique fingerprint.
- **Render with the real calculator**, no key: headless Chromium on `desmos.com/calculator/<hash>` exposes `window.Calc`. Change a variable by editing its existing expression id (adding a second `a=` makes a "defined twice" error), then `Calc.asyncScreenshot`, which waits for the graph to settle. `scripts/frames.js` does this.
- Measured: light graphs ~1.7 s per frame at 960x540, heavy ones (Apotheosis) 5 to 25 s. A 30 fps, 60 s video of a heavy scene is hours, so quality knobs matter.
- 96 frames of Steamboat Willie took 2.7 minutes and became a clean mp4 with ffmpeg.

## Time and structure

1. **One clock, many scene windows.** `sceneP = (T - t0)/(t1 - t0) {t0 <= T < t1}`; everything in the scene uses `sceneP`. Outside the window it is undefined and the scene vanishes. (Unveil, Apotheosis)
2. **Gate whole scenes** by multiplying by a toggle that is undefined outside a window. Off-screen scenes then cost nothing. (Apotheosis `Toggle`)
3. **Clock in beats when there is music**: `T` advances by `BPM/60 · dt`. Cuts land on beats for free. (Apotheosis)
4. **Ease everything.** 1D cubic Bezier `ease(x,a,b,c,d)`, `median(0,1,x)` clamps, `tanh` or logistic steps, `e^{-k(x-c)^2}` pulses for flashes. (all)
5. **Export by stepping, not by playing.** Advance the clock by exactly `1/fps` per captured frame. (Apotheosis `RENDER` action; our `frames.js`)
6. **Plan the timeline first, build scenes in separate graphs, then merge** with re-keyed ids. (Unveil process doc)
7. **Folder order is draw order.** One folder per layer, back to front. (Final Boss)
8. **Shared helper library**: rotate, 3D projection, Bezier, lerp, keyframes, palette. Every serious graph has one. (all)

## Look

9. **Everything soft is stacked copies at low opacity**: glow (list of line widths), blur (shifted or scaled copies), gradients (list of growing rectangles or circles), fog, bloom, vignette. One generator covers all of them. (all)
10. **`0·[1...N]` broadcast**: add it to a point to get N copies, then give `lineWidth` a list. (Unveil)
11. **Polygons over parametrics** for speed; sample curves at N points with a global quality slider. (Final Boss)
12. **`0/0` breaks** pack many disjoint shapes into one expression. (Final Boss, Steamboat Willie)
13. **List comprehension** `[polygon(...) for n=[1...N]]` makes particle systems, crowds and waves in one line. (Final Boss, Apotheosis)
14. **Palette as `hsv()` variables** used through `colorLatex`, so colours can be animated (lightning flash brightens the sky). (Apotheosis, Unveil)
15. **Perspective 3D** is one function: `15 (x, y)/z {z>0}` plus a rotation. (Apotheosis, Final Boss, Unveil)
16. **Pixel-relative widths**: `l = width/k`, widths as multiples of `l`. (Apotheosis, Final Boss)
17. **Full-screen fills**: `|x| > 0` or a huge `polygon` square for backgrounds, flashes and fades. (Unveil, Apotheosis)
18. **Noise**: cosine-interpolated value noise over a fixed pasted random list gives stable organic shapes; `random(n, seed)` with a time-based seed gives jitter. (Unveil, Apotheosis)
19. **Camera shake**: add `amp(t) (sin 23t, cos 31t)` to every point. (Apotheosis)

## Image and video input

20. **Filled, posterized layers** (quantize to K tones, one `polygon()` per tone with `0/0` breaks) look like art and stay playable. Outline tracing (DesmosBezierRenderer) gives double-line sketches and thousands of expressions. (Steamboat Willie vs. DesmosBezierRenderer)
21. **Frame lists**: `[f_1, ..., f_n][k]` plus a ticker `k -> {k=n: 1, k+1}` is the cheapest frame-by-frame animation. (Steamboat Willie)
22. Hide heavy definitions in a collapsed folder so Desmos does not typeset them. (Steamboat Willie)

## Not worth copying for our offline renderer

- ImageMode / pre-rendered PNG swaps (Final Boss): only needed for live playback in a browser.
- Real-time tickers for playback: we capture frame by frame instead.
