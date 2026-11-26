#!/usr/bin/env python3
"""Pack video frames into ONE playable Desmos graph (for a desmos.com link).

    python3 scripts/video_link.py frames_dir state.json [--step 2] [--k 12] [--simplify 1.0] [--fps 30]

Live Desmos can only afford a few MB, so this is a lighter cut than video2desmos.py:
each frame is k-means quantized (CIELAB) to k colours and traced with potrace.
Layout (the Steamboat Willie trick, extended to per-frame palettes):

  hidden, collapsed folder:  a_{f<i>s<j>} = polygon(...)   frame i, slot j (j-th largest colour)
                             R_{s<j>}, G_{s<j>}, B_{s<j>}  slot colour for every frame
  visible, one per slot:     [a_{f1sj}, a_{f2sj}, ...][k]   colour rgb(R_sj[k], G_sj[k], B_sj[k])
  ticker:                    k -> {k = N: 1, k + 1} every 1000/fps ms

Only the k-dependent slot expressions change per tick; the frame data is constant.
Then: node scripts/share.js state.json --state
"""
import json, sys, glob, os, argparse
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from video2desmos import kmeans_lab, potrace_rings, num

PIX = False  # --pix: integer coordinates with the origin at the bottom-left corner

def fmt(v, half):
    return str(int(round(v + half))) if PIX else num(v)

