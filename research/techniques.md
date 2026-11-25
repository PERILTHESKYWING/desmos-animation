# Technique catalogue

The working reference for building scenes. **Tested** means it was rendered headless with `scripts/render.js` in this repo (scenes in `research/tests/`). The source says where it was seen. Performance numbers are per frame at 960x540 on the cloud box.

Gojo vs Sukuna use is at the bottom.

## 0. Pipeline rules (all tested)

| Rule | Why |
|---|---|
| Load scenes with `Calc.setState`, never `setExpression(s)` | the public expression API silently drops `colorLatex`, so every colour variable is lost |
| Hide definitions (`A=...`, `f(x)=...`, point lists) | otherwise Desmos plots them: stray lines and dots. `render.js` hides them automatically |
| Multiply a number by a list with `\cdot` | `\frac{2\pi}{5}\left[0...4\right]` is read as *indexing* and errors |
| Index lists with `L\left[j\right]`, never `L_{j}` | `L_{j}` is a different variable name |
| No `for` inside parametrics producing point lists | "cannot store a list of points in a list". Broadcast a list inside instead |
| Lists cap at 10,000 elements | split polygons into chunks, or use a list of points (20k numbers) |
| Step the clock per captured frame | export is frame exact and independent of how slowly a frame draws |
| `?simulationFPS` / `?timeInWorker` URL flags show live cost | from the unofficial Desmos wiki |

## 1. Time and choreography

| Technique | Recipe | Source | Status |
|---|---|---|---|
| Scene window | `p = (T - t0)/(t1 - t0) {t0 <= T < t1}`, everything in the scene uses `p` | Unveil anim | seen |
| Scene gate | multiply by `Toggle`, undefined outside the window, costs nothing | Apotheosis | seen |
| Beat clock | `T += BPM/60 · dt` so cuts land on beats | Apotheosis | seen |
| Ease in/out | `E(x) = {0<x<1: 3x^2 - 2x^3, x<=0: 0, 1}` | many | **tested** (t2, t3) |
| 1D Bezier ease | `ease(x,a,b,c,d)` cubic with control values, clamped | Unveil anim | seen |
| Key poses + overshoot | smooth steps plus a damped spring `sin(4x) e^{-2x}/(1+e^{-5(x-0.4)})` per key | Hummingbird | seen |
| Keyframe tables | `Key(p, x)` linear interpolation over (time, value) points | Apotheosis | seen |
| Flash pulse | `e^{-k(T - t_hit)^2}` | Apotheosis | **tested** (t5) |
| Event lists | `{T >= times: values, -∞}` for hits and notes | Unveil anim | seen |

## 2. Drawing characters

| Technique | Recipe | Source | Status |
|---|---|---|---|
| Cel layers | base fill, shadow fills, specular highlights, lineart on top, one folder each | A System of Lights | seen |
| Traced polygons | `polygon(x_n, y_n)` from tables traced on a reference image | most entries | seen |
| **Image to polygons** | quantize to K colours, potrace each mask, one `polygon()` per colour with `0/0` breaks, holes by reversed rings | Steamboat Willie, our `img2desmos.py` | **tested**: 4 tones 24k points 0.3 s/frame, 12 colours 63k points 0.9 s/frame |
| Holes in one polygon | rings wound the opposite way are holes (nonzero fill) **only if every ring is closed** by repeating its first point | our test | **tested** |
| Lineart | thin curves or `fillOpacity 0` polygons with `lineWidth` | A System of Lights | seen |
| Shape morph (in-betweening) | equal-length point lists, `polygon((1-u)P_1 + uP_2)` | our test | **tested** (t3), 60 ms |
| Bezier strokes | `b_4(t, p0..p3)` per stroke, or tables of control points | Final Boss, Apotheosis | seen |
| Eye close-up | layered eyelid / iris / highlight polygons, scene inside the iris | silent scream | seen |

## 3. Secondary motion

| Technique | Recipe | Source | Status |
|---|---|---|---|
| Anchor-weighted sway | add `k(d) sin(ωT + phase)` to vertices, k grows with distance from root (hair, cape, fire, cloth) | In the Distance, A System of Lights | seen |
| Breathing | scale around centroid, `mean(x) + (x - mean(x))(1 + 0.02 sin T)` | A System of Lights | seen |
| Flicker / blink | `fillOpacity = a + b sin(T/0.08)` | A System of Lights | seen |
| Camera shake | offset bounds by `amp(T)(sin 53T, cos 47T)` | Apotheosis (as point offset) | **tested** via camera (t5) |

