#!/usr/bin/env python3
"""Convert an image into filled Desmos polygons, one expression per colour.

    python3 scripts/img2desmos.py in.png out.json [--colors 8] [--width 32] [--detail 2]

Approach (from the dissections): quantize to K flat colours, trace each colour
mask with potrace, sample the Bezier paths into points, and join every blob of
a colour into ONE polygon() with (0/0,0/0) breaks. Layers are emitted largest
first so small details land on top. Output is a render.js scene file.

Needs: pip install potracer opencv-python-headless pillow numpy
"""
import json, sys, argparse
import numpy as np
from PIL import Image
import potrace

def sample(curve, step):
    """Turn a potrace curve into a flat list of (x, y) points."""
    pts = []; start = curve.start_point
    for seg in curve.segments:
        x0, y0 = start.x, start.y
        if seg.is_corner:
            pts += [(seg.c.x, seg.c.y), (seg.end_point.x, seg.end_point.y)]
        else:
            c1, c2, e = seg.c1, seg.c2, seg.end_point
            n = max(2, int(np.hypot(e.x - x0, e.y - y0) / step))
            for i in range(1, n + 1):
                t = i / n; u = 1 - t
                pts.append((u**3*x0 + 3*u*u*t*c1.x + 3*u*t*t*c2.x + t**3*e.x,
                            u**3*y0 + 3*u*u*t*c1.y + 3*u*t*t*c2.y + t**3*e.y))
        start = seg.end_point
    return pts

def convert(path, k=8, width=32.0, detail=2.0, turdsize=8):
    img = Image.open(path).convert('RGB')
    q = img.quantize(colors=k, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:3 * k]).reshape(-1, 3)
    idx = np.array(q)
    h, w = idx.shape; s = width / w
    layers = []
    for c in range(k):
        mask = idx == c
        if mask.sum() < turdsize: continue
        # potracer traces the False pixels, so pass the inverted mask; flip y so the
        # image is upright in Desmos (y grows upward)
        plist = potrace.Bitmap(~mask[::-1]).trace(turdsize=turdsize, alphamax=1.0, opticurve=True, opttolerance=0.4)
        blobs = [sample(cv, detail) for cv in plist]
        blobs = [b + b[:1] for b in blobs if len(b) >= 3]   # close every ring explicitly
        if not blobs: continue
        # Desmos fills one polygon() with the nonzero rule: a ring wound the other way is
        # a hole (potrace already winds holes oppositely) but only if each ring is closed.
        # Lists cap at 10,000 elements, so split into chunks, keeping rings whole.
        chunks, xs, ys = [], [], []
        for b in blobs:
            if xs and len(xs) + len(b) + 1 > 9990:
                chunks.append((xs, ys)); xs, ys = [], []
            xs += [f"{(x - w/2)*s:.2f}" for x, _ in b[:9989]] + ["0/0"]
            ys += [f"{(y - h/2)*s:.2f}" for _, y in b[:9989]] + ["0/0"]
        chunks.append((xs, ys))
        for xs, ys in chunks:
            layers.append((int(mask.sum()), '#%02x%02x%02x' % tuple(pal[c]), xs, ys))
    layers.sort(key=lambda L: -L[0])  # stable: chunks of one colour stay together
    # Full-screen fill in the dominant colour hides hairline seams between layers.
    exprs, npts = [{"latex": r"\left|x\right|>0", "color": layers[0][1], "fillOpacity": "1", "lines": False}], 0
    for area, col, xs, ys in layers:
        npts += len(xs)
        exprs.append({"latex": r"\operatorname{polygon}\left(\left[" + ",".join(xs) + r"\right],\left[" + ",".join(ys) + r"\right]\right)",
                      "color": col, "fillOpacity": "1", "lines": False})
    H = width * h / w
    return {"size": [960, int(960 * h / w) // 2 * 2], "bounds": {"left": -width/2, "right": width/2, "bottom": -H/2, "top": H/2},
            "expressions": exprs, "stats": {"layers": len(exprs), "points": npts}}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--colors', type=int, default=8); ap.add_argument('--width', type=float, default=32)
    ap.add_argument('--detail', type=float, default=2.0, help='pixels per sampled point on curves (bigger = fewer points)')
    a = ap.parse_args()
    sc = convert(a.inp, a.colors, a.width, a.detail)
    json.dump(sc, open(a.out, 'w'))
    print(sc['stats'])