def frame_slots(img, k, simplify, width, smooth=True):
    h, w = img.shape[:2]; s = width / w
    std = img.reshape(-1, 3).std(0).max()
    if std < 6:
        return [(img.reshape(-1, 3).mean(0), None)]  # flat: background colour only
    lab, pal = kmeans_lab(cv2.bilateralFilter(img, 7, 30, 5) if smooth else img, k)
    slots = []
    for c in np.argsort([-(lab == c).sum() for c in range(len(pal))]):
        mask = lab == c
        if mask.sum() < 6: continue
        rings = potrace_rings(mask, turdsize=6, alphamax=0.6, simplify=simplify)
        xs, ys = [], []
        for r in rings:  # a colour with more than 10k points spills into extra slots
            if xs and len(xs) + len(r) + 1 > 9990:
                slots.append((pal[c], (xs, ys))); xs, ys = [], []
            xs += [fmt((x - w / 2) * s, width / 2) for x, _ in r[:9989]] + ['0/0']
            ys += [fmt((y - h / 2) * s, width * h / w / 2) for _, y in r[:9989]] + ['0/0']
        if xs: slots.append((pal[c], (xs, ys)))
    return slots

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('frames'); ap.add_argument('out')
    ap.add_argument('--step', type=int, default=2); ap.add_argument('--k', type=int, default=12)
    ap.add_argument('--simplify', type=float, default=1.0); ap.add_argument('--fps', type=float, default=30)
    ap.add_argument('--width', type=float, default=32); ap.add_argument('--scale', type=float, default=0.5)
    ap.add_argument('--pix', action='store_true', help='integer coords (with --width 960: half-res pixels); about 40%% smaller')
    ap.add_argument('--dupmap', help='json {frame.png: first identical frame.png}: held drawings are stored once')
    a = ap.parse_args(); PIX = a.pix
    if a.dupmap:
        dm = json.load(open(a.dupmap)); names = sorted(dm)[::a.step]
        uniq = sorted(set(dm[n] for n in names))
        files = [os.path.join(a.frames, n) for n in uniq]
        order = [uniq.index(dm[n]) + 1 for n in names]
    else:
        files = sorted(glob.glob(os.path.join(a.frames, '*.png')))[::a.step]
        order = list(range(1, len(files) + 1))
    frames = []
    for f in files:
        img = Image.open(f).convert('RGB')
        full = np.asarray(img)
        # frames that are mostly one flat colour (logo on black) keep full resolution:
        # their thin strokes vanish at half size and they cost few points anyway
        dom = (np.abs(full.astype(int) - np.median(full.reshape(-1, 3), 0)).sum(-1) < 30).mean()
        if a.scale != 1 and dom < 0.75: img = img.resize((int(img.width * a.scale), int(img.height * a.scale)), Image.LANCZOS)
        frames.append(frame_slots(np.asarray(img), a.k, a.simplify, a.width, smooth=dom < 0.75))
        print(len(frames), len(frames[-1]), flush=True)
    N = len(frames); M = len(order); S = max(len(fr) for fr in frames)
    H = a.width * 9 / 16 if img.width * 9 == img.height * 16 else a.width * img.height / img.width
    x0, x1, y0, y1 = (('0', num(a.width), '0', num(H)) if PIX else
                      (f"-{num(a.width/2)}", num(a.width/2), f"-{num(H/2)}", num(H/2)))
    data, vis = [{"type": "folder", "id": "data", "title": "frame data (keep closed)", "collapsed": True}], []
    for j in range(S):
        R, G, B = [], [], []
        for i, fr in enumerate(frames):
            col, poly = fr[j] if j < len(fr) else (fr[0][0], None)
            R.append(int(col[0])); G.append(int(col[1])); B.append(int(col[2]))
            if poly is None:
                latex = rf"a_{{f{i+1}s{j+1}}}=\operatorname{{polygon}}\left(\left[0/0\right],\left[0/0\right]\right)"
                if j == 0:  # flat frame: slot 1 is a full-screen rectangle
                    latex = (rf"a_{{f{i+1}s{j+1}}}=\operatorname{{polygon}}\left(\left[{x0},{x1},{x1},{x0}\right],"
                             rf"\left[{y0},{y0},{y1},{y1}\right]\right)")
            else:
                xs, ys = poly
                if j == 0:  # largest colour also floods the frame so gaps never show white
                    xs = [x0, x1, x1, x0, x0, "0/0"] + xs
                    ys = [y0, y0, y1, y1, y0, "0/0"] + ys
                latex = rf"a_{{f{i+1}s{j+1}}}=\operatorname{{polygon}}\left(\left[{','.join(xs)}\right],\left[{','.join(ys)}\right]\right)"
            data.append({"type": "expression", "id": f"f{i+1}s{j+1}", "folderId": "data", "latex": latex, "hidden": True})
        for nm, L in (("R", R), ("G", G), ("B", B)):
            data.append({"type": "expression", "id": f"{nm}{j+1}", "folderId": "data",
                         "latex": rf"{nm}_{{s{j+1}}}=\left[{','.join(map(str, L))}\right]"})
        vis.append({"type": "expression", "id": f"slot{j+1}",
                    "latex": r"\left[" + ",".join(rf"a_{{f{i+1}s{j+1}}}" for i in range(N)) + r"\right]\left[u\right]",
                    "colorLatex": rf"\operatorname{{rgb}}\left(R_{{s{j+1}}}\left[u\right],G_{{s{j+1}}}\left[u\right],B_{{s{j+1}}}\left[u\right]\right)",
                    "fillOpacity": "1", "lines": False})
    state = {"version": 11, "randomSeed": "0",
             "graph": {"viewport": ({"xmin": 0, "xmax": a.width, "ymin": 0, "ymax": H} if PIX else
                                    {"xmin": -a.width/2, "xmax": a.width/2, "ymin": -H/2, "ymax": H/2}),
                       "showGrid": False, "showXAxis": False, "showYAxis": False},
             "expressions": {"list": [
                 {"type": "text", "id": "note", "text": f"{M} frames ({N} drawings) at {a.fps:g} fps. Press play on the ticker (or drag k)."},
                 {"type": "expression", "id": "k", "latex": "k=1", "slider": {"hardMin": True, "hardMax": True, "min": "1", "max": str(M), "step": "1"}},
                 {"type": "expression", "id": "U", "latex": r"U=\left[" + ",".join(map(str, order)) + r"\right]", "hidden": True},
                 {"type": "expression", "id": "u", "latex": r"u=U\left[k\right]", "hidden": True},
             ] + vis + data,
                 "ticker": {"handlerLatex": rf"k\to\left\{{k={M}:1,k+1\right\}}", "minStepLatex": f"{1000/a.fps:.3f}", "open": True, "playing": True}}}
    json.dump(state, open(a.out, 'w'))
    print('frames', N, 'slots', S, 'MB', round(os.path.getsize(a.out) / 1e6, 2))
