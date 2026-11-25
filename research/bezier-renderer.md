# DesmosBezierRenderer and Junferno's tutorial video

Repo: github.com/kevinjycui/DesmosBezierRenderer (GPL-3.0). Video: "How I animate stuff on Desmos Graphing Calculator" (Junferno, 7:48), transcript read through the desktop app's browser.

## What it does

1. Video to PNG frames (youtube-dl, ffmpeg).
2. Per frame: greyscale, **Canny edge detection** (OpenCV), then **potrace** on the edge image. potrace needs a strictly two-colour bitmap, which is why Canny runs first on colour images.
3. Every potrace segment becomes **one parametric expression**: corners as two linear pieces, curves as a nested-lerp cubic Bezier in `t`. A frame is thousands of expressions, all one colour, outlines only.
4. A Flask server hands each frame's expressions to a browser page that calls `setExpressions`, screenshots, and moves to the next frame.

## Limits today

- It embeds the old **demo API key**, which Desmos deprecated in September 2025, so the frontend no longer works as shipped.
- Tracing the output of an edge detector gives **double lines** (the author says so in the video).
- Outlines only, single colour, no fills or shading.
- Render speed is limited by expression count: about an hour for Bad Apple.
- GPL-3.0, and the author asks that it not be used for Math Art Contest entries. We should **reimplement the idea, not copy the code**.

## What we take from it

- potrace is the right tool for raster to Bezier.
- Writing curves as nested lerps is safe LaTeX that Desmos parses fast.
- The frame loop (set expressions, screenshot, next) is the same loop as our `frames.js`, with Playwright on desmos.com instead of the API.

## How we do it better (next milestone)

Combine with the Steamboat Willie approach: quantize each frame to K colours, run potrace on each colour mask (no Canny, so no double lines), sample paths into points, and emit one filled `polygon()` per colour joined with `0/0`. That gives coloured, shaded art in K expressions per frame instead of thousands.
