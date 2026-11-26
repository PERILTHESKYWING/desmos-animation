#!/usr/bin/env python3
"""Automatic flaw checks for amv_build.py output.

    python3 scripts/amv_qa.py WORK [--render RENDER_DIR] [--sheet]

Per drawing (cel preview vs source frame):
  patch   a connected region (>1.5% of the frame) whose colour is far from the source
          (mean CIELAB distance > 30): stray colour blobs
  glow    a vivid bright blob in the source that the cel version lost
Per rendered frame (with --render, files rNNNNN.png at 1920x1080):
  render  rendered frame differs from its cel preview (PSNR < 24 dB): a Desmos fault
--sheet writes contact sheets (one preview per shot) to WORK/qa/ for a visual pass.
Prints flagged frames and writes WORK/qa/flags.json.
"""
import argparse, json, os, glob
import numpy as np, cv2

def lab(img): return cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)

def patches(src, prev):
    d = np.sqrt(((lab(cv2.GaussianBlur(src, (0, 0), 3)) - lab(prev)) ** 2).sum(-1))
    m = (d > 30).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(m, 8)
    big = [int(st[i, cv2.CC_STAT_AREA]) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.015 * m.size]
    return big

def glows(img):
    L = lab(img); c = np.hypot(L[..., 1] - 128, L[..., 2] - 128)
    m = ((c > 38) & (L[..., 0] > 170)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--render'); ap.add_argument('--sheet', action='store_true')
    a = ap.parse_args()
    fr = os.path.join(a.work, 'frames'); qa = os.path.join(a.work, 'qa'); os.makedirs(qa, exist_ok=True)
    flags = {}
    for p in sorted(glob.glob(os.path.join(a.work, 'slots', '*_preview.png'))):
        n = os.path.basename(p).replace('_preview', '')
        src, prev = cv2.imread(os.path.join(fr, n)), cv2.imread(p)
        f = []
        big = patches(src, prev)
        if big: f.append(f'patch {max(big) * 100 // src[..., 0].size}%')
        gs, gp = glows(src), glows(prev)
        lost = gs.sum() - (gs & gp).sum()
        if gs.sum() > 40 and lost > 0.6 * gs.sum(): f.append(f'glow lost {int(lost)}px')
        if f: flags[n] = f
    if a.render:
        for p in sorted(glob.glob(os.path.join(a.render, 'r*.png'))):
            n = os.path.basename(p); pv = os.path.join(a.work, 'slots', n.replace('.png', '_preview.png'))
            if not os.path.exists(pv): continue  # held frame: same as its drawing
            r = cv2.resize(cv2.imread(p), (960, 540), interpolation=cv2.INTER_AREA).astype(np.float32)
            m = ((r - cv2.imread(pv).astype(np.float32)) ** 2).mean()
            ps = 99 if m == 0 else 10 * np.log10(255 ** 2 / m)
            if ps < 24: flags.setdefault(n, []).append(f'render {ps:.1f}dB')
    json.dump(flags, open(os.path.join(qa, 'flags.json'), 'w'), indent=0)
    print(len(flags), 'flagged'); [print(k, v) for k, v in list(flags.items())[:80]]
    if a.sheet:
        shots = json.load(open(os.path.join(a.work, 'shots.json'))); dup = json.load(open(os.path.join(a.work, 'dupmap.json')))
        tiles = []
        for s, e in shots:
            n = dup[f'r{(s + e) // 2:05d}.png']; pv = os.path.join(a.work, 'slots', n.replace('.png', '_preview.png'))
            if not os.path.exists(pv): continue
            t = np.hstack([cv2.resize(cv2.imread(os.path.join(fr, n)), (320, 180)), cv2.resize(cv2.imread(pv), (320, 180))])
            cv2.putText(t, f'{s}', (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            tiles.append(t)
        for b in range(0, len(tiles), 30):
            g = tiles[b:b + 30]; g += [np.zeros_like(tiles[0])] * (-len(g) % 3)
            cv2.imwrite(os.path.join(qa, f'sheet{b // 30:02d}.jpg'), np.vstack([np.hstack(g[i:i + 3]) for i in range(0, len(g), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
