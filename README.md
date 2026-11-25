# desmos-animation

Tools and notes for making cinematic animations in the Desmos graphing calculator, rendered to video headlessly. Lean on purpose: a few scripts plus a skill, not a framework.

## Status

Milestone 1 (research) is done: four example graphs dissected end to end.

- `research/lessons.md`: the reusable technique list.
- `research/dissections/`: one write-up per example graph, with contact sheets.
- `research/bezier-renderer.md`: notes on DesmosBezierRenderer and its tutorial video.

## Scripts

```sh
# Summarise any saved graph (no API key needed)
python3 scripts/fetch.py https://www.desmos.com/calculator/u6nxdjq31x [--out state.json] [--full]

# Render frames by setting variables, then make a video
NODE_PATH=$(npm root -g) node scripts/frames.js bhqh6a0i9g out '[[{"k":1}],[{"k":2}],[{"k":3}]]'
ffmpeg -framerate 30 -i out_%03d.png -pix_fmt yuv420p out.mp4
```

`frames.js` loads desmos.com/calculator in headless Chromium (Playwright) and drives the page's `Calc` object.
