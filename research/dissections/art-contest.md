# Math Art Contest galleries, 2022-2025

The galleries at desmos.com/art-2022 ... art-2025 feature 195 graphs (20 per age group per year). The pages load client side, so I listed them with headless Chromium, then fetched 182 states with `scripts/fetch.py` (13 were Geometry-tool graphs that return 404). 108 are marked animated.

## What the whole corpus uses (182 graphs)

| Feature | Share |
|---|---|
| inequality regions | 100% |
| colour variables (`rgb`/`hsv`) and `colorLatex` | 95% |
| `polygon()` | 63% |
| animated sliders | 53% |
| `mod`/`floor` | 50% |
| actions (`->`) | 46% |
| list comprehension (`for`) | 40% |
| `sort`/`join` | 40% |
| tables | 32% |
| ticker | 31% |
| `random()` | 30% |
| `with` | 19% |
| images | 18% |
| Bezier helpers | 6% |

Takeaway: entries are mostly hand-placed polygons and inequalities. The advanced machinery (Bezier libraries, 3D, beat clocks) lives in a handful of graphs, mostly the ones dissected earlier.

## The ones that matter for anime-style work

**"A System of Lights" (vfeogqzm8y, 2025), the cel-shading recipe.** 449 flat polygons traced over a reference, organised exactly like an anime cel: clothing colour, torso, face, hair base, *hair specular highlights*, hair lineart, face lineart. Lineart is a separate layer of thin curves on top. Animation is cheap and convincing:
- *Breathing*: scale a polygon around its own centre, `mean(x) + (x - mean(x))(1 + 0.02 sin(t/10))`.
- *Flicker*: `fillOpacity = 0.62 + 0.2 sin(t/0.08)`.
- *Fire*: deform every vertex by an amount proportional to its height above the base, `X = 0.004 (y - y_base) sin(2t/3 + y)`, so the tip sways and the base stays put. Three copies at opacity 1, 0.2 and 0.1 (scaled up) give core, glow and halo.
- *Sparks*: 16 circles positioned by a hash `sin(91.7n) - floor(sin(91.7n))`, drifting with slow sines, opacity `max(0, sin(2t + n))` so they blink in and out.

**"In the Distance" (0qy6pb4tr2, 2025), hair in the wind.** Hair strands are polygons whose *tip* vertices get `+k sin(t)` with k growing toward the tip (`+sin t`, `+2 sin t`, `+4 sin t`, `+10 sin t`). The root stays fixed. A ticker `t -> t + dt/1000` drives everything, and per-part opacity sliders (`t_hair`, `t_sea`) were used while drawing.

**"silent scream" (mdmf4zoiuy, 2023), an anime eye.** 96 polygons: white of the eye, two iris layers, eyelid as a thick black polygon, lower lid at opacity 0.8, highlights, then a whole landscape reflected inside the iris. Good template for a Gojo eye close-up.

**"Hummingbird" (lt3yqpjlru) and "Lionfish" (y5ugyiadfb), Simon Lav: motion in under 60 expressions.** Bodies are 3D surfaces of revolution (inequalities projected isometrically). Motion is blocked with smooth steps, `b_f(x) = 1.88 + 1.78 step(x-2) - 0.66 step(x-5) ...`. *Settle* uses a damped spring, `s(x) = sin(4x) e^{-2x} / (1 + e^{-5(x-0.4)})`, added at each key time for overshoot. Wing flaps use `|sin(...)|`. This is the cleanest secondary-motion recipe in the set.

**"Cosmic Joyride" (gtnbkecmmi, 2025), effects.** *Film grain*: one polygon through 1,400-2,400 random points at opacity 0.015, so antialiasing speckles the screen. Volumetric black hole: parametric curves (faster than layered implicits) at opacity 0.05. Star list hit the 10k limit, so stars are split by motion-blur scale.

**"pick it up pick it up" (3f2n1fhtyi, 2025).** Three moshing figures drawn from the author's own reference clips, 99 tables plus polygons, flat colour per figure. Shows that poses from video reference work well.

## Lessons added to the catalogue

- An anime look comes from **layer discipline** (base, shadow, highlight, lineart), not from fancy maths.
- **Vertex deformation weighted by distance from an anchor** handles hair, fire, cloth and capes with one formula.
- **Breathing, flicker, blink** are one-line opacity or scale sines and add a lot of life.
- **Springs and smooth steps** give key poses overshoot and settle.
- **Grain** from one random polygon is a free post-process.
