#!/usr/bin/env python3
"""Convert video frames into per-frame Desmos scenes, as close to the source as possible.

    python3 scripts/video2desmos.py frames_dir out_dir [--width 32] [--target 33] [--maxk 64]

For every frame it picks the cheapest representation that reaches the target
PSNR (dB) against the source frame, or the best one it can afford:

  flat   one full-screen fill (white flashes, black frames)
  trace  k-means colour quantization in CIELAB (k = 8..maxk), each colour mask
         traced by the potrace CLI (Beziers flattened to points), one polygon() per
         colour with (0/0,0/0) breaks; holes via reversed closed rings
  grid   a smooth-gradient grid of rectangles, colour per cell from rgb lists
         (better than tracing on soft glows and gradients)

Writes out_dir/fNNNN.json (render_seq.js format: {"expressions": [...]}) and
out_dir/report.json with the method, k, points and predicted PSNR per frame.
Needs: apt install potrace; pip install opencv-python-headless pillow numpy
"""
import json, os, sys, argparse, glob
import numpy as np, cv2
from PIL import Image

def psnr(a, b):
    m = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return 99.0 if m == 0 else float(10 * np.log10(255 ** 2 / m))

def kmeans_lab(img, k, fit_px=60000, seed=0):
    """k-means in CIELAB. Fit on a random pixel sample, then label every pixel."""
    Z = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    rng = np.random.default_rng(seed)
    S = Z[rng.choice(len(Z), min(fit_px, len(Z)), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.3)
    _, _, cen = cv2.kmeans(S, k, None, crit, 1, cv2.KMEANS_PP_CENTERS)
    d = ((Z[:, None, :] - cen[None, :, :]) ** 2).sum(-1) if len(Z) * k < 4e7 else None
    if d is None:
        lab = np.concatenate([((Z[i:i+100000, None, :] - cen[None]) ** 2).sum(-1).argmin(1) for i in range(0, len(Z), 100000)])
    else:
        lab = d.argmin(1)
    rgb = cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    return lab.reshape(img.shape[:2]), rgb

def sample(curve, step):
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

def potrace_rings(mask, turdsize=4, alphamax=0.4, simplify=0.4):
    """Trace a boolean mask with the potrace CLI (fast C) and return closed rings in
    pixel units, y up. potrace fits cubic Beziers; the GeoJSON backend flattens them
    into points. Outer rings come out counter-clockwise and holes clockwise, which
    Desmos's nonzero fill turns into real holes."""
    import io, subprocess
    buf = io.BytesIO(); Image.fromarray(~mask).convert('1').save(buf, format='PPM')
    out = subprocess.run(['potrace', '-b', 'geojson', '-a', str(alphamax), '-O', '0.2', '-t', str(turdsize),
                          '-r', '72', '-o', '-', '-'], input=buf.getvalue(), capture_output=True).stdout
    rings = []
    for f in json.loads(out)['features']:
        for ring in f['geometry']['coordinates']:
            a = np.asarray(ring, np.float32)
            if simplify:  # drop points closer than `simplify` px to the curve (Douglas-Peucker)
                a = cv2.approxPolyDP(a.reshape(-1, 1, 2), simplify, True).reshape(-1, 2)
            if len(a) >= 3: rings.append([tuple(p) for p in a] + [tuple(a[0])])
    return rings

def hexc(c): return '#%02x%02x%02x' % tuple(int(v) for v in c)
def num(v): return f"{v:.2f}".rstrip('0').rstrip('.') or '0'

def bg(col):
    return {"latex": r"\left|x\right|>0", "color": hexc(col), "fillOpacity": "1", "lines": False}

def trace_layers(lab, pal, width, detail, turdsize, dilate=0, alphamax=0.4, underlay=None):
    h, w = lab.shape; s = width / w
    layers = []
    for c in range(len(pal)):
        mask = lab == c
        area = int(mask.sum())
        if area < turdsize: continue
        # grow each colour region a little (optional) so neighbouring shapes overlap
        m = cv2.dilate(mask.astype(np.uint8), np.ones((2 * dilate + 1,) * 2, np.uint8)) > 0 if dilate else mask
        rings = potrace_rings(m, turdsize, alphamax)
        xs, ys, chunks = [], [], []
        for r in rings:
            if xs and len(xs) + len(r) + 1 > 9990:
                chunks.append((xs, ys)); xs, ys = [], []
            xs += [num((x - w / 2) * s) for x, _ in r[:9989]] + ["0/0"]
            ys += [num((y - h / 2) * s) for _, y in r[:9989]] + ["0/0"]
        if xs: chunks.append((xs, ys))
        for xs, ys in chunks:
            layers.append((area, pal[c], xs, ys))
    layers.sort(key=lambda L: -L[0])
    exprs = [bg(layers[0][1])] if layers else []
    if underlay is not None:  # low-res colour grid under the traced shapes: any gap shows nearly the right colour
        exprs = underlay
    pts = 0
    for _, col, xs, ys in layers:
        pts += len(xs)
        exprs.append({"latex": r"\operatorname{polygon}\left(\left[" + ",".join(xs) + r"\right],\left[" + ",".join(ys) + r"\right]\right)",
                      "color": hexc(col), "fillOpacity": "1", "lines": False})
    return exprs, pts

def grid_layers(img, cols, width):
    h, w = img.shape[:2]; rows = round(cols * h / w)
    small = cv2.resize(img, (cols, rows), interpolation=cv2.INTER_AREA)
    cw = width / cols; H = width * h / w; ch = H / rows
    flat = small[::-1].reshape(-1, 3)  # row 0 = bottom
    n = len(flat)
    exprs = [bg(img.reshape(-1, 3).mean(0))]  # also clears whatever the last frame left
    f6 = lambda v: f"{v:.6f}"  # grid steps need precision: 0.13 vs 0.1333 drifts 24 px over 240 cells
    for start in range(0, n, 9000):
        part = flat[start:start + 9000]; m = len(part)
        R, G, B = (",".join(str(int(v)) for v in part[:, i]) for i in range(3))
        # cell j sits at column mod(j, cols), row floor(j / cols)
        x0 = rf"\left(-{f6(width/2)}+{f6(cw)}\operatorname{{mod}}\left(j,{cols}\right)\right)"
        y0 = rf"\left(-{f6(H/2)}+{f6(ch)}\operatorname{{floor}}\left(\frac{{j}}{{{cols}}}\right)\right)"
        poly = (rf"\operatorname{{polygon}}\left(\left({x0},{y0}\right),\left({x0}+{f6(cw*1.04)},{y0}\right),"
                rf"\left({x0}+{f6(cw*1.04)},{y0}+{f6(ch*1.04)}\right),\left({x0},{y0}+{f6(ch*1.04)}\right)\right)"
                rf"\operatorname{{for}}j=\left[{start}...{start+m-1}\right]")
        exprs.append({"latex": poly, "colorLatex": rf"\operatorname{{rgb}}\left(\left[{R}\right],\left[{G}\right],\left[{B}\right]\right)",
                      "fillOpacity": "1", "lines": False, "lineWidth": "0", "lineOpacity": "0"})
    nearest = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return exprs, n * 3, nearest

def convert_frame(img, width, target, maxk, detail, cols_list=(160, 240)):
    h, w = img.shape[:2]
    std = img.reshape(-1, 3).std(0).max()
    if std < 6:  # flat frame
        return [bg(img.reshape(-1, 3).mean(0))], dict(method='flat', points=0, psnr=psnr(img, np.full_like(img, img.reshape(-1, 3).mean(0).astype(np.uint8))))
    sm = cv2.bilateralFilter(img, 7, 30, 5)
    best = None
    for k in (8, 16, 24, 32, 48, 64):
        if k > maxk: break
        # smoothing gives cleaner regions (fewer points) but kills thin lines; keep the better one
        for src in (sm, img):
            lab, pal = kmeans_lab(src, k)
            p = psnr(img, pal[lab])
            if best is None or best[1] != k or p > best[4]:
                best = ('trace', k, lab, pal, p)
        if best[4] >= target: break
    cand = []
    for cols in cols_list:
        small = cv2.resize(img, (cols, round(cols * h / w)), interpolation=cv2.INTER_AREA)
        cand.append((psnr(img, cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)), cols))
    gp, gcols = max(cand)
    if gp > best[4] + 1.0:
        exprs, pts, _ = grid_layers(img, gcols, width)
        return exprs, dict(method='grid', cols=gcols, points=pts, psnr=gp)
    _, k, lab, pal, p = best
    # one flat colour covering most of the frame (line art on black): the grid
    # underlay would put a grey halo round thin strokes, so use a flat fill there
    cnt = np.bincount(lab.ravel(), minlength=len(pal)); dom = cnt.argmax()
    rest = (lab != dom).astype(np.uint8)
    thin = rest.sum() and cv2.erode(rest, np.ones((5, 5), np.uint8)).sum() < 0.4 * rest.sum()
    if cnt[dom] > 0.6 * lab.size and thin:  # line art (strokes under ~5 px), not glows
        exprs, pts = trace_layers(lab, pal, width, detail, turdsize=4)
        return exprs, dict(method='trace-flat', k=k, points=pts, psnr=p)
    under, upts, _ = grid_layers(img, 240, width)
    exprs, pts = trace_layers(lab, pal, width, detail, turdsize=4, underlay=under)
    pts += upts
    return exprs, dict(method='trace', k=k, points=pts, psnr=p)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('frames'); ap.add_argument('out')
    ap.add_argument('--width', type=float, default=32); ap.add_argument('--target', type=float, default=33)
    ap.add_argument('--maxk', type=int, default=64); ap.add_argument('--detail', type=float, default=2.5)
    ap.add_argument('--only', type=str, default=None, help='comma list of frame numbers (1-based)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.frames, '*.png')))
    pick = set(int(x) for x in a.only.split(',')) if a.only else None
    rep_path = os.path.join(a.out, 'report.json')
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}
    for i, f in enumerate(files, 1):
        if pick and i not in pick: continue
        img = np.asarray(Image.open(f).convert('RGB'))
        exprs, info = convert_frame(img, a.width, a.target, a.maxk, a.detail)
        h, w = img.shape[:2]
        json.dump({"size": [w, h], "bounds": {"left": -a.width/2, "right": a.width/2, "bottom": -a.width*h/w/2, "top": a.width*h/w/2},
                   "expressions": exprs}, open(os.path.join(a.out, f'f{i:04d}.json'), 'w'))
        report[f'{i:04d}'] = info
        print(i, info, flush=True)
    json.dump(report, open(rep_path, 'w'), indent=0)
