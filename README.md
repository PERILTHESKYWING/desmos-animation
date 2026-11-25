# desmos-animation

Tools and notes for making cinematic animations in the Desmos graphing calculator, rendered to video headlessly. Lean on purpose: a few scripts plus a skill, not a framework.

## Status

Milestone 1 (research) is done: four example graphs and the 2022-2025 Math Art galleries dissected, key techniques tested headless.

- `research/techniques.md`: **the technique catalogue** (tested vs seen, costs, Gojo vs Sukuna mapping).
- `research/lessons.md`: first-pass lessons from the four example graphs.
- `research/tests/`: scenes that prove each technique renders.
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

```sh
# Render a scene file (expressions + clock + optional camera) to frames
NODE_PATH=$(npm root -g) node scripts/render.js research/tests/t2_glow.json out/t2

# Image to filled Desmos polygons, one expression per colour
pip install potracer opencv-python-headless pillow numpy
python3 scripts/img2desmos.py pose.png pose.json --colors 8
```

`render.js` and `frames.js` load desmos.com/calculator in headless Chromium (Playwright) and drives the page's `Calc` object.
