#!/usr/bin/env python3
"""Clean, hand-made-looking flat-colour ("cel") version of a frame.

One palette per shot (no colour flicker between frames), mean-shift flattening,
soft majority vote on the label map (no speckles, smooth borders), then potrace
with smooth curves. Returns the same slot list video_link.py packs.
"""
import numpy as np, cv2
from video2desmos import potrace_rings

def flatten(img, sp=10, sr=24):
    return cv2.pyrMeanShiftFiltering(img, sp, sr)

def _km(Z, k, seed):
    cv2.setRNGSeed(seed)
    _, _, cen = cv2.kmeans(Z, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2), 3, cv2.KMEANS_PP_CENTERS)
    return cen

def fit_palette(imgs, k, accents=2, px=200000, seed=0):
    """k tones for the whole shot, plus up to `accents` saturated colours (eye glow,
    flames) that a plain k-means would swallow because they cover few pixels."""
    Z = np.concatenate([cv2.cvtColor(flatten(i), cv2.COLOR_RGB2LAB).reshape(-1, 3) for i in imgs]).astype(np.float32)
    Z = Z[np.random.default_rng(seed).choice(len(Z), min(px, len(Z)), replace=False)]
    cen = _km(Z, k, seed)
    chroma = np.hypot(Z[:, 1] - 128, Z[:, 2] - 128)
    hot = Z[chroma > max(40, np.percentile(chroma, 99.5))]
    if accents and len(hot) > 200:
        cen = np.concatenate([cen, _km(hot, min(accents, len(hot) // 100), seed)])
    return cen  # LAB float

def ink(img, block=15, C=10, dark=120, min_px=25):
    """Dark ink lines: pixels clearly darker than their surroundings."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    m = (cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, C) > 0) & (g < dark)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= min_px
    return keep[cc]

def labels(img, cen, soft=2.5):
    L = cv2.cvtColor(flatten(img), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    d = ((L[:, None] - cen[None]) ** 2).sum(-1)
    # a saturated accent (eye glow) may only claim pixels that are themselves vivid,
    # otherwise dull sky next to a glow gets painted in the accent colour
    cc = np.hypot(cen[:, 1] - 128, cen[:, 2] - 128); pc = np.hypot(L[:, 1] - 128, L[:, 2] - 128)
    for c in np.where(cc > 40)[0]:
        d[pc < 0.7 * cc[c], c] = np.inf
    lab = d.argmin(1).reshape(img.shape[:2])
    # soft majority: blur each class mask, keep the strongest -> smooth, speckle-free borders
    votes = np.stack([cv2.GaussianBlur((lab == c).astype(np.float32), (0, 0), soft) for c in range(len(cen))])
    return votes.argmax(0)

def rgb(cen):
    return cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)

def cel_slots(img, cen, fmtx, fmty, turd=40, alphamax=1.0, simplify=1.0, lines=True):
    lab = labels(img, cen); pal = rgb(cen)
    layers = [(pal[c], lab == c, turd, alphamax) for c in np.argsort([-(lab == c).sum() for c in range(len(cen))])]
    preview = pal[lab].copy()
    if lines:  # ink on top, in the shot's darkest tone
        m = ink(img); col = pal[np.argmin(cen[:, 0])]
        layers.append((col, m, 6, 0.8)); preview[m] = col
    slots = []
    for col, mask, turd, alphamax in layers:
        if mask.sum() < turd: continue
        xs, ys = [], []
        for r in potrace_rings(mask, turdsize=turd, alphamax=alphamax, simplify=simplify):
            if xs and len(xs) + len(r) + 1 > 9990:
                slots.append((col, (xs, ys))); xs, ys = [], []
            xs += [fmtx(x) for x, _ in r[:9989]] + ['0/0']; ys += [fmty(y) for _, y in r[:9989]] + ['0/0']
        if xs: slots.append((col, (xs, ys)))
    return slots, preview
