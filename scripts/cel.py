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
    """k tones for the whole shot, plus up to `accents` vivid, bright colours (eye
    glow, flames, energy) that a plain k-means would swallow because they cover few
    pixels. Returns (centres in LAB, number of tones); accents follow the tones."""
    Zs = [cv2.cvtColor(i, cv2.COLOR_RGB2LAB).reshape(-1, 3) for i in imgs]
    Z = np.concatenate([cv2.cvtColor(flatten(i), cv2.COLOR_RGB2LAB).reshape(-1, 3) for i in imgs]).astype(np.float32)
    Z = Z[np.random.default_rng(seed).choice(len(Z), min(px, len(Z)), replace=False)]
    cen = _km(Z, k, seed)
    R = np.concatenate(Zs).astype(np.float32)
    R = R[np.random.default_rng(seed).choice(len(R), min(px * 2, len(R)), replace=False)]
    chroma = np.hypot(R[:, 1] - 128, R[:, 2] - 128)
    glow = (chroma > 38) & (R[:, 0] > 170)  # vivid and bright, not just saturated
    hot = R[glow]
    if accents and len(hot) > 150:
        acc = _km(hot, max(1, min(accents, len(hot) // 150)), seed)
        far = [a for a in acc if np.sqrt(((cen - a) ** 2).sum(1)).min() > 30]
        if far: cen = np.concatenate([cen, np.array(far, np.float32)])
    return cen, k

def accent_masks(img, cen, k):
    """Pixels of the raw frame that match each accent: drawn on top of the fills,
    each with a soft halo ring in the colour actually around it."""
    L = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    pc = np.hypot(L[:, 1] - 128, L[:, 2] - 128)
    out = []
    for a in cen[k:]:
        ca = np.hypot(a[1] - 128, a[2] - 128)
        m = ((np.sqrt(((L - a) ** 2).sum(1)) < 28) & (pc > 0.6 * ca)).reshape(img.shape[:2]).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, cc, st, _ = cv2.connectedComponentsWithStats(m, 8)  # glows are blobs, not grain
        keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= 12
        m = keep[cc].astype(np.uint8)
        if m.sum() < 12: continue
        ring = (cv2.dilate(m, np.ones((7, 7), np.uint8)) > 0) & (m == 0)
        halo = img[ring].mean(0) * 0.5 + rgb(a[None])[0] * 0.5 if ring.any() else rgb(a[None])[0]
        out.append((halo.astype(np.uint8), ring | (m > 0)))
        out.append((rgb(a[None])[0], m > 0))
    # small glows that never made the shot palette (a faint eye glow in a wide shot):
    # pixels far more vivid than the rest of this frame, bright, and in a solid blob
    thr = max(26, np.percentile(pc, 99.7)) if len(cen) == k else 1e9
    Lr = L[:, 0].reshape(img.shape[:2]); C = pc.reshape(img.shape[:2])
    m = ((C > thr) & (Lr > 150)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(m, 8)
    for i in range(1, n):
        if not 12 <= st[i, cv2.CC_STAT_AREA] <= 4000: continue
        b = cc == i; col = img[b].mean(0)
        ring = (cv2.dilate(b.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~b
        out.append(((img[ring].mean(0) * 0.5 + col * 0.5).astype(np.uint8), ring | b))
        out.append((col.astype(np.uint8), b))
    return out

def ink(img, block=15, C=18, min_px=30, min_len=12):
    """Ink lines: pixels clearly darker than their neighbourhood (works for grey
    pencil on white as well as black ink), kept only in stroke-like pieces so that
    ground texture and film grain do not turn into speckles."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    m = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, C) > 0
    # drop thick dark blobs (a shadow core inside hair is a fill, not a line)
    m &= ~(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    keep[1:] = (st[1:, cv2.CC_STAT_AREA] >= min_px) & (np.maximum(st[1:, cv2.CC_STAT_WIDTH], st[1:, cv2.CC_STAT_HEIGHT]) >= min_len)
    return keep[cc]

def light_ink(img, thr=70, C=25, min_px=4):
    """Bright strokes on a dark ground: pixels well above their neighbourhood and above thr."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    m = (cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -C) > 0) & (g > thr)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= min_px
    return keep[cc]

def labels(img, cen, soft=2.5):
    """Fill label map over the shot's tones (accents are drawn separately)."""
    L = cv2.cvtColor(flatten(img), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    lab = ((L[:, None] - cen[None]) ** 2).sum(-1).argmin(1).reshape(img.shape[:2])
    # two near-black tones read as one black to the eye; splitting them draws rings in dark hair
    order = np.argsort(cen[:, 0])
    for a, b in zip(order[:-1], order[1:]):
        if cen[b, 0] < 30 and np.sqrt(((cen[a] - cen[b]) ** 2).sum()) < 30: lab[lab == b] = a
    # soft majority: blur each class mask, keep the strongest -> smooth, speckle-free borders
    votes = np.stack([cv2.GaussianBlur((lab == c).astype(np.float32), (0, 0), soft) for c in range(len(cen))])
    return merge_islands(votes.argmax(0), cen)

def merge_islands(lab, cen, passes=3):
    """Remove 'bullseye' rings in smooth gradients (a black core inside dark hair, a
    blob inside a sky): an island of one tone that sits entirely inside a single
    other, similar tone takes that tone. A colourist would paint it as one shape."""
    L = cen[:, 0]
    dist = np.sqrt(((cen[:, None] - cen[None]) ** 2).sum(-1))
    h, w = lab.shape
    # letterbox bars count as frame edge, so a shape is not 'touching the edge' through them
    top = bot = 0
    while top < h // 4 and np.bincount(lab[top]).max() > 0.98 * w: top += 1
    while bot < h // 4 and np.bincount(lab[h - 1 - bot]).max() > 0.98 * w: bot += 1
    for _ in range(passes):
        changed = False
        for c in range(len(cen)):
            m = (lab == c).astype(np.uint8); m[:top] = 0; m[h - bot:] = 0
            n, cc, st, _ = cv2.connectedComponentsWithStats(m, 8)
            for i in range(1, n):
                x, y, bw, bh, area = st[i]
                if x == 0 or y <= top or x + bw >= w or y + bh >= h - bot or area > 0.25 * h * w: continue
                sub = (slice(max(0, y - 3), y + bh + 3), slice(max(0, x - 3), x + bw + 3))
                b = (cc[sub] == i).astype(np.uint8)
                ring = (cv2.dilate(b, np.ones((5, 5), np.uint8)) > 0) & (b == 0)
                vals = lab[sub][ring]
                if not len(vals): continue
                o = np.bincount(vals, minlength=len(cen)).argmax()
                if (vals == o).mean() < 0.95 or o == c: continue
                if dist[c, o] < 20 or (max(L[c], L[o]) < 110 and dist[c, o] < 40):
                    lab[sub][b > 0] = o; changed = True
        if not changed: break
    return lab

def rgb(cen):
    return cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)

def cel_slots(img, cen, fmtx, fmty, turd=40, alphamax=1.0, simplify=1.0, lines=True, k=None):
    k = len(cen) if k is None else k
    lab = labels(img, cen[:k]); pal = rgb(cen)
    layers = [(pal[c], lab == c, turd, alphamax) for c in np.argsort([-(lab == c).sum() for c in range(k)])]
    preview = pal[lab].copy()
    for col, m in accent_masks(img, cen, k):
        layers.append((col, m, 4, 1.0)); preview[m] = col
    dark = np.argmin(cen[:k, 0])
    if (lab == dark).mean() > 0.85:  # mostly-black frame: keep small bright detail (credits text, distant lights)
        m = light_ink(img)
        if m.sum():
            col = pal[np.argmin(((cen[:k] - cv2.cvtColor(img[m].reshape(1, -1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32).mean(0)) ** 2).sum(1))]
            layers.append((col, m, 2, 0.8)); preview[m] = col
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