## 4. Effects

| Technique | Recipe | Source | Status |
|---|---|---|---|
| **Multi-colour in one expression** | list of polygons/points with `colorLatex` = list of colours, e.g. `hsv(30n, 0.8, 1)` | our test | **tested** (t1), 100 ms for 12 shapes + 12 points + 12 curves |
| Soft glow halo | 20 discs of growing radius at opacity 0.05-0.06 in one `for` | Final Boss | **tested** (t2), 100 ms |
| Glow stroke | `curve + 0·[1...10]`, `lineWidth = 6·[1...10]`, `lineOpacity 0.08` | Unveil | **tested** (t2) |
| Energy arcs | parametric between two points + `random(n, floor(30T))` jitter, re-seeded per frame | our test | **tested** (t2) |
| Particles | `random(N, seed)` positions, per-point `pointSize` and colour lists | Final Boss | **tested**: 2k points 125 ms, 9k points 240 ms |
| Speed lines | 90 thin triangles from a radius to off-screen, angles re-seeded every 2 frames | our test | **tested** (t5), 100 ms |
| White-out flash | full-screen `|x|>0` with pulse opacity | Apotheosis | **tested** (t5) |
| Gradient / vignette / fog | stacked growing rectangles or circles at opacity 0.01-0.03 | Final Boss, Unveil | seen |
| Blur | shifted or scaled duplicates at low opacity | Unveil, Final Boss | seen |
| Film grain | one `polygon(random(2400)...)` at opacity 0.015 | Cosmic Joyride | seen |
| Fire | three copies of a height-weighted wobbling polygon at opacity 1 / 0.2 / 0.1 | A System of Lights | seen |
| Sparks | hash-positioned circles, opacity `max(0, sin(2T + n))` | A System of Lights | seen |
| Noise terrain / clouds | cosine value noise over a fixed random list | Unveil | seen |
| Shatter | random-hash triangle polygons | Apotheosis | seen |

## 5. Camera and 3D

| Technique | Recipe | Source | Status |
|---|---|---|---|
| Camera moves | animate the viewport per frame (`Calc.setMathBounds`) for pan, zoom, shake | our renderer | **tested** (t5) |
| Perspective | `d(p) = 15 (p.x, p.y)/p.z {p.z>0}` plus rotation `R_3` | Apotheosis, Final Boss | seen |
| Isometric 3D bodies | surfaces of revolution projected with a fixed matrix | Hummingbird | seen |

## Performance budget (measured)

- Light effect scenes: 60-120 ms per frame. 30 fps x 60 s = 1,800 frames ≈ 3-4 minutes.
- Traced character, 12 colours, 63k points: about 1 s per frame. A minute of that is about 30 minutes of rendering.
- Heavy community graphs (Apotheosis): 5-25 s per frame. Avoid by gating scenes and keeping point counts down.
- Keep each scene under ~1,000 expressions (the wiki's threshold where FPS drops).

## Gojo vs Sukuna: what each beat needs

Two weeks means: trace or convert the characters instead of building them from formulas, and spend the maths on effects and motion.

| Beat | Techniques |
|---|---|
| Characters (Gojo, Sukuna), key poses | image to polygons from our own pose sketches or reference frames, cel layers, lineart pass |
| Poses in between | shape morph between key poses with equal point counts, eased; or hold poses anime-style (2s and 3s) with camera motion doing the work |
| Hair, coat, blindfold tails in wind | anchor-weighted sway |
| Gojo's eye reveal | eye close-up layers, glow halo on the iris, slow push-in camera |
| Blue / Red / Hollow Purple | glow halos, glow strokes, energy arcs, particles, merge with easing (t2 is a first draft) |
| Sukuna's slashes (Dismantle / Cleave) | thin white triangle slivers with motion streaks, shatter triangles, camera shake |
| Domain expansions | full-screen colour fades, radial speed lines, gradient backdrops, symbol rings via list comprehension, noise textures |
| Impacts | impact frame (t5): speed lines, white-out flash, inverted frame, shake |
| Atmosphere | grain, vignette, fog, sparks, embers |
| Timing | beat clock if there is music, scene windows, flash pulses on hits |
